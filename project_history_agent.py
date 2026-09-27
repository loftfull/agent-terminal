from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

SCHEMA = "project-history-state/v0.5"
EVIDENCE_STATUSES = {"requested", "planned", "reported", "observed", "verified", "inferred", "unknown"}
RELATION_TYPES = {"continues", "forked_from", "merged_into", "supersedes", "inspired_by", "possibly_related"}
CHAT_CLASSIFICATIONS = {"new", "continuation", "unknown"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def evidence_date_key(value: Any) -> tuple:
    """Order known instants safely; preserve unknown/naive dates without inventing UTC."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return (0, float(value), '')
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is not None:
                return (0, parsed.timestamp(), '')
            return (1, 0.0, value)  # local/day-only date, timezone not established
        except (ValueError, OverflowError, OSError):
            return (2, 0.0, value)
    return (3, 0.0, '')


def empty_state(project_id: str, name: str, goal: str) -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "project": {
            "project_id": project_id,
            "name": name,
            "description": "",
            "goal": goal,
            "canonical_version": None,
            "constraints": [],
        },
        "sources": [],
        "locations": [],
        "chats": [],
        "plans": [],
        "versions": [],
        "visuals": [],
        "development_lines": [],
        "events": [],
        "search_queue": [],
        "conflicts": [],
        "handoff": {"current_chat_id": None, "next_step": None, "updated_at": utc_now()},
    }


def load_state(path: Path | str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_state(path: Path | str, state: Dict[str, Any]) -> None:
    """Compatibility snapshot writer. Journal-backed flows should use hooks/checkpoint.

    The write itself is atomic; callers that need recoverability must also append the
    corresponding mutation to PROJECT_HISTORY.events.jsonl.
    """
    state.setdefault("handoff", {})["updated_at"] = utc_now()
    from project_history_journal import atomic_save_state
    atomic_save_state(path, state)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _norm_identifier(value: str | None) -> str:
    return (value or "").strip().casefold()


def _norm_repo(value: str) -> str:
    v = value.strip().rstrip("/")
    if v.endswith(".git"):
        v = v[:-4]
    return v.casefold()


def _set(values: Iterable[str] | None, normalizer=_norm_identifier) -> set[str]:
    return {normalizer(v) for v in (values or []) if v}


def event_dedupe_key(event: Dict[str, Any]) -> str:
    material = {
        "event_type": event.get("event_type"),
        "occurred_at": event.get("occurred_at"),
        "summary": event.get("summary"),
        "source_locator": event.get("source_locator"),
        "source_ids": sorted(event.get("source_ids") or []),
    }
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def ingest_event(state: Dict[str, Any], event: Dict[str, Any]) -> bool:
    status = event.get("evidence_status", "unknown")
    if status not in EVIDENCE_STATUSES:
        raise ValueError(f"invalid evidence_status: {status}")
    normalized = dict(event)
    normalized["evidence_status"] = status
    normalized.setdefault("source_ids", [])
    normalized.setdefault("observed_at", utc_now())
    normalized.setdefault("model_id", "unknown")
    normalized.setdefault("author", "unknown")
    normalized.setdefault("tool", "unknown")
    normalized.setdefault("session_id", None)
    normalized["dedupe_key"] = event_dedupe_key(normalized)
    if any(existing.get("dedupe_key") == normalized["dedupe_key"] for existing in state.setdefault("events", [])):
        return False
    normalized.setdefault("event_id", f"EV-{len(state['events']) + 1:05d}")
    state["events"].append(normalized)
    return True


def _location_key(location: Dict[str, Any]) -> str:
    material = {
        "kind": location.get("kind"),
        "uri": location.get("uri"),
        "device_id": location.get("device_id"),
        "branch": location.get("branch"),
        "sha": location.get("sha"),
    }
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def add_location(state: Dict[str, Any], location: Dict[str, Any]) -> bool:
    normalized = dict(location)
    normalized.setdefault("observed_now", False)
    normalized.setdefault("observation_status", "mentioned")
    normalized.setdefault("source_ids", [])
    normalized["location_key"] = _location_key(normalized)
    locations = state.setdefault("locations", [])
    if any(x.get("location_key") == normalized["location_key"] for x in locations):
        return False
    normalized.setdefault("location_id", f"LOC-{len(locations) + 1:04d}")
    locations.append(normalized)
    return True


def add_line(state: Dict[str, Any], line: Dict[str, Any]) -> bool:
    normalized = dict(line)
    if not normalized.get("line_id"):
        raise ValueError("line_id is required")
    normalized.setdefault("relations", [])
    for relation in normalized["relations"]:
        if relation.get("type") not in RELATION_TYPES:
            raise ValueError(f"invalid relation type: {relation.get('type')}")
    lines = state.setdefault("development_lines", [])
    if any(x.get("line_id") == normalized["line_id"] for x in lines):
        return False
    lines.append(normalized)
    return True


def add_source(state: Dict[str, Any], source: Dict[str, Any]) -> bool:
    normalized = dict(source)
    sources = state.setdefault("sources", [])
    if not normalized.get("source_id"):
        normalized["source_id"] = f"S{len(sources) + 1:03d}"
    if any(x.get("source_id") == normalized["source_id"] for x in sources):
        return False
    sources.append(normalized)
    return True


def add_chat(state: Dict[str, Any], chat: Dict[str, Any]) -> bool:
    normalized = dict(chat)
    chat_id = normalized.get("chat_id")
    if not chat_id:
        raise ValueError("chat_id is required")
    classification = normalized.get("classification", "unknown")
    if classification not in CHAT_CLASSIFICATIONS:
        raise ValueError(f"invalid chat classification: {classification}")
    if classification == "new" and normalized.get("parent_chat_id"):
        raise ValueError("new chat cannot have parent_chat_id")
    normalized["classification"] = classification
    normalized.setdefault("source_ids", [])
    normalized.setdefault("evidence_strength", "unknown")
    chats = state.setdefault("chats", [])
    if any(x.get("chat_id") == chat_id for x in chats):
        return False
    chats.append(normalized)
    return True


def detect_chat_lineage(current: Dict[str, Any], candidates: List[Dict[str, Any]], search_complete: bool = False) -> Dict[str, Any]:
    """Deterministically classify the current chat from host-extracted identifiers.

    This function does not search conversations. It only judges evidence supplied by the host.
    """
    refs = _set(current.get("continuation_refs"))
    for candidate in candidates:
        cid = _norm_identifier(candidate.get("chat_id"))
        title = _norm_identifier(candidate.get("title"))
        if cid in refs or title in refs:
            return {
                "classification": "continuation",
                "parent_chat_id": candidate.get("chat_id"),
                "evidence_strength": "explicit",
                "evidence": ["explicit_continuation_reference"],
            }

    if current.get("new_project") is True:
        return {"classification": "new", "parent_chat_id": None, "evidence_strength": "explicit", "evidence": ["explicit_new_project"]}

    current_project = _norm_identifier(current.get("project_id"))
    current_repos = _set(current.get("repositories"), _norm_repo)
    current_paths = _set(current.get("paths"))
    weak_match = False

    for candidate in candidates:
        candidate_project = _norm_identifier(candidate.get("project_id"))
        repo_overlap = bool(current_repos & _set(candidate.get("repositories"), _norm_repo))
        path_overlap = bool(current_paths & _set(candidate.get("paths")))
        project_match = bool(current_project and candidate_project and current_project == candidate_project)
        if project_match and (repo_overlap or path_overlap):
            evidence = ["same_project_id"]
            if repo_overlap:
                evidence.append("same_repository")
            if path_overlap:
                evidence.append("same_local_path")
            return {
                "classification": "continuation",
                "parent_chat_id": candidate.get("chat_id"),
                "evidence_strength": "corroborated",
                "evidence": evidence,
            }
        if repo_overlap or path_overlap or project_match:
            weak_match = True

    if weak_match:
        return {"classification": "unknown", "parent_chat_id": None, "evidence_strength": "possibly_related", "evidence": ["insufficient_stable_identity"]}
    if search_complete:
        return {"classification": "new", "parent_chat_id": None, "evidence_strength": "searched_no_match", "evidence": ["bounded_search_complete_no_match"]}
    return {"classification": "unknown", "parent_chat_id": None, "evidence_strength": "unknown", "evidence": ["search_incomplete"]}


def initialize_chat_lineage(state: Dict[str, Any], current: Dict[str, Any], candidates: List[Dict[str, Any]], search_complete: bool = False) -> Dict[str, Any]:
    """Classify a first-run chat and persist the available continuation chain.

    Candidate chats are host-retrieved evidence. The function never searches hidden
    conversation history itself; it only records candidates that are needed for the
    resolved parent chain plus the current chat.
    """
    result = detect_chat_lineage(current, candidates, search_complete=search_complete)
    by_id = {item.get("chat_id"): item for item in candidates if item.get("chat_id")}

    parent_id = result.get("parent_chat_id")
    lineage_to_add: List[Dict[str, Any]] = []
    seen: set[str] = set()
    cursor = parent_id
    while cursor:
        if cursor in seen:
            raise ValueError("candidate chat lineage cycle")
        seen.add(cursor)
        candidate = by_id.get(cursor)
        if candidate is None:
            raise ValueError(f"candidate parent not found: {cursor}")
        lineage_to_add.append(candidate)
        cursor = candidate.get("parent_chat_id")
    lineage_to_add.reverse()
    for candidate in lineage_to_add:
        add_chat(state, candidate)

    current_record = dict(current)
    current_record.update({
        "classification": result["classification"],
        "parent_chat_id": result.get("parent_chat_id"),
        "evidence_strength": result.get("evidence_strength", "unknown"),
        "lineage_evidence": result.get("evidence", []),
    })
    add_chat(state, current_record)
    state.setdefault("handoff", {})["current_chat_id"] = current_record["chat_id"]
    return result


def build_chat_chain(state: Dict[str, Any], current_chat_id: str) -> List[Dict[str, Any]]:
    chat_map = {x.get("chat_id"): x for x in state.get("chats", []) if x.get("chat_id")}
    if current_chat_id not in chat_map:
        raise KeyError(current_chat_id)
    chain: List[Dict[str, Any]] = []
    seen: set[str] = set()
    cursor: str | None = current_chat_id
    while cursor:
        if cursor in seen:
            raise ValueError("chat lineage cycle")
        seen.add(cursor)
        chat = chat_map.get(cursor)
        if chat is None:
            raise ValueError(f"chat lineage parent not found: {cursor}")
        chain.append(chat)
        cursor = chat.get("parent_chat_id")
    chain.reverse()
    return chain


def _add_unique(state: Dict[str, Any], bucket: str, id_field: str, value: Dict[str, Any]) -> bool:
    normalized = dict(value)
    identifier = normalized.get(id_field)
    if not identifier:
        raise ValueError(f"{id_field} is required")
    values = state.setdefault(bucket, [])
    if any(x.get(id_field) == identifier for x in values):
        return False
    normalized.setdefault("source_ids", [])
    values.append(normalized)
    return True


def add_plan(state: Dict[str, Any], plan: Dict[str, Any]) -> bool:
    normalized = dict(plan)
    normalized.setdefault("status", "planned")
    normalized.setdefault("items", [])
    return _add_unique(state, "plans", "plan_id", normalized)


def add_version(state: Dict[str, Any], version: Dict[str, Any]) -> bool:
    normalized = dict(version)
    status = normalized.get("evidence_status", "reported")
    if status not in EVIDENCE_STATUSES:
        raise ValueError(f"invalid evidence_status: {status}")
    normalized["evidence_status"] = status
    normalized.setdefault("changes", [])
    normalized.setdefault("plan_ids", [])
    return _add_unique(state, "versions", "version_id", normalized)


def add_visual(state: Dict[str, Any], visual: Dict[str, Any]) -> bool:
    normalized = dict(visual)
    normalized.setdefault("kind", "screenshot")
    normalized.setdefault("observed_now", False)
    normalized.setdefault("observation_status", "reported")
    return _add_unique(state, "visuals", "visual_id", normalized)


def capture_visual(url: str, output_path: Path | str, viewport: Dict[str, int] | None = None, timeout_ms: int = 30000) -> Dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("capture_visual accepts only http/https URLs")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    viewport = viewport or {"width": 1440, "height": 900}
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not available for screenshot capture") from exc

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as primary_exc:
            system_chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
            if not system_chromium:
                raise RuntimeError("No Playwright-managed or system Chromium executable is available") from primary_exc
            browser = p.chromium.launch(headless=True, executable_path=system_chromium, args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport=viewport)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.screenshot(path=str(output), full_page=True)
        finally:
            browser.close()
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("screenshot capture did not produce a file")
    return {"url": url, "path": str(output), "captured_at": utc_now(), "viewport": viewport, "size_bytes": output.stat().st_size}


def _run_git(root: Path, *args: str) -> str | None:
    try:
        cp = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if cp.returncode != 0:
        return None
    return cp.stdout.strip()


def scan_local_project(root: Path | str) -> Dict[str, Any]:
    root = Path(root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(root)
    snapshot: Dict[str, Any] = {"root": str(root), "checked_at": utc_now(), "git": None, "key_docs": []}
    git_root = _run_git(root, "rev-parse", "--show-toplevel")
    if git_root:
        branch = _run_git(root, "branch", "--show-current") or None
        head = _run_git(root, "rev-parse", "HEAD") or None
        remote_lines = _run_git(root, "remote", "-v") or ""
        remotes = []
        for line in remote_lines.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] not in remotes:
                remotes.append(parts[1])
        worktree_lines = _run_git(root, "worktree", "list", "--porcelain") or ""
        worktrees = [line.split(" ", 1)[1] for line in worktree_lines.splitlines() if line.startswith("worktree ")]
        status = _run_git(root, "status", "--porcelain=v1")
        snapshot["git"] = {"root": git_root, "branch": branch, "head": head, "remotes": remotes, "worktrees": worktrees, "dirty": bool(status)}
    candidates = [
        "README.md", "PROJECT_HANDOFF.md", "START_HERE.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
        "PROJECT_HISTORY_AGENT.md", "PROJECT_MEMORY.md", "PROJECT_MEMORY.json", "package.json", "pyproject.toml",
    ]
    for name in candidates:
        p = root / name
        if p.is_file():
            snapshot["key_docs"].append(name)
    docs = root / "docs"
    if docs.is_dir():
        for p in sorted(docs.iterdir()):
            if p.is_file() and p.name.lower() in {"project_handoff.md", "start_here.md", "product_vision.md"}:
                snapshot["key_docs"].append(str(p.relative_to(root)))
    return snapshot


def _table_cell(value: Any) -> str:
    return str(value if value not in {None, ""} else "—").replace("|", "\\|")


def render_markdown(state: Dict[str, Any]) -> str:
    p = state.get("project", {})
    lines = [
        "# PROJECT_MEMORY — AI handoff report",
        "",
        "## 0. Карточка проекта",
        f"- Project ID: `{p.get('project_id', 'unknown')}`",
        f"- Имя: {p.get('name', 'unknown')}",
        f"- Описание: {p.get('description') or 'не зафиксировано'}",
        f"- Цель: {p.get('goal', 'unknown')}",
        f"- Каноническая версия: {p.get('canonical_version') or 'unknown'}",
        "",
        "## 0.1 Быстрый handoff для новой AI-модели",
        f"- Project ID: `{p.get('project_id', 'unknown')}`",
        f"- Каноническая версия: {p.get('canonical_version') or 'unknown'}",
        f"- Текущий чат: {state.get('handoff', {}).get('current_chat_id') or 'не установлен'}",
        f"- Следующий проверяемый шаг: {state.get('handoff', {}).get('next_step') or 'не установлен'}",
        "- Правило продолжения: сначала прочитать этот отчёт и PROJECT_MEMORY.json; не повышать reported/planned до verified без новой проверки.",
        "",
        "## 1. Где находится проект",
        "| Среда | Расположение | Branch | SHA | Статус | Проверено |",
        "|---|---|---|---|---|---|",
    ]
    # Keep mandatory requirements in the short handoff, not only in JSON.
    constraint_lines = ["## CRITICAL_CONSTRAINTS — обязательные ограничения"]
    constraint_lines.extend(f"- {item}" for item in p.get("constraints", []))
    if not p.get("constraints"):
        constraint_lines.append("- Не зарегистрированы; это не подтверждение отсутствия требований.")
    constraint_lines.append("")
    section = lines.index("## 1. Где находится проект")
    lines[section:section] = constraint_lines
    if state.get("locations"):
        for loc in state["locations"]:
            marker = "observed_now" if loc.get("observed_now") else loc.get("observation_status", "mentioned")
            lines.append("| " + " | ".join([
                _table_cell(loc.get("kind")), _table_cell(loc.get("uri")), _table_cell(loc.get("branch")),
                _table_cell(loc.get("sha")), _table_cell(marker), _table_cell(loc.get("checked_at")),
            ]) + " |")
    else:
        lines.append("| — | Нет подтверждённых расположений | — | — | — | — |")

    lines += ["", "## 2. Цепочка чатов", "| Дата | Чат | Класс | Родитель | Основание |", "|---|---|---|---|---|"]
    chats = state.get("chats", [])
    current_chat_id = state.get("handoff", {}).get("current_chat_id")
    ordered = chats
    if current_chat_id:
        try:
            ordered = build_chat_chain(state, current_chat_id)
        except (ValueError, KeyError):
            ordered = sorted(chats, key=lambda x: (evidence_date_key(x.get("started_at")), x.get("chat_id") or ""))
    else:
        ordered = sorted(chats, key=lambda x: (evidence_date_key(x.get("started_at")), x.get("chat_id") or ""))
    if ordered:
        for chat in ordered:
            lines.append("| " + " | ".join([
                _table_cell(chat.get("started_at")), _table_cell(chat.get("title") or chat.get("chat_id")),
                _table_cell(chat.get("classification")), _table_cell(chat.get("parent_chat_id")),
                _table_cell(chat.get("evidence_strength")),
            ]) + " |")
    else:
        lines.append("| — | Чаты ещё не классифицированы | — | — | — |")

    lines += ["", "## 3. Планы → фактические изменения", "| План | Статус плана | Связанные версии | Фактически внесено |", "|---|---|---|---|"]
    versions = state.get("versions", [])
    if state.get("plans"):
        for plan in state["plans"]:
            related = [v for v in versions if plan.get("plan_id") in (v.get("plan_ids") or [])]
            version_names = ", ".join(v.get("name") or v.get("version_id") for v in related) or "—"
            changes = "; ".join(change for v in related for change in (v.get("changes") or [])) or "—"
            lines.append(f"| {_table_cell(plan.get('title') or plan.get('plan_id'))} | {_table_cell(plan.get('status'))} | {_table_cell(version_names)} | {_table_cell(changes)} |")
    else:
        lines.append("| — | Планы ещё не зафиксированы | — | — |")

    lines += ["", "## 4. Версии и фактические изменения"]
    if versions:
        for version in sorted(versions, key=lambda x: (evidence_date_key(x.get("occurred_at")), x.get("version_id") or "")):
            lines.append(f"### {version.get('name') or version.get('version_id')} · {version.get('occurred_at') or 'unknown date'} · {version.get('evidence_status', 'unknown')}")
            for change in version.get("changes") or []:
                lines.append(f"- {change}")
    else:
        lines.append("- Версии ещё не зафиксированы.")

    lines += ["", "## 5. Скриншоты и визуальные подтверждения"]
    visuals = sorted(state.get("visuals", []), key=lambda x: (evidence_date_key(x.get("captured_at")), x.get("visual_id") or ""), reverse=True)
    if visuals:
        for visual in visuals:
            parts = [f"`{visual.get('visual_id')}`", visual.get("label") or visual.get("kind", "visual")]
            if visual.get("version_id"):
                parts.append(f"version={visual['version_id']}")
            parts.append(f"status={'observed_now' if visual.get('observed_now') else visual.get('observation_status', 'reported')}")
            lines.append(f"- {' · '.join(parts)} — `{visual.get('uri', 'unknown')}`" + (f" · {visual.get('captured_at')}" if visual.get("captured_at") else ""))
    else:
        lines.append("- Скриншоты не найдены или их источник пока недоступен.")

    lines += ["", "## 6. Хронология"]
    if state.get("events"):
        for ev in sorted(state["events"], key=lambda x: (evidence_date_key(x.get("occurred_at")), x.get("event_id") or "")):
            lines.append(f"- {ev.get('occurred_at') if ev.get('occurred_at') is not None else 'unknown date'} · **{ev.get('evidence_status', 'unknown')}** · {ev.get('summary', '')}")
    else:
        lines.append("- События ещё не зафиксированы.")

    lines += ["", "## 7. Варианты и ответвления"]
    if state.get("development_lines"):
        for line in state["development_lines"]:
            lines.append(f"- `{line.get('line_id')}` — {line.get('name', '')} · {line.get('status', 'unknown')}")
            for rel in line.get("relations", []):
                lines.append(f"  - {rel.get('type')} → `{rel.get('target')}`")
    else:
        lines.append("- Линии развития ещё не зафиксированы.")

    lines += ["", "## 8. Нерешённые противоречия"]
    if state.get("conflicts"):
        lines.extend(f"- {x}" if isinstance(x, str) else f"- {x.get('summary', _canonical_json(x))}" for x in state["conflicts"])
    else:
        lines.append("- Нет зафиксированных противоречий.")

    lines += ["", "## 9. Очередь поиска"]
    if state.get("search_queue"):
        lines.extend(f"- {x}" if isinstance(x, str) else f"- {x.get('query', _canonical_json(x))}" for x in state["search_queue"])
    else:
        lines.append("- Очередь пуста.")

    lines += ["", "## 10. Источники"]
    if state.get("sources"):
        for src in state["sources"]:
            lines.append(f"- `{src.get('source_id')}` — {src.get('name') or src.get('locator') or 'source'}")
    else:
        lines.append("- Источники ещё не добавлены.")

    lines += [
        "", "## 11. Передача",
        f"- Текущий чат: {state.get('handoff', {}).get('current_chat_id') or 'не установлен'}",
        f"- Следующий шаг: {state.get('handoff', {}).get('next_step') or 'не установлен'}",
        f"- Обновлено: {state.get('handoff', {}).get('updated_at') or 'unknown'}", "",
    ]
    return "\n".join(lines)


def _cmd_scan(args: argparse.Namespace) -> int:
    print(json.dumps(scan_local_project(args.root), ensure_ascii=False, indent=2))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    state = load_state(args.state)
    text = render_markdown(state)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    state = load_state(args.state)
    p = state.get("project", {})
    print(json.dumps({
        "project_id": p.get("project_id"),
        "name": p.get("name"),
        "events": len(state.get("events", [])),
        "locations": len(state.get("locations", [])),
        "chats": len(state.get("chats", [])),
        "plans": len(state.get("plans", [])),
        "versions": len(state.get("versions", [])),
        "visuals": len(state.get("visuals", [])),
        "development_lines": len(state.get("development_lines", [])),
        "constraints": p.get("constraints", []),
    }, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_capture_visual(args: argparse.Namespace) -> int:
    result = capture_visual(args.url, args.output, {"width": args.width, "height": args.height}, args.timeout_ms)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Project History Agent v0.5 deterministic collector")
    sub = ap.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan-local")
    scan.add_argument("root")
    scan.set_defaults(func=_cmd_scan)
    render = sub.add_parser("render")
    render.add_argument("state")
    render.add_argument("--output")
    render.set_defaults(func=_cmd_render)
    summary = sub.add_parser("summary")
    summary.add_argument("state")
    summary.set_defaults(func=_cmd_summary)
    capture = sub.add_parser("capture-visual")
    capture.add_argument("url")
    capture.add_argument("output")
    capture.add_argument("--width", type=int, default=1440)
    capture.add_argument("--height", type=int, default=900)
    capture.add_argument("--timeout-ms", type=int, default=30000)
    capture.set_defaults(func=_cmd_capture_visual)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
