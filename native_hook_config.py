from __future__ import annotations

import json
import shlex
from pathlib import Path

LIFECYCLE_EVENTS = ("SessionStart", "PreCompact", "SessionEnd")


def _hook_entries(command: str) -> list[dict]:
    return [{
        "hooks": [{
            "type": "command",
            "command": command,
            "timeout": 30,
        }]
    }]


def claude_plugin_hooks(python_command: str = "python") -> dict:
    """Return a project-scoped Claude Code hook template.

    This function only renders configuration. It does not modify Claude settings.
    """
    runner = '"$CLAUDE_PROJECT_DIR/native_hook_runner.py"'
    root = '"$CLAUDE_PROJECT_DIR"'
    command = f"{python_command} {runner} --provider claude-code --project-root {root}"
    return {
        "description": "Project History Agent lifecycle memory hooks",
        "hooks": {event: _hook_entries(command) for event in LIFECYCLE_EVENTS},
    }


def codex_hooks(project_root: Path | str, python_command: str = "python") -> dict:
    """Return a Codex hooks.json template for one explicit project root.

    The returned object mirrors Codex's confirmed hooks.json wrapper and is not
    written into the user's Codex home by this function.
    """
    root = Path(project_root).expanduser().resolve()
    runner = root / "native_hook_runner.py"
    command = " ".join([
        shlex.quote(python_command),
        shlex.quote(str(runner)),
        "--provider",
        "codex",
        "--project-root",
        shlex.quote(str(root)),
    ])
    return {"hooks": {event: _hook_entries(command) for event in LIFECYCLE_EVENTS}}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_hook_templates(project_root: Path | str, python_command: str = "python") -> dict:
    """Write safe, reviewable templates inside the project only.

    Authority is deliberately template-only: this never edits `.claude/settings.json`,
    `$CODEX_HOME/hooks.json`, or any other host/global configuration.
    """
    root = Path(project_root).expanduser().resolve()
    claude_path = root / "integrations" / "claude-code" / "hooks.json"
    codex_path = root / "integrations" / "codex" / "hooks.json"
    _write_json(claude_path, claude_plugin_hooks(python_command=python_command))
    _write_json(codex_path, codex_hooks(root, python_command=python_command))
    return {
        "authority": "template_only",
        "project_root": str(root),
        "templates": {
            "claude-code": str(claude_path),
            "codex": str(codex_path),
        },
        "host_configuration_modified": False,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Render Project History Agent native hook templates without installing them")
    sub = ap.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="write project-local Claude Code and Codex hook templates")
    write.add_argument("project_root", nargs="?", default=".")
    write.add_argument("--python-command", default="python")
    args = ap.parse_args()

    if args.command == "write":
        result = write_hook_templates(args.project_root, python_command=args.python_command)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
