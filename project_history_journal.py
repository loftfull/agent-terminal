from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import unquote_plus, urlsplit, urlunsplit

from project_history_agent import (
    add_chat,
    add_line,
    add_location,
    add_plan,
    add_source,
    add_version,
    add_visual,
    empty_state,
    ingest_event,
    event_dedupe_key,
)

JOURNAL_SCHEMA = "project-history-journal/v0.5"
SUPPORTED_OPS = {
    "project.patch",
    "source.add",
    "source.patch",
    "location.add",
    "location.patch",
    "chat.add",
    "chat.patch",
    "plan.add",
    "plan.patch",
    "version.add",
    "version.patch",
    "visual.add",
    "visual.patch",
    "line.add",
    "line.patch",
    "event.add",
    "search_queue.replace",
    "conflicts.replace",
    "handoff.patch",
}
SECRET_KEY_RE = re.compile(r"(?:^|[_-])(token|password|passwd|secret|api[_-]?key|authorization|cookie|credential)(?:$|[_-])", re.I)
SECRET_VALUE_PATTERNS = [
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+\-/]+=*", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{8,}\b", re.I),
]


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _redact_string(value: str) -> str:
    def scrub_url(match):
        raw = match.group(0)
        try:
            parts = urlsplit(raw)
            # Preserve IPv6 and ports without reconstructing hostname.
            host = parts.netloc.rsplit('@', 1)[-1]
            def scrub_params(text):
                fields = []
                for field in text.split('&'):
                    key, sep, val = field.partition('=')
                    fields.append(key + sep + ('[REDACTED]' if sep and SECRET_KEY_RE.search(unquote_plus(key)) else val))
                return '&'.join(fields)
            return urlunsplit((parts.scheme, host, parts.path,
                               scrub_params(parts.query), scrub_params(parts.fragment)))
        except ValueError:
            return '[REDACTED_URL]'
    result = re.sub(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s<>\"']+", scrub_url, value)
    result = re.sub(r"(?im)\b(?:set-cookie|cookie)\s*:[^\r\n]*", "Cookie: [REDACTED]", result)
    for pattern in SECRET_VALUE_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    # Recognizable assignments in free text, including quoted values with spaces.
    result = re.sub(
        r"\b([\w-]*(?:api[_-]?key|token|password|passwd|secret|authorization|credential)[\w-]*\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;&]+)",
        lambda m: m.group(1) + '[REDACTED]', result, flags=re.I)
    for pattern in SECRET_VALUE_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                out[key] = "[REDACTED]"
            else:
                out[key] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(x) for x in value]
    if isinstance(value, tuple):
        return [redact_secrets(x) for x in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


class ProjectLock:
    def __init__(self, path: Path | str, timeout: float = 5.0, poll_interval: float = 0.05, stale_after: float = 300.0):
        self.path = Path(path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.stale_after = stale_after
        self.acquired = False

    def __enter__(self):
        import portalocker
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = portalocker.Lock(str(self.path), mode="a+b", timeout=self.timeout,
                                     check_interval=self.poll_interval)
        try:
            self._lock.acquire()
        except portalocker.exceptions.LockException as exc:
            raise TimeoutError(f"project history lock busy: {self.path}") from exc
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.acquired:
            self._lock.release()
            self.acquired = False
        # Keep the inode: unlinking permits two independent locks at one pathname.


def atomic_write_text(path: Path | str, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=p.name + ".tmp.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, p)
        try:
            dir_fd = os.open(p.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_save_state(path: Path | str, state: Dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid journal JSON at line {line_no}: {exc}") from exc
    return records


def _record_hash(record_without_hash: Dict[str, Any]) -> str:
    prev_hash = record_without_hash.get("prev_hash") or ""
    return hashlib.sha256((prev_hash + "|" + _canonical(record_without_hash)).encode("utf-8")).hexdigest()


def append_mutation(path: Path | str, op: str, payload: Any, *, timestamp: str | None = None, lock_timeout: float = 5.0) -> Dict[str, Any]:
    if op not in SUPPORTED_OPS:
        raise ValueError(f"unsupported journal operation: {op}")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_path = p.parent / ".project-history.lock"
    with ProjectLock(lock_path, timeout=lock_timeout):
        records = _read_records(p)
        prev_hash = records[-1].get("hash", "") if records else ""
        state = replay_journal(p) if records else None
        ts = timestamp or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        prepared = redact_secrets(deepcopy(payload))
        if op == "event.add":
            prepared.setdefault("source_ids", [])
            prepared.setdefault("observed_at", ts)
            prepared.setdefault("model_id", "unknown")
            prepared.setdefault("author", "unknown")
            prepared.setdefault("tool", "unknown")
            prepared.setdefault("session_id", None)
            prepared.setdefault("evidence_status", "unknown")
            prepared["dedupe_key"] = event_dedupe_key(prepared)
        _apply_mutation(deepcopy(state), op, prepared)  # Preflight before writing bytes.
        base = {
            "schema": JOURNAL_SCHEMA,
            "journal_id": f"J-{len(records) + 1:06d}",
            "timestamp": ts,
            "op": op,
            "payload": prepared,
            "prev_hash": prev_hash,
        }
        record = dict(base)
        record["hash"] = _record_hash(base)
        with p.open("a", encoding="utf-8", newline="") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return record


def verify_journal(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    issues: list[dict] = []
    try:
        records = _read_records(p)
    except ValueError as exc:
        return {"ok": False, "records": 0, "issues": [{"code": "INVALID_JSON", "message": str(exc)}]}
    expected_prev = ""
    seen_ids: set[str] = set()
    for index, record in enumerate(records, 1):
        jid = record.get("journal_id") or f"line-{index}"
        if record.get("schema") != JOURNAL_SCHEMA:
            issues.append({"code": "SCHEMA_MISMATCH", "journal_id": jid})
        if jid in seen_ids:
            issues.append({"code": "DUPLICATE_JOURNAL_ID", "journal_id": jid})
        seen_ids.add(jid)
        if record.get("op") not in SUPPORTED_OPS:
            issues.append({"code": "UNKNOWN_OP", "journal_id": jid})
        if record.get("prev_hash", "") != expected_prev:
            issues.append({"code": "PREV_HASH_MISMATCH", "journal_id": jid})
        base = {k: v for k, v in record.items() if k != "hash"}
        calculated = _record_hash(base)
        if record.get("hash") != calculated:
            issues.append({"code": "HASH_MISMATCH", "journal_id": jid})
        expected_prev = record.get("hash", "")
    return {"ok": not issues, "records": len(records), "last_hash": expected_prev, "issues": issues}


def _patch_entity(state: Dict[str, Any], bucket: str, id_field: str, payload: Dict[str, Any]) -> None:
    identifier = payload.get(id_field)
    if not identifier:
        raise ValueError(f"{id_field} is required for patch")
    for item in state.get(bucket) or []:
        if item.get(id_field) == identifier:
            patch = deepcopy(payload)
            patch.pop(id_field, None)
            item.update(patch)
            return
    raise ValueError(f"cannot patch missing {bucket} entity {identifier}")


def _apply_mutation(state: Dict[str, Any] | None, op: str, payload: Any) -> Dict[str, Any]:
    if op == "project.patch":
        if state is None:
            state = empty_state(payload.get("project_id", "unknown"), payload.get("name", "unknown"), payload.get("goal", "unknown"))
            state.setdefault("handoff", {})["updated_at"] = None
        state["project"].update(deepcopy(payload))
        return state
    if state is None:
        raise ValueError("journal must begin with project.patch")
    if op == "source.add":
        add_source(state, payload)
    elif op == "source.patch":
        _patch_entity(state, "sources", "source_id", payload)
    elif op == "location.add":
        add_location(state, payload)
    elif op == "location.patch":
        _patch_entity(state, "locations", "location_id", payload)
    elif op == "chat.add":
        add_chat(state, payload)
    elif op == "chat.patch":
        _patch_entity(state, "chats", "chat_id", payload)
    elif op == "plan.add":
        add_plan(state, payload)
    elif op == "plan.patch":
        _patch_entity(state, "plans", "plan_id", payload)
    elif op == "version.add":
        add_version(state, payload)
    elif op == "version.patch":
        _patch_entity(state, "versions", "version_id", payload)
    elif op == "visual.add":
        add_visual(state, payload)
    elif op == "visual.patch":
        _patch_entity(state, "visuals", "visual_id", payload)
    elif op == "line.add":
        add_line(state, payload)
    elif op == "line.patch":
        _patch_entity(state, "development_lines", "line_id", payload)
    elif op == "event.add":
        ingest_event(state, payload)
    elif op == "search_queue.replace":
        state["search_queue"] = deepcopy(payload)
    elif op == "conflicts.replace":
        state["conflicts"] = deepcopy(payload)
    elif op == "handoff.patch":
        state.setdefault("handoff", {}).update(deepcopy(payload))
    else:
        raise ValueError(f"unsupported journal operation: {op}")
    return state


def journal_paths(project_root: Path | str) -> list[Path]:
    root = Path(project_root)
    base = root / "PROJECT_HISTORY.events.jsonl"
    paths: list[Path] = []
    if base.is_file():
        paths.append(base)
    seg_dir = root / "PROJECT_HISTORY.segments"
    if seg_dir.is_dir():
        paths.extend(sorted((x for x in seg_dir.glob("*.jsonl") if x.is_file()),
                            key=lambda x: (int(x.name.split("-", 1)[0]) if x.name.split("-", 1)[0].isdigit() else -1, x.name)))
    return paths


def verify_journal_set(project_root: Path | str) -> Dict[str, Any]:
    paths = journal_paths(project_root)
    if not paths:
        return {"ok": False, "records": 0, "last_hash": "", "issues": [{"code": "MISSING_JOURNAL"}], "segments": []}
    issues: list[dict] = []
    expected_prev = ""
    seen_ids: set[str] = set()
    record_count = 0
    segments: list[dict] = []
    for path in paths:
        try:
            records = _read_records(path)
        except ValueError as exc:
            issues.append({"code": "INVALID_JSON", "segment": str(path), "message": str(exc)})
            continue
        segments.append({"path": str(path), "records": len(records)})
        for record in records:
            record_count += 1
            jid = record.get("journal_id") or f"record-{record_count}"
            if record.get("schema") != JOURNAL_SCHEMA:
                issues.append({"code": "SCHEMA_MISMATCH", "journal_id": jid, "segment": str(path)})
            if jid in seen_ids:
                issues.append({"code": "DUPLICATE_JOURNAL_ID", "journal_id": jid, "segment": str(path)})
            seen_ids.add(jid)
            if record.get("op") not in SUPPORTED_OPS:
                issues.append({"code": "UNKNOWN_OP", "journal_id": jid, "segment": str(path)})
            if record.get("prev_hash", "") != expected_prev:
                issues.append({"code": "PREV_HASH_MISMATCH", "journal_id": jid, "segment": str(path)})
            base = {k: v for k, v in record.items() if k != "hash"}
            calculated = _record_hash(base)
            if record.get("hash") != calculated:
                issues.append({"code": "HASH_MISMATCH", "journal_id": jid, "segment": str(path)})
            expected_prev = record.get("hash", "")
    return {"ok": not issues, "records": record_count, "last_hash": expected_prev, "issues": issues, "segments": segments}


def replay_journal_set(project_root: Path | str) -> Dict[str, Any]:
    verification = verify_journal_set(project_root)
    if not verification["ok"]:
        codes = ",".join(x["code"] for x in verification["issues"])
        raise ValueError(f"journal set integrity failure: {codes}")
    state: Dict[str, Any] | None = None
    for path in journal_paths(project_root):
        for record in _read_records(path):
            state = _apply_mutation(state, record["op"], record.get("payload"))
    if state is None:
        raise ValueError("journal set is empty")
    return state


def replay_journal(path: Path | str) -> Dict[str, Any]:
    verification = verify_journal(path)
    if not verification["ok"]:
        codes = ",".join(x["code"] for x in verification["issues"])
        raise ValueError(f"journal integrity failure: {codes}")
    state: Dict[str, Any] | None = None
    for record in _read_records(Path(path)):
        state = _apply_mutation(state, record["op"], record.get("payload"))
    if state is None:
        raise ValueError("journal is empty")
    return state


def _state_mutations(state: Dict[str, Any]) -> Iterable[tuple[str, Any]]:
    yield "project.patch", state.get("project") or {}
    for key, op in [
        ("sources", "source.add"), ("locations", "location.add"), ("chats", "chat.add"),
        ("plans", "plan.add"), ("versions", "version.add"), ("visuals", "visual.add"),
        ("development_lines", "line.add"), ("events", "event.add"),
    ]:
        for item in state.get(key) or []:
            yield op, item
    yield "search_queue.replace", state.get("search_queue") or []
    yield "conflicts.replace", state.get("conflicts") or []
    yield "handoff.patch", state.get("handoff") or {}


def bootstrap_journal_from_state(state: Dict[str, Any], path: Path | str) -> None:
    """Publish the entire initial journal under the cooperative writer lock.

    Failure before rename leaves no journal. Failure after rename may have
    committed: callers must verify/replay, never delete and blindly retry.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with ProjectLock(p.parent / '.project-history.lock', timeout=5.0):
        if p.exists():
            raise FileExistsError(p)
        ts = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
        records = []
        replayed = None
        previous = ''
        for op, payload in _state_mutations(state):
            prepared = redact_secrets(deepcopy(payload))
            if op == 'event.add':
                for key, value in {'source_ids': [], 'observed_at': ts,
                    'model_id': 'unknown', 'author': 'unknown', 'tool': 'unknown',
                    'session_id': None, 'evidence_status': 'unknown'}.items():
                    prepared.setdefault(key, value)
                prepared['dedupe_key'] = event_dedupe_key(prepared)
            replayed = _apply_mutation(replayed, op, prepared)
            base = {'schema': JOURNAL_SCHEMA,
                    'journal_id': f'J-{len(records) + 1:06d}',
                    'timestamp': ts, 'op': op, 'payload': prepared,
                    'prev_hash': previous}
            record = dict(base, hash=_record_hash(base))
            previous = record['hash']
            records.append(record)
        atomic_write_text(p, ''.join(json.dumps(r, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')) + '\n' for r in records))
