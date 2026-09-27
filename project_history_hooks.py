from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from project_history_agent import empty_state, initialize_chat_lineage, load_state, render_markdown, utc_now
from project_history_journal import (
    ProjectLock,
    atomic_save_state,
    atomic_write_text,
    bootstrap_journal_from_state,
    replay_journal_set,
    verify_journal_set,
)
from runtime_journal import append_mutation_set, begin_runtime_segment, close_runtime_segment

JOURNAL_NAME = "PROJECT_HISTORY.events.jsonl"
SNAPSHOT_NAME = "PROJECT_MEMORY.json"
REPORT_NAME = "PROJECT_MEMORY.md"


def _candidate_from_session(item: dict, by_session: dict[str, dict]) -> dict:
    candidate = {
        "chat_id": item.get("chat_id") or item.get("session_id"),
        "title": item.get("title"),
        "project_id": item.get("project_id"),
        "repositories": item.get("repositories") or [],
        "paths": item.get("paths") or [],
        "started_at": item.get("started_at"),
        "classification": item.get("classification", "unknown"),
        "source_ids": item.get("source_ids") or [],
        "evidence_strength": item.get("evidence_strength", "reported"),
        "session_id": item.get("session_id"),
    }
    parent_session = item.get("parent_session_id")
    if parent_session:
        parent = by_session.get(str(parent_session))
        candidate["parent_chat_id"] = (parent or {}).get("chat_id") or str(parent_session)
    elif item.get("parent_chat_id"):
        candidate["parent_chat_id"] = item.get("parent_chat_id")
    return candidate


def _discover_candidates(adapter, current: dict) -> list[dict]:
    query_parts = list(current.get("continuation_refs") or [])
    if not query_parts:
        query_parts.extend(current.get("repositories") or [])
    if not query_parts and current.get("project_id"):
        query_parts.append(current["project_id"])
    if not query_parts and current.get("title"):
        query_parts.append(current["title"])
    query = str(query_parts[0]) if query_parts else ""
    results = adapter.search("conversations", query, limit=50)
    by_session = {str(x.get("session_id")): x for x in results if x.get("session_id")}
    queue = [str(x.get("parent_session_id")) for x in results if x.get("parent_session_id")]
    while queue:
        sid = queue.pop(0)
        if sid in by_session:
            continue
        parent = adapter.inspect(sid)
        if parent is None:
            continue
        by_session[sid] = parent
        if parent.get("parent_session_id"):
            queue.append(str(parent["parent_session_id"]))
    return [_candidate_from_session(x, by_session) for x in by_session.values()]


def _ensure_root(root: Path | str) -> Path:
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def session_start(root: Path | str, current: dict, adapter, *, project_id: str, name: str, goal: str, search_complete: bool = False) -> dict:
    if current.get("project_id") not in (None, project_id):
        raise ValueError("Current chat project identity mismatch")
    root = _ensure_root(root)
    journal = root / JOURNAL_NAME
    snapshot = root / SNAPSHOT_NAME
    if journal.exists():
        state = replay_journal_set(root)
    elif snapshot.exists():
        state = load_state(snapshot)
        if state["project"]["project_id"] != project_id:
            raise ValueError("Project identity mismatch")
        bootstrap_journal_from_state(state, journal)
    else:
        state = empty_state(project_id, name, goal)

    if state["project"]["project_id"] != project_id:
        raise ValueError("Project identity mismatch")
    before_chat_ids = {x.get("chat_id") for x in state.get("chats") or []}
    candidates = _discover_candidates(adapter, current)
    lineage = initialize_chat_lineage(state, current, candidates, search_complete=search_complete)

    if not journal.exists():
        bootstrap_journal_from_state(state, journal)
    else:
        begin_runtime_segment(root)
        for chat in state.get("chats") or []:
            if chat.get("chat_id") not in before_chat_ids:
                append_mutation_set(root, "chat.add", chat)
        append_mutation_set(root, "handoff.patch", {"current_chat_id": current["chat_id"]})
    state = checkpoint(root)
    return {"lineage": lineage, "state": state, "candidates": candidates}


def record_mutation(root: Path | str, op: str, payload: Any) -> dict:
    root = _ensure_root(root)
    append_mutation_set(root, op, payload)
    return checkpoint(root)


def checkpoint(root: Path | str) -> dict:
    root = _ensure_root(root)
    journal = root / JOURNAL_NAME
    verification = verify_journal_set(root)
    if not verification["ok"]:
        raise ValueError(f"journal verification failed: {verification['issues']}")
    append_mutation_set(root, "handoff.patch", {"updated_at": utc_now()})
    lock_path = root / ".project-history.snapshot.lock"
    with ProjectLock(lock_path, timeout=5.0):
        state = replay_journal_set(root)
        atomic_save_state(root / SNAPSHOT_NAME, state)
        atomic_write_text(root / REPORT_NAME, render_markdown(state))
    return state


def session_stop(root: Path | str, *, next_step: str | None = None) -> dict:
    patch = {"updated_at": utc_now()}
    if next_step is not None:
        patch["next_step"] = next_step
    root = _ensure_root(root)
    append_mutation_set(root, "handoff.patch", patch)
    state = checkpoint(root)
    close_runtime_segment(root)
    return state
