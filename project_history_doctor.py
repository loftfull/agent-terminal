from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from project_history_auditor import audit_state
from host_history_discovery import HostHistoryDiscovery
from project_history_journal import ProjectLock, append_mutation, atomic_write_text, replay_journal_set, verify_journal_set


def _result(status: str, detail: str, **extra) -> dict:
    out = {"status": status, "detail": detail}
    out.update(extra)
    return out


def _semantic_state(state: dict) -> dict:
    return state


def _state_checks(root: Path) -> dict:
    """Read one generation; caller holds snapshot then journal lock."""
    checks = {}
    journal = root / "PROJECT_HISTORY.events.jsonl"
    verification = verify_journal_set(root)
    checks["journal_integrity"] = _result("PASS" if verification["ok"] else "FAIL", f"{verification.get('records', 0)} record(s)", issues=verification.get("issues", []))

    rebuilt = None
    if verification["ok"]:
        try:
            rebuilt = replay_journal_set(root)
            checks["journal_replay"] = _result("PASS", "journal replay succeeded")
        except Exception as exc:
            checks["journal_replay"] = _result("FAIL", str(exc))
    else:
        checks["journal_replay"] = _result("FAIL", "journal integrity prevents replay")

    snapshot_path = root / "PROJECT_MEMORY.json"
    if rebuilt is not None and snapshot_path.is_file():
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            match = _semantic_state(snapshot) == _semantic_state(rebuilt)
            checks["snapshot_replay_match"] = _result("PASS" if match else "FAIL", "snapshot matches journal replay" if match else "snapshot differs from journal replay")
        except Exception as exc:
            checks["snapshot_replay_match"] = _result("FAIL", str(exc))
    else:
        checks["snapshot_replay_match"] = _result("FAIL", "snapshot or replay unavailable")

    if rebuilt is not None:
        issues = audit_state(rebuilt)
        errors = [x for x in issues if x.get("severity") == "error"]
        checks["structural_audit"] = _result("PASS" if not errors else "FAIL", f"{len(errors)} structural error(s)", issues=issues)
    else:
        checks["structural_audit"] = _result("FAIL", "replayed state unavailable")

    return checks


def run_doctor(project_root: Path | str, adapter=None, history_discovery=None, probe_screenshot: bool = True) -> dict:
    root = Path(project_root)
    checks: dict[str, dict] = {}
    required = ["PROJECT_MEMORY.json", "PROJECT_MEMORY.md", "PROJECT_HISTORY.events.jsonl"]
    missing = [name for name in required if not (root / name).is_file()]
    checks["package_files"] = _result("FAIL" if missing else "PASS", "missing: " + ", ".join(missing) if missing else "required state files present")

    # Snapshot publishers already take the snapshot lock. Take it first, then
    # the writer lock, so replay and snapshot cannot cross a published generation.
    # A writer may have committed before its checkpoint: retry only a mismatch,
    # release both locks between attempts, and never repair or hide persistent lag.
    try:
        for attempt in range(3):
            with ProjectLock(root / ".project-history.snapshot.lock", timeout=5.0):
                with ProjectLock(root / ".project-history.lock", timeout=5.0):
                    state_checks = _state_checks(root)
            checks.update(state_checks)
            if (checks["snapshot_replay_match"]["status"] != "FAIL"
                    or checks["journal_integrity"]["status"] == "FAIL"):
                break
            if attempt < 2:
                time.sleep(0.05)
        checks["consistent_read"] = _result("PASS", "locked state observation", attempts=attempt + 1)
    except TimeoutError as exc:
        checks["consistent_read"] = _result("FAIL", str(exc))

    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".doctor-write-probe"
        atomic_write_text(probe, "probe\n")
        probe.unlink(missing_ok=True)
        checks["atomic_persistence"] = _result("PASS", "atomic write/replace available")
    except Exception as exc:
        checks["atomic_persistence"] = _result("FAIL", str(exc))

    try:
        redaction_probe = root / ".doctor-redaction-probe.jsonl"
        redaction_probe.unlink(missing_ok=True)
        append_mutation(redaction_probe, "project.patch", {"project_id": "doctor", "name": "Doctor", "goal": "probe", "api_key": "sk-doctor-secret-value", "authorization": "Bearer doctor.secret.token"})
        raw_probe = redaction_probe.read_text(encoding="utf-8")
        redaction_probe.unlink(missing_ok=True)
        if "sk-doctor-secret-value" in raw_probe or "doctor.secret.token" in raw_probe:
            checks["redaction_pipeline"] = _result("FAIL", "secret probe persisted unredacted")
        else:
            checks["redaction_pipeline"] = _result("PASS", "secret probe redacted before persistence")
    except Exception as exc:
        checks["redaction_pipeline"] = _result("FAIL", f"redaction probe failed: {exc}")

    discovery_report = None
    if adapter is None:
        discovery = history_discovery or HostHistoryDiscovery()
        try:
            discovery_report = discovery.discover()
            available = [x.get("provider") for x in discovery_report.get("sources", []) if x.get("status") == "available"]
            unavailable = {x.get("provider"): x.get("status") for x in discovery_report.get("sources", []) if x.get("status") != "available"}
            if available:
                checks["history_sources"] = _result("PASS", f"{len(available)} host history source(s) available", available=available, unavailable=unavailable)
                adapter = discovery.build_adapter(discovery_report)
            else:
                checks["history_sources"] = _result("WARN", "no host history source available", available=[], unavailable=unavailable)
        except Exception as exc:
            checks["history_sources"] = _result("WARN", f"host history discovery unavailable: {exc}")
    else:
        checks["history_sources"] = _result("PASS", "history adapter supplied explicitly", available=["explicit-adapter"], unavailable={})

    if adapter is None:
        checks["history_adapter"] = _result("WARN", "no usable history adapter configured or discovered")
    else:
        try:
            adapter.search("sessions", "", limit=1)
            checks["history_adapter"] = _result("PASS", "adapter search responded")
        except Exception as exc:
            checks["history_adapter"] = _result("WARN", f"adapter unavailable: {exc}")

    template_paths = {
        "claude-code": root / "integrations" / "claude-code" / "hooks.json",
        "codex": root / "integrations" / "codex" / "hooks.json",
    }
    present_templates = [provider for provider, path in template_paths.items() if path.is_file()]
    missing_templates = [provider for provider, path in template_paths.items() if not path.is_file()]
    checks["hook_templates"] = _result(
        "PASS" if not missing_templates else "WARN",
        "project-local hook templates present" if not missing_templates else "hook templates not generated for: " + ", ".join(missing_templates),
        authority="template_only",
        present=present_templates,
        missing=missing_templates,
    )

    if not probe_screenshot:
        checks["screenshot_capability"] = _result("PASS", "probe skipped by caller")
    else:
        try:
            import playwright  # noqa: F401
            chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
            checks["screenshot_capability"] = _result("PASS" if chromium else "WARN", "Playwright + system Chromium available" if chromium else "Playwright available; system Chromium not found")
        except Exception as exc:
            checks["screenshot_capability"] = _result("WARN", f"screenshot dependency unavailable: {exc}")

    statuses = {item["status"] for item in checks.values()}
    blocking_warns = {name for name, item in checks.items() if item["status"] == "WARN" and name not in {"hook_templates"}}
    overall = "FAIL" if "FAIL" in statuses else "WARN" if blocking_warns else "PASS"
    return {"overall": overall, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description="Project History Agent v0.7 doctor")
    ap.add_argument("project_root", nargs="?", default=".")
    ap.add_argument("--no-screenshot-probe", action="store_true")
    args = ap.parse_args()
    report = run_doctor(args.project_root, probe_screenshot=not args.no_screenshot_probe)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["overall"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
