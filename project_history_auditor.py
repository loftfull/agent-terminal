from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

EXPECTED_SCHEMA = "project-history-state/v0.5"
LINEAGE_EDGE_TYPES = {"continues", "forked_from", "supersedes"}


def _issue(code: str, message: str, severity: str = "error", ref: str | None = None) -> Dict[str, Any]:
    out = {"code": code, "message": message, "severity": severity}
    if ref is not None:
        out["ref"] = ref
    return out


def _check_sources(issues: List[Dict[str, Any]], source_ids: set[str], refs: List[str], code: str, label: str, ref: str) -> None:
    for sid in refs or []:
        if sid not in source_ids:
            issues.append(_issue(code, f"{label} {ref} references unknown source {sid}", ref=ref))


def _has_directed_cycle(graph: Dict[str, List[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(dfs(node) for node in graph if node not in visited)


def audit_state(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    if state.get("schema") != EXPECTED_SCHEMA:
        issues.append(_issue("SCHEMA_MISMATCH", f"expected {EXPECTED_SCHEMA}, got {state.get('schema')!r}"))

    project = state.get("project") or {}
    if not project.get("project_id"):
        issues.append(_issue("MISSING_PROJECT_ID", "project.project_id is required"))
    if not project.get("name"):
        issues.append(_issue("MISSING_PROJECT_NAME", "project.name is required"))

    source_ids: set[str] = set()
    for src in state.get("sources") or []:
        sid = src.get("source_id")
        if not sid:
            issues.append(_issue("MISSING_SOURCE_ID", "source without source_id"))
            continue
        if sid in source_ids:
            issues.append(_issue("DUPLICATE_SOURCE_ID", f"duplicate source_id {sid}", ref=sid))
        source_ids.add(sid)

    event_ids: set[str] = set()
    event_keys: set[str] = set()
    for ev in state.get("events") or []:
        eid = ev.get("event_id") or "<unknown-event>"
        if eid in event_ids:
            issues.append(_issue("DUPLICATE_EVENT_ID", f"duplicate event_id {eid}", ref=eid))
        event_ids.add(eid)
        key = ev.get("dedupe_key")
        if not key:
            issues.append(_issue("MISSING_EVENT_KEY", f"event {eid} lacks dedupe_key", ref=eid))
        elif key in event_keys:
            issues.append(_issue("DUPLICATE_EVENT_KEY", f"duplicate dedupe_key {key}", ref=eid))
        if key:
            event_keys.add(key)
        refs = ev.get("source_ids") or []
        if ev.get("evidence_status") == "verified" and not refs:
            issues.append(_issue("VERIFIED_WITHOUT_SOURCE", f"verified event {eid} has no sources", ref=eid))
        _check_sources(issues, source_ids, refs, "EVENT_SOURCE_NOT_FOUND", "event", eid)

    location_ids: set[str] = set()
    location_keys: set[str] = set()
    for loc in state.get("locations") or []:
        lid = loc.get("location_id") or "<unknown-location>"
        if lid in location_ids:
            issues.append(_issue("DUPLICATE_LOCATION_ID", f"duplicate location_id {lid}", ref=lid))
        location_ids.add(lid)
        key = loc.get("location_key")
        if key:
            if key in location_keys:
                issues.append(_issue("DUPLICATE_LOCATION_KEY", f"duplicate location_key {key}", ref=lid))
            location_keys.add(key)
        if loc.get("observed_now") and not loc.get("checked_at"):
            issues.append(_issue("OBSERVED_NOW_WITHOUT_CHECKED_AT", f"location {lid} is observed_now without checked_at", ref=lid))
        _check_sources(issues, source_ids, loc.get("source_ids") or [], "LOCATION_SOURCE_NOT_FOUND", "location", lid)

    line_map: Dict[str, Dict[str, Any]] = {}
    for line in state.get("development_lines") or []:
        lid = line.get("line_id")
        if not lid:
            issues.append(_issue("MISSING_LINE_ID", "development line without line_id"))
            continue
        if lid in line_map:
            issues.append(_issue("DUPLICATE_LINE_ID", f"duplicate line_id {lid}", ref=lid))
        line_map[lid] = line
        if line.get("status") == "dead_end" and not line.get("stop_decision_source_ids"):
            issues.append(_issue("DEAD_END_WITHOUT_DECISION_SOURCE", f"dead_end line {lid} lacks stop_decision_source_ids", ref=lid))
        _check_sources(issues, source_ids, line.get("stop_decision_source_ids") or [], "DEAD_END_SOURCE_NOT_FOUND", "line", lid)

    for lid, line in line_map.items():
        for rel in line.get("relations") or []:
            target = rel.get("target")
            if target and target not in line_map:
                issues.append(_issue("RELATION_TARGET_NOT_FOUND", f"line {lid} targets missing line {target}", ref=lid))
            _check_sources(issues, source_ids, rel.get("source_ids") or [], "RELATION_SOURCE_NOT_FOUND", "relation on line", lid)

    graph: Dict[str, List[str]] = {lid: [] for lid in line_map}
    for lid, line in line_map.items():
        for rel in line.get("relations") or []:
            if rel.get("type") in LINEAGE_EDGE_TYPES and rel.get("target") in line_map:
                graph[lid].append(rel["target"])
    if _has_directed_cycle(graph):
        issues.append(_issue("LINEAGE_CYCLE", "ancestry-like development-line relations contain a cycle"))

    chat_map: Dict[str, Dict[str, Any]] = {}
    for chat in state.get("chats") or []:
        cid = chat.get("chat_id")
        if not cid:
            issues.append(_issue("MISSING_CHAT_ID", "chat without chat_id"))
            continue
        if cid in chat_map:
            issues.append(_issue("DUPLICATE_CHAT_ID", f"duplicate chat_id {cid}", ref=cid))
        chat_map[cid] = chat
        if chat.get("classification") == "new" and chat.get("parent_chat_id"):
            issues.append(_issue("NEW_CHAT_HAS_PARENT", f"new chat {cid} cannot have parent_chat_id", ref=cid))
        if chat.get("classification") == "continuation" and not chat.get("parent_chat_id"):
            issues.append(_issue("CONTINUATION_CHAT_WITHOUT_PARENT", f"continuation chat {cid} must identify parent_chat_id", ref=cid))
        _check_sources(issues, source_ids, chat.get("source_ids") or [], "CHAT_SOURCE_NOT_FOUND", "chat", cid)
    chat_graph: Dict[str, List[str]] = {cid: [] for cid in chat_map}
    for cid, chat in chat_map.items():
        parent = chat.get("parent_chat_id")
        if parent:
            if parent not in chat_map:
                issues.append(_issue("CHAT_PARENT_NOT_FOUND", f"chat {cid} parent {parent} does not exist", ref=cid))
            else:
                chat_graph[cid].append(parent)
    if _has_directed_cycle(chat_graph):
        issues.append(_issue("CHAT_LINEAGE_CYCLE", "chat continuation lineage contains a cycle"))

    plan_ids: set[str] = set()
    for plan in state.get("plans") or []:
        pid = plan.get("plan_id")
        if not pid:
            issues.append(_issue("MISSING_PLAN_ID", "plan without plan_id"))
            continue
        if pid in plan_ids:
            issues.append(_issue("DUPLICATE_PLAN_ID", f"duplicate plan_id {pid}", ref=pid))
        plan_ids.add(pid)
        _check_sources(issues, source_ids, plan.get("source_ids") or [], "PLAN_SOURCE_NOT_FOUND", "plan", pid)

    version_ids: set[str] = set()
    for version in state.get("versions") or []:
        vid = version.get("version_id")
        if not vid:
            issues.append(_issue("MISSING_VERSION_ID", "version without version_id"))
            continue
        if vid in version_ids:
            issues.append(_issue("DUPLICATE_VERSION_ID", f"duplicate version_id {vid}", ref=vid))
        version_ids.add(vid)
        _check_sources(issues, source_ids, version.get("source_ids") or [], "VERSION_SOURCE_NOT_FOUND", "version", vid)
        for pid in version.get("plan_ids") or []:
            if pid not in plan_ids:
                issues.append(_issue("VERSION_PLAN_NOT_FOUND", f"version {vid} references missing plan {pid}", ref=vid))

    visual_ids: set[str] = set()
    for visual in state.get("visuals") or []:
        iid = visual.get("visual_id")
        if not iid:
            issues.append(_issue("MISSING_VISUAL_ID", "visual without visual_id"))
            continue
        if iid in visual_ids:
            issues.append(_issue("DUPLICATE_VISUAL_ID", f"duplicate visual_id {iid}", ref=iid))
        visual_ids.add(iid)
        version_id = visual.get("version_id")
        if version_id and version_id not in version_ids:
            issues.append(_issue("VISUAL_VERSION_NOT_FOUND", f"visual {iid} references missing version {version_id}", ref=iid))
        if visual.get("observed_now") and not visual.get("captured_at"):
            issues.append(_issue("VISUAL_OBSERVED_NOW_WITHOUT_CAPTURE", f"visual {iid} observed_now without captured_at", ref=iid))
        if visual.get("observed_now") and not visual.get("uri"):
            issues.append(_issue("VISUAL_OBSERVED_NOW_WITHOUT_URI", f"visual {iid} observed_now without uri", ref=iid))
        _check_sources(issues, source_ids, visual.get("source_ids") or [], "VISUAL_SOURCE_NOT_FOUND", "visual", iid)

    handoff_chat = (state.get("handoff") or {}).get("current_chat_id")
    if handoff_chat and handoff_chat not in chat_map:
        issues.append(_issue("HANDOFF_CURRENT_CHAT_NOT_FOUND", f"handoff current_chat_id {handoff_chat} not found", ref=handoff_chat))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Independent structural auditor for Project History Agent state")
    ap.add_argument("state")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    issues = audit_state(state)
    errors = [x for x in issues if x.get("severity") == "error"]
    if args.json:
        print(json.dumps({"errors": len(errors), "issues": issues}, ensure_ascii=False, indent=2))
    else:
        if issues:
            for item in issues:
                print(f"{item['severity'].upper()} {item['code']}: {item['message']}")
        else:
            print("AUDIT PASS: no structural issues")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
