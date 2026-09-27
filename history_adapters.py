from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Protocol

SUPPORTED_SCOPES = {"conversations", "files", "plans", "sessions", "memories", "all"}


class HistoryAdapter(Protocol):
    def search(self, scope: str, query: str, limit: int = 20) -> list[dict]: ...
    def inspect(self, session_id: str) -> dict | None: ...


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text(x) for x in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {_text(v)}" for k, v in value.items())
    return str(value)


def normalize_session(raw: dict) -> dict:
    item = dict(raw)
    sid = item.get("session_id") or item.get("id") or item.get("chat_id")
    if not sid:
        raise ValueError("history session requires session_id/id/chat_id")
    item["session_id"] = str(sid)
    item.setdefault("chat_id", item["session_id"])
    item.setdefault("title", item.get("name") or item["chat_id"])
    item.setdefault("repositories", [])
    item.setdefault("paths", [])
    item.setdefault("files", [])
    item.setdefault("text", item.get("content") or "")
    stable = []
    for value in [item.get("project_id"), item.get("chat_id"), *item["repositories"], *item["paths"]]:
        if value and value not in stable:
            stable.append(value)
    item["stable_ids"] = stable
    return item


def _haystack(item: dict, scope: str) -> str:
    if scope == "files":
        return _text(item.get("files"))
    if scope == "plans":
        return _text(item.get("plans")) + " " + _text(item.get("text"))
    if scope == "memories":
        return _text(item.get("memories")) + " " + _text(item.get("files"))
    if scope == "sessions":
        return _text([item.get("session_id"), item.get("title"), item.get("project_id"), item.get("started_at")])
    if scope == "conversations":
        return _text([item.get("title"), item.get("text"), item.get("project_id"), item.get("chat_id")])
    return _text(item)


class InMemoryHistoryAdapter:
    def __init__(self, sessions: Iterable[dict]):
        self.sessions = [normalize_session(x) for x in sessions]

    def search(self, scope: str, query: str, limit: int = 20) -> list[dict]:
        if scope not in SUPPORTED_SCOPES:
            raise ValueError(f"unsupported history scope: {scope}")
        q = (query or "").casefold().strip()
        scored = []
        for index, item in enumerate(self.sessions):
            text = _haystack(item, scope).casefold()
            if q and q not in text:
                continue
            score = 0
            if q:
                if q == str(item.get("title", "")).casefold():
                    score += 100
                if q in str(item.get("title", "")).casefold():
                    score += 20
                if q in str(item.get("project_id", "")).casefold():
                    score += 10
                score += text.count(q)
            scored.append((score, index, dict(item)))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [item for _, _, item in scored[: max(0, limit)]]

    def inspect(self, session_id: str) -> dict | None:
        sid = str(session_id)
        for item in self.sessions:
            if item.get("session_id") == sid:
                return dict(item)
        return None


class JsonlHistoryAdapter:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def _iter(self):
        with self.path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    yield normalize_session(json.loads(line))
                except (json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"invalid history JSONL line {line_no}: {exc}") from exc

    def search(self, scope: str, query: str, limit: int = 20) -> list[dict]:
        return InMemoryHistoryAdapter(self._iter()).search(scope, query, limit)

    def inspect(self, session_id: str) -> dict | None:
        sid = str(session_id)
        for item in self._iter():
            if item.get("session_id") == sid:
                return item
        return None


def _extract_text(value: Any) -> list[str]:
    out: list[str] = []
    if value is None:
        return out
    if isinstance(value, str):
        if value.strip():
            out.append(value)
        return out
    if isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_extract_text(item))
        return out
    if isinstance(value, dict):
        for key in ("text", "parts", "content"):
            if key in value:
                out.extend(_extract_text(value.get(key)))
        return out
    return out


def _extract_file_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"file_path", "filepath", "path"} and isinstance(item, str) and item.strip():
                if item not in found:
                    found.append(item)
            else:
                for nested in _extract_file_paths(item):
                    if nested not in found:
                        found.append(nested)
    elif isinstance(value, (list, tuple)):
        for item in value:
            for nested in _extract_file_paths(item):
                if nested not in found:
                    found.append(nested)
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            parsed = None
        if parsed is not None:
            found.extend(_extract_file_paths(parsed))
    return found


def _first_user_text(rows: list[dict]) -> str:
    for row in rows:
        message = row.get("message") if isinstance(row, dict) else None
        if isinstance(message, dict) and message.get("role") == "user":
            parts = _extract_text(message.get("content"))
            if parts:
                return parts[0][:120]
        payload = row.get("payload") if isinstance(row, dict) else None
        if isinstance(payload, dict) and payload.get("role") == "user":
            parts = _extract_text(payload.get("content"))
            if parts:
                return parts[0][:120]
    return ""


class _FilesystemJsonlAdapter:
    provider = "unknown"

    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser()

    def _files(self) -> list[Path]:
        if self.root.is_file():
            return [self.root]
        if not self.root.exists():
            return []
        return sorted(p for p in self.root.rglob("*.jsonl") if p.is_file())

    def _parse_file(self, path: Path) -> dict | None:
        raise NotImplementedError

    def _sessions(self) -> list[dict]:
        sessions: list[dict] = []
        for path in self._files():
            item = self._parse_file(path)
            if item is not None:
                sessions.append(normalize_session(item))
        return sessions

    def search(self, scope: str, query: str, limit: int = 20) -> list[dict]:
        return InMemoryHistoryAdapter(self._sessions()).search(scope, query, limit)

    def inspect(self, session_id: str) -> dict | None:
        sid = str(session_id)
        for item in self._sessions():
            if item.get("session_id") == sid:
                return item
        return None


class ClaudeCodeHistoryAdapter(_FilesystemJsonlAdapter):
    provider = "claude-code"

    def _parse_file(self, path: Path) -> dict | None:
        rows: list[dict] = []
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid Claude Code JSONL {path}:{line_no}: {exc}") from exc
                if isinstance(obj, dict):
                    rows.append(obj)
        if not rows:
            return None
        sid = next((r.get("sessionId") for r in rows if r.get("sessionId")), None) or path.stem
        paths: list[str] = []
        files: list[str] = []
        text: list[str] = []
        started_at = None
        for row in rows:
            cwd = row.get("cwd")
            if isinstance(cwd, str) and cwd and cwd not in paths:
                paths.append(cwd)
            if started_at is None and row.get("timestamp"):
                started_at = row.get("timestamp")
            message = row.get("message")
            if isinstance(message, dict):
                text.extend(_extract_text(message.get("content")))
                for fp in _extract_file_paths(message.get("content")):
                    if fp not in files:
                        files.append(fp)
            for fp in _extract_file_paths(row.get("toolUseResult")):
                if fp not in files:
                    files.append(fp)
        return {"session_id": str(sid), "chat_id": str(sid), "title": _first_user_text(rows) or path.stem, "provider": self.provider, "source_locator": str(path), "started_at": started_at, "text": "\n".join(text), "repositories": [], "paths": paths, "files": files}


class CodexHistoryAdapter(_FilesystemJsonlAdapter):
    provider = "codex"

    def _parse_file(self, path: Path) -> dict | None:
        rows: list[dict] = []
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid Codex JSONL {path}:{line_no}: {exc}") from exc
                if isinstance(obj, dict):
                    rows.append(obj)
        if not rows:
            return None
        meta = next((r.get("payload") for r in rows if r.get("type") == "session_meta" and isinstance(r.get("payload"), dict)), {})
        sid = meta.get("id") or meta.get("session_id") or path.stem
        cwd = meta.get("cwd")
        git = meta.get("git") if isinstance(meta.get("git"), dict) else {}
        repo = git.get("repository_url") or git.get("repo_url")
        text: list[str] = []
        files: list[str] = []
        started_at = next((r.get("timestamp") for r in rows if r.get("timestamp")), None)
        for row in rows:
            payload = row.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "message" or payload.get("role") in {"user", "assistant", "system"}:
                text.extend(_extract_text(payload.get("content")))
            if payload.get("type") in {"function_call", "tool_call"}:
                args = payload.get("arguments") or payload.get("input")
                for fp in _extract_file_paths(args):
                    if fp not in files:
                        files.append(fp)
        return {"session_id": str(sid), "chat_id": str(sid), "title": _first_user_text(rows) or path.stem, "provider": self.provider, "source_locator": str(path), "started_at": started_at, "text": "\n".join(text), "repositories": [repo] if isinstance(repo, str) and repo else [], "paths": [cwd] if isinstance(cwd, str) and cwd else [], "files": files, "git_branch": git.get("branch"), "git_sha": git.get("commit_hash") or git.get("sha")}


class ChatGPTExportHistoryAdapter:
    def __init__(self, conversations_json: Path | str):
        self.path = Path(conversations_json).expanduser()

    def _sessions(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid ChatGPT export JSON {self.path}: {exc}") from exc
        if not isinstance(data, list):
            raise ValueError("ChatGPT conversations export must be a JSON list")
        sessions: list[dict] = []
        for conv in data:
            if not isinstance(conv, dict):
                continue
            sid = conv.get("conversation_id") or conv.get("id")
            if not sid:
                continue
            mapping = conv.get("mapping") if isinstance(conv.get("mapping"), dict) else {}
            warnings: list[str] = []
            active: list[str] = []
            current = conv.get("current_node")
            valid_path = isinstance(current, str) and current in mapping
            if not valid_path:
                warnings.append("current_node_missing_or_unknown: active path is unknown")
            else:
                seen: set[str] = set()
                cursor = current
                while cursor is not None:
                    if not isinstance(cursor, str) or cursor not in mapping:
                        warnings.append("dangling_active_parent: active path is unknown")
                        valid_path = False
                        break
                    if cursor in seen:
                        warnings.append("cyclic_active_path: active path is unknown")
                        valid_path = False
                        break
                    seen.add(cursor)
                    node = mapping[cursor]
                    if not isinstance(node, dict) or "parent" not in node:
                        warnings.append("malformed_active_node: active path is unknown")
                        valid_path = False
                        break
                    active.append(cursor)
                    cursor = node.get("parent")
                active.reverse()
            if not valid_path:
                active = []
            active_set = set(active)
            messages: list[dict] = []
            files: list[str] = []
            for node_id, node in mapping.items():
                if not isinstance(node, dict):
                    warnings.append(f"malformed_node:{node_id}")
                    continue
                parent = node.get("parent")
                if parent is not None and (not isinstance(parent, str) or parent not in mapping):
                    warnings.append(f"dangling_parent:{node_id}")
                children = node.get("children")
                if not isinstance(children, list):
                    warnings.append(f"missing_or_malformed_children:{node_id}")
                elif any(not isinstance(child, str) or child not in mapping for child in children):
                    warnings.append(f"dangling_children:{node_id}")
                message = node.get("message")
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                author = message.get("author")
                normalized = {
                    "id": message.get("id"), "node_id": node_id,
                    "parent": parent, "children": children,
                    "role": author.get("role") if isinstance(author, dict) else message.get("role"),
                    "text": "\n".join(_extract_text(content)),
                    "create_time": message.get("create_time"),
                    "metadata": message.get("metadata") if isinstance(message.get("metadata"), dict) else {},
                    "content": content, "author": author,
                    "raw_message": dict(message),
                    "node_metadata": {key: value for key, value in node.items() if key != "message"},
                    "on_active_path": node_id in active_set if valid_path else None,
                }
                if message.get("metadata") is not None and not isinstance(message.get("metadata"), dict):
                    normalized["raw_metadata"] = message.get("metadata")
                    warnings.append(f"malformed_metadata:{node_id}")
                messages.append(normalized)
                for fp in _extract_file_paths(content):
                    if fp not in files:
                        files.append(fp)
            by_node = {message["node_id"]: message for message in messages}
            text_messages = [by_node[n] for n in active if n in by_node] if valid_path else messages
            if not valid_path:
                warnings.append("text_contains_unordered_alternatives: mapping order is not chronology")
            item = {"session_id": str(sid), "chat_id": str(sid), "title": conv.get("title") or str(sid), "provider": "chatgpt-export", "source_locator": str(self.path), "started_at": conv.get("create_time"), "text": "\n".join(message["text"] for message in text_messages), "repositories": [], "paths": [], "files": files,
                    "messages": messages, "current_node": current, "active_node_ids": active,
                    "raw_session": {key: value for key, value in conv.items() if key != "mapping"},
                    "node_index": {key: ({k: v for k, v in value.items() if k != "message"} if isinstance(value, dict) else value) for key, value in mapping.items()},
                    "coverage": {"source": "explicit_chatgpt_export_mapping", "attachments": "export references only; external bytes not fetched", "active_path_known": valid_path, "messages_scope": "all_exported_mapping_messages", "text_scope": "active_path" if valid_path else "all_alternatives_unordered", "warnings": warnings}}
            sessions.append(normalize_session(item))
        return sessions

    def search(self, scope: str, query: str, limit: int = 20) -> list[dict]:
        sessions = self._sessions()
        # Discovery searches every exported alternative; the returned text remains
        # scoped to the selected active path and is never silently expanded.
        searchable = []
        for item in sessions:
            candidate = dict(item)
            candidate["text"] = "\n".join(message["text"] for message in item["messages"])
            searchable.append(candidate)
        hits = InMemoryHistoryAdapter(searchable).search(scope, query, limit)
        by_id = {item["session_id"]: item for item in sessions}
        return [by_id[item["session_id"]] for item in hits]

    def inspect(self, session_id: str) -> dict | None:
        sid = str(session_id)
        for item in self._sessions():
            if item.get("session_id") == sid:
                return item
        return None


class CompositeHistoryAdapter:
    def __init__(self, adapters: Iterable[HistoryAdapter]):
        self.adapters = list(adapters)

    def search(self, scope: str, query: str, limit: int = 20) -> list[dict]:
        merged: list[dict] = []
        seen: set[str] = set()
        for adapter in self.adapters:
            for item in adapter.search(scope, query, limit=limit):
                key = str(item.get("session_id") or item.get("chat_id"))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
                if len(merged) >= limit:
                    return merged
        return merged

    def inspect(self, session_id: str) -> dict | None:
        for adapter in self.adapters:
            item = adapter.inspect(session_id)
            if item is not None:
                return item
        return None
