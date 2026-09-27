from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from host_lifecycle_bridge import handle_lifecycle_event
from native_hook_adapters import normalize_hook_event


def _slug(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.").casefold()
    return out or "project"


def load_project_identity(root: Path) -> dict:
    snapshot = root / "PROJECT_MEMORY.json"
    if snapshot.is_file():
        try:
            state = json.loads(snapshot.read_text(encoding="utf-8"))
            project = state.get("project") if isinstance(state, dict) else None
            if isinstance(project, dict) and all(project.get(k) for k in ("project_id", "name", "goal")):
                return {k: project[k] for k in ("project_id", "name", "goal")}
        except (OSError, json.JSONDecodeError):
            pass

    config = root / "PROJECT_HISTORY_AGENT.config.json"
    if config.is_file():
        value = json.loads(config.read_text(encoding="utf-8"))
        project = value.get("project", value) if isinstance(value, dict) else {}
        if all(project.get(k) for k in ("project_id", "name", "goal")):
            return {k: project[k] for k in ("project_id", "name", "goal")}
        raise ValueError("PROJECT_HISTORY_AGENT.config.json requires project_id, name and goal")

    name = root.name or "Project"
    return {
        "project_id": _slug(name),
        "name": name,
        "goal": "Preserve evidence-based project history across AI sessions and development environments",
    }


def _project_root(payload: dict, explicit: Path | str | None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    env_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("PROJECT_HISTORY_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    cwd = payload.get("cwd")
    if cwd:
        return Path(str(cwd)).expanduser().resolve()
    return Path.cwd().resolve()


def _handoff_context(root: Path, max_chars: int = 3500) -> str:
    report = root / "PROJECT_MEMORY.md"
    if not report.is_file():
        return "Project History Agent initialized. Read PROJECT_MEMORY.md before continuing project work."
    text = report.read_text(encoding="utf-8")
    # Preserve the complete projection: user text may contain section markers.
    # max_chars is retained for call compatibility, not a hard truncation budget.
    compact = text.rstrip()
    return "Project History Agent handoff loaded. Read PROJECT_MEMORY.md for full evidence.\n\n" + compact


def _success_response(provider: str, normalized: dict, root: Path) -> dict:
    response = {"continue": True, "suppressOutput": True}
    if normalized.get("event") == "session_start":
        context = _handoff_context(root)
        response["suppressOutput"] = False
        if provider == "codex":
            response["hookSpecificOutput"] = {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        else:
            response["systemMessage"] = context
    return response


def run_native_hook(provider: str, payload: dict, *, project_root: Path | str | None = None, discovery=None, adapter=None) -> dict:
    provider = str(provider).strip().casefold()
    try:
        root = _project_root(payload if isinstance(payload, dict) else {}, project_root)
        root.mkdir(parents=True, exist_ok=True)
        project = load_project_identity(root)
        normalized = normalize_hook_event(provider, payload, project)
        lifecycle = handle_lifecycle_event(root, normalized, discovery=discovery, adapter=adapter)
        return {
            "hook_response": _success_response(provider, normalized, root),
            "lifecycle": lifecycle,
            "error": None,
            "project_root": str(root),
        }
    except Exception as exc:
        return {
            "hook_response": {
                "continue": True,
                "suppressOutput": False,
                "systemMessage": f"Project History Agent warning: {exc}",
            },
            "lifecycle": None,
            "error": str(exc),
            "project_root": str(project_root) if project_root is not None else None,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Native Claude Code / Codex lifecycle hook runner")
    ap.add_argument("--provider", required=True, choices=["claude-code", "codex"])
    ap.add_argument("--project-root")
    args = ap.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook stdin must be a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"continue": True, "suppressOutput": False, "systemMessage": f"Project History Agent warning: {exc}"}, ensure_ascii=False))
        return 0
    result = run_native_hook(args.provider, payload, project_root=args.project_root)
    print(json.dumps(result["hook_response"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
