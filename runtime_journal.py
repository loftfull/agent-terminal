from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from project_history_agent import event_dedupe_key
from project_history_journal import (
    JOURNAL_SCHEMA,
    SUPPORTED_OPS,
    ProjectLock,
    append_mutation,
    _read_records,
    _apply_mutation,
    _record_hash,
    atomic_write_text,
    journal_paths,
    replay_journal_set,
    redact_secrets,
    verify_journal_set,
)

ACTIVE_SEGMENT_MARKER = ".project-history.active-segment"


def _next_segment_name(project_root: Path | str, label: str = "runtime") -> str:
    root = Path(project_root)
    seg_dir = root / "PROJECT_HISTORY.segments"
    max_prefix = 1
    if seg_dir.is_dir():
        for path in seg_dir.glob("*.jsonl"):
            match = re.match(r"^(\d+)-", path.name)
            if match:
                max_prefix = max(max_prefix, int(match.group(1)))
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-.") or "runtime"
    return f"{max_prefix + 1:04d}-{safe_label}.jsonl"


def _active_segment_path_unlocked(root: Path, *, create: bool, label: str = "runtime") -> Path | None:
    marker = root / ACTIVE_SEGMENT_MARKER
    if marker.is_file():
        name = marker.read_text(encoding="utf-8").strip()
        if name and Path(name).name == name and name.endswith(".jsonl"):
            return root / "PROJECT_HISTORY.segments" / name
        raise ValueError(f"invalid active segment marker: {name!r}")
    if not create:
        return None
    name = _next_segment_name(root, label=label)
    seg_dir = root / "PROJECT_HISTORY.segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(marker, name + "\n")
    return seg_dir / name


def begin_runtime_segment(project_root: Path | str, *, label: str = "runtime", lock_timeout: float = 5.0) -> Path:
    root = Path(project_root)
    root.mkdir(parents=True, exist_ok=True)
    if not (root / "PROJECT_HISTORY.events.jsonl").is_file():
        raise FileNotFoundError(root / "PROJECT_HISTORY.events.jsonl")
    with ProjectLock(root / ".project-history.lock", timeout=lock_timeout):
        verification = verify_journal_set(root)
        if not verification["ok"]:
            raise ValueError(f"journal set integrity failure: {verification['issues']}")
        path = _active_segment_path_unlocked(root, create=True, label=label)
        assert path is not None
        existing = journal_paths(root)
        if path.exists() and existing and existing[-1] != path:
            raise ValueError(f"active segment is not the journal tail: {path.name}")
        return path


def close_runtime_segment(project_root: Path | str, *, lock_timeout: float = 5.0) -> None:
    root = Path(project_root)
    with ProjectLock(root / ".project-history.lock", timeout=lock_timeout):
        (root / ACTIVE_SEGMENT_MARKER).unlink(missing_ok=True)


def append_mutation_batch(project_root, mutations, *, timestamp=None,
                          segment_label="batch", lock_timeout=5.0):
    """Publish a validated batch by atomically replacing the active segment.

    A failed pre-publication write leaves no visible batch. A crash after rename
    may have committed it: callers must reconcile evidence IDs before retrying.
    """
    from project_history_auditor import audit_state
    mutations = list(mutations)
    if not mutations:
        raise ValueError("Empty mutation batch")
    root = Path(project_root)
    with ProjectLock(root / ".project-history.lock", timeout=lock_timeout):
        verification = verify_journal_set(root)
        if not verification["ok"]:
            raise ValueError("Journal set integrity failure")
        state = replay_journal_set(root)
        ts = timestamp or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        records = []
        previous = verification["last_hash"]
        for op, payload in mutations:
            if op not in SUPPORTED_OPS:
                raise ValueError("Unsupported journal operation")
            prepared = redact_secrets(deepcopy(payload))
            if op == "event.add":
                for key, value in {"source_ids": [], "observed_at": ts,
                    "model_id": "unknown", "author": "unknown", "tool": "unknown",
                    "session_id": None, "evidence_status": "unknown"}.items():
                    prepared.setdefault(key, value)
                prepared["dedupe_key"] = event_dedupe_key(prepared)
            state = _apply_mutation(state, op, prepared)
            base = {"schema": JOURNAL_SCHEMA,
                    "journal_id": f"J-{verification['records'] + len(records) + 1:06d}",
                    "timestamp": ts, "op": op, "payload": prepared, "prev_hash": previous}
            record = dict(base, hash=_record_hash(base))
            previous = record["hash"]
            records.append(record)
        if any(x.get("severity") == "error" for x in audit_state(state)):
            raise ValueError("Batch would leave structurally invalid state")
        target = _active_segment_path_unlocked(root, create=True, label=segment_label)
        existing = journal_paths(root)
        if target.exists() and existing and existing[-1] != target:
            raise ValueError("Active segment is not the journal tail")
        prefix = target.read_bytes().decode("utf-8") if target.exists() else ""
        # Preserve all previous bytes; readers see the old or entire new segment.
        atomic_write_text(target, prefix + "".join(json.dumps(r, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")) + "\n" for r in records))
        return records


def append_mutation_set(project_root, op, payload, *, timestamp=None,
                        segment_label="runtime", lock_timeout=5.0):
    return append_mutation_batch(project_root, [(op, payload)], timestamp=timestamp,
        segment_label=segment_label, lock_timeout=lock_timeout)[0]
