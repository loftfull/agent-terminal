from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from history_adapters import InMemoryHistoryAdapter
from host_history_discovery import HostHistoryDiscovery
from project_history_agent import utc_now
from project_history_hooks import record_mutation, session_start, session_stop

SUPPORTED_LIFECYCLE_EVENTS = {"session_start", "checkpoint", "session_end"}


def _normalize_event_name(value: str | None) -> str:
    return (value or "").strip().casefold().replace("-", "_")


def _resolve_start_adapter(discovery=None, adapter=None):
    if adapter is not None:
        return adapter, None
    discovery = discovery or HostHistoryDiscovery()
    report = discovery.discover()
    resolved = discovery.build_adapter(report)
    return resolved or InMemoryHistoryAdapter([]), report


def handle_lifecycle_event(project_root: Path | str, payload: dict, *, discovery=None, adapter=None) -> dict:
    event = _normalize_event_name(payload.get("event"))
    if event not in SUPPORTED_LIFECYCLE_EVENTS:
        raise ValueError(f"unsupported lifecycle event: {payload.get('event')}")
    root = Path(project_root)

    if event == "session_start":
        project = payload.get("project") or {}
        current = payload.get("current") or {}
        for key in ("project_id", "name", "goal"):
            if not project.get(key):
                raise ValueError(f"session_start project.{key} is required")
        if not current.get("chat_id"):
            raise ValueError("session_start current.chat_id is required")
        resolved_adapter, report = _resolve_start_adapter(discovery=discovery, adapter=adapter)
        result = session_start(
            root,
            current,
            resolved_adapter,
            project_id=project["project_id"],
            name=project["name"],
            goal=project["goal"],
            search_complete=bool(payload.get("search_complete", False)),
        )
        return {
            "event": event,
            "lineage": result["lineage"],
            "candidates": result["candidates"],
            "state": result["state"],
            "discovery": report,
            "authority": "evidence-gated-lineage",
        }

    if event == "checkpoint":
        reason = str(payload.get("reason") or "checkpoint")
        summary = str(payload.get("summary") or f"Lifecycle checkpoint: {reason}")
        observed_at = utc_now()
        state = record_mutation(root, "event.add", {
            "event_type": "checkpoint",
            "occurred_at": observed_at.split("T", 1)[0],
            "observed_at": observed_at,
            "summary": summary,
            "source_locator": str(payload.get("source_locator") or f"lifecycle:{reason}"),
            "source_ids": list(payload.get("source_ids") or []),
            "evidence_status": "observed",
            "model_id": str(payload.get("model_id") or "unknown"),
            "author": str(payload.get("author") or "unknown"),
            "tool": str(payload.get("tool") or "host-lifecycle-bridge"),
            "session_id": payload.get("session_id"),
        })
        if payload.get("next_step") is not None:
            state = record_mutation(root, "handoff.patch", {"next_step": payload.get("next_step")})
        return {"event": event, "reason": reason, "state": state}

    state = session_stop(root, next_step=payload.get("next_step"))
    return {"event": event, "state": state}


def main() -> int:
    ap = argparse.ArgumentParser(description="Project History Agent host lifecycle bridge")
    ap.add_argument("project_root")
    ap.add_argument("--event-file", help="JSON lifecycle event file; stdin is used when omitted")
    args = ap.parse_args()
    try:
        if args.event_file:
            payload = json.loads(Path(args.event_file).read_text(encoding="utf-8"))
        else:
            payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("lifecycle payload must be a JSON object")
        result = handle_lifecycle_event(args.project_root, payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": "LIFECYCLE_EVENT_FAILED", "detail": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
