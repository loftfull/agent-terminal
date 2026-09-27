from __future__ import annotations

from copy import deepcopy

SUPPORTED_PROVIDERS = {"claude-code", "codex"}
SUPPORTED_NATIVE_EVENTS = {"SessionStart", "PreCompact", "SessionEnd"}


def _required(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"native hook field {key} is required")
    return str(value)


def normalize_hook_event(provider: str, payload: dict, project: dict) -> dict:
    provider = str(provider).strip().casefold()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported hook provider: {provider}")
    if not isinstance(payload, dict):
        raise ValueError("native hook payload must be a JSON object")
    if not isinstance(project, dict):
        raise ValueError("project identity must be a JSON object")

    event_name = _required(payload, "hook_event_name")
    if event_name not in SUPPORTED_NATIVE_EVENTS:
        raise ValueError(f"unsupported native hook event: {event_name}")
    session_id = _required(payload, "session_id")
    cwd = str(payload.get("cwd") or "").strip()
    transcript = payload.get("transcript_path")
    model = payload.get("model")

    common = {
        "provider": provider,
        "session_id": session_id,
        "source_locator": str(transcript) if transcript else f"{provider}:session:{session_id}",
        "tool": f"{provider}-hook",
    }
    if model:
        common["model_id"] = str(model)

    if event_name == "SessionStart":
        current = {
            "chat_id": session_id,
            "session_id": session_id,
            "title": f"{provider}:{session_id}",
            "paths": [cwd] if cwd else [],
            "repositories": [],
            "source_ids": [],
            "provider": provider,
        }
        out = {
            **common,
            "event": "session_start",
            "project": deepcopy(project),
            "current": current,
            "search_complete": False,
        }
        if payload.get("source") is not None:
            out["host_source"] = str(payload.get("source"))
        return out

    if event_name == "PreCompact":
        trigger = payload.get("trigger")
        summary = f"{provider} pre-compaction checkpoint"
        if trigger is not None:
            summary += f" (trigger: {trigger})"
        out = {
            **common,
            "event": "checkpoint",
            "reason": "pre_compaction",
            "summary": summary,
            "source_ids": [],
        }
        if trigger is not None:
            out["trigger"] = str(trigger)
        if payload.get("turn_id") is not None:
            out["turn_id"] = str(payload.get("turn_id"))
        return out

    out = {**common, "event": "session_end"}
    if payload.get("reason") is not None:
        out["end_reason"] = str(payload.get("reason"))
    return out
