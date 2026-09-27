"""Explicit, evidence-preserving normalized chat import (no inference or execution).

Input: {"sessions": [{"session_id": "stable-id", "title": "...",
 "source_uri": "export or share locator", "messages": [
 {"id": "stable-message-id", "role": "assistant", "text": "full text",
  "create_time": null, "metadata": {"model_slug": "model-id"},
  "node_id": "node", "parent_id": "parent"}]}]}.
All selected messages require explicit stable IDs, roles and string text. Extra
session/message fields are preserved. Dates remain exactly as supplied; missing
means unknown. Parent/node links are recorded, never interpreted as project forks.
Contents are reported claims, not verified facts; observation only establishes
presence in the supplied export. Text is retained without truncation, except
mandatory secret redaction. A changed redacted message becomes a new revision.

python evidence_import.py --root PROJECT --project-id ID --input export.json \
  --session-id CHAT_ID [--session-id OTHER_ID]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from project_history_agent import empty_state, render_markdown
from project_history_hooks import checkpoint
from project_history_journal import (ProjectLock, bootstrap_journal_from_state,
    journal_paths, redact_secrets, replay_journal_set, verify_journal_set,
    atomic_save_state, atomic_write_text)
from runtime_journal import append_mutation_set, append_mutation_batch


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def required_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be an explicit nonempty string")
    return value


def prepare(document: dict, session_ids: list[str]) -> list[dict]:
    if not session_ids:
        raise ValueError("explicit session_ids required")
    selected = {required_id(x, "session_id") for x in session_ids}
    if not isinstance(document, dict) or not isinstance(document.get("sessions"), list):
        raise ValueError("input requires sessions array")
    sessions = {}
    for session in document["sessions"]:
        if not isinstance(session, dict):
            raise ValueError("session must be object")
        sid = required_id(session.get("session_id"), "session_id")
        if sid in sessions:
            raise ValueError("duplicate session_id")
        sessions[sid] = session
    if selected - sessions.keys():
        raise ValueError("selected session_id absent from input")
    output = []
    for sid in sorted(selected):
        session = sessions[sid]
        messages = session.get("messages")
        if not isinstance(messages, list):
            raise ValueError("messages must be array")
        # Aggregate session text duplicates message bodies in normalized adapters.
        metadata = redact_secrets({k: v for k, v in session.items()
                                  if k not in {"messages", "text"}})
        metadata_revision = digest(metadata)
        session_source = {
            "source_id": "SRC-SESSION-" + digest([sid, metadata_revision]),
            "kind": "normalized_session_observation", "session_id": sid,
            "revision_hash": metadata_revision, "session_metadata": metadata,
            "locator": "normalized-chat:" + quote(sid, safe="") + "?metadata_revision=" + metadata_revision,
            "presence_status": "observed", "content_status": "reported",
        }
        seen = set()
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("message must be object")
            mid = required_id(message.get("id"), "message.id")
            if mid in seen:
                raise ValueError("duplicate message.id within session")
            seen.add(mid)
            required_id(message.get("role"), "message.role")
            if not isinstance(message.get("text"), str):
                raise ValueError("message.text must be string")
            if message.get("metadata") is not None and not isinstance(message["metadata"], dict):
                raise ValueError("message.metadata must be object")
            clean = redact_secrets(message)
            revision = digest(clean)
            identity = digest([sid, mid])
            source_id = "SRC-MSG-" + digest([sid, mid, revision])
            # Semantic pointer stays stable if an export reorders its messages.
            locator = {"session_id": sid, "message_id": mid, "revision": revision}
            source = {"source_id": source_id, "kind": "normalized_message",
                      "source_locator": locator,
                      "locator": "normalized-chat:" + quote(sid, safe="") + "/message/" + quote(mid, safe="") + "?revision=" + revision,
                      "session_metadata": metadata,
                      "message": clean, "presence_status": "observed",
                      "content_status": "reported", "redaction_applied": clean != message}
            event = {"event_id": "EV-MSG-" + digest([sid, mid, revision]),
                     "message_identity": identity, "revision_hash": revision,
                     "event_type": "message_record", "evidence_status": "reported",
                     "summary": f"Imported message {mid}; revision {revision}",
                     "text": clean["text"], "source_ids": [source_id],
                     "source_locator": locator, "session_id": sid,
                     "occurred_at": clean.get("create_time"),
                     "date_status": "reported" if clean.get("create_time") is not None else "unknown",
                     "author": clean["role"], "model_id": (clean.get("metadata") or {}).get("model_slug") or "unknown",
                     "node_id": clean.get("node_id"), "parent_id": clean.get("parent_id", clean.get("parent")),
                     "children": clean.get("children"),
                     "metadata": clean.get("metadata") or {},
                     "observation_scope": "Presence in supplied export only; content not verified"}
            output.append({"source": source, "event": event})
        output.append({"source": session_source, "event": None})
    return output


def import_sessions(root: Path | str, project_id: str, document: dict,
                    session_ids: list[str]) -> dict:
    required_id(project_id, "project_id")
    prepared = prepare(document, session_ids)  # validate everything before writes
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with ProjectLock(root / ".evidence-import.lock", timeout=30):
        if journal_paths(root):
            verification = verify_journal_set(root)
            if not verification["ok"]:
                raise ValueError("journal integrity failure")
            state = replay_journal_set(root)
            if state["project"]["project_id"] != project_id:
                raise ValueError("project_id mismatch")
        else:
            if (root / "PROJECT_MEMORY.json").exists():
                raise ValueError("snapshot without journal: explicit migration required")
            state = empty_state(project_id, project_id, "")
            bootstrap_journal_from_state(state, root / "PROJECT_HISTORY.events.jsonl")
        known_sources = {x["source_id"] for x in state["sources"]}
        known_events = {x["event_id"] for x in state["events"]}
        added = 0
        session_observations_added = 0
        mutated = False
        mutations = []
        for item in prepared:
            source, event = item["source"], item["event"]
            if event is None:
                if source["source_id"] not in known_sources:
                    mutations.append(("source.add", source))
                    known_sources.add(source["source_id"])
                    session_observations_added += 1
                    mutated = True
                continue
            if event["event_id"] in known_events:
                continue
            event["prior_revision_event_ids"] = [x["event_id"] for x in state["events"]
                if x.get("message_identity") == event["message_identity"]]
            if source["source_id"] not in known_sources:
                mutations.append(("source.add", source))
                known_sources.add(source["source_id"])
                mutated = True
            mutations.append(("event.add", event))
            known_events.add(event["event_id"])
            state["events"].append(event)
            added += 1
            mutated = True
        if mutated:
            append_mutation_batch(root, mutations, segment_label="import")
            checkpoint(root)
        else:
            # Recover snapshots after a crash between journal append and checkpoint.
            # No new journal record is needed for a projection repair.
            with ProjectLock(root / ".project-history.snapshot.lock", timeout=5):
                state = replay_journal_set(root)
                snapshot = root / "PROJECT_MEMORY.json"
                try:
                    matches = json.loads(snapshot.read_text(encoding="utf-8")) == state
                except (OSError, ValueError):
                    matches = False
                if not matches:
                    atomic_save_state(snapshot, state)
                report = root / "PROJECT_MEMORY.md"
                markdown = render_markdown(state)
                if not report.exists() or report.read_text(encoding="utf-8") != markdown:
                    atomic_write_text(report, markdown)
        return {"project_id": project_id, "selected_sessions": sorted(set(session_ids)),
                "messages_added": added, "messages_unchanged": sum(x["event"] is not None for x in prepared) - added,
                "session_observations_added": session_observations_added,
                "content_status": "reported", "semantic_analysis": "not_performed"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--session-id", required=True, action="append")
    args = parser.parse_args()
    try:
        result = import_sessions(args.root, args.project_id,
                                 json.loads(args.input.read_text(encoding="utf-8")), args.session_id)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Import rejected: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
