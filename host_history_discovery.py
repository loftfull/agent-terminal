from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from history_adapters import (
    ChatGPTExportHistoryAdapter,
    ClaudeCodeHistoryAdapter,
    CodexHistoryAdapter,
    CompositeHistoryAdapter,
)


class HostHistoryDiscovery:
    """Bounded, read-only discovery of host-native AI session stores.

    Discovery only yields candidate history sources. It never decides chat
    continuation or parentage; those remain evidence-gated in the lineage core.
    """

    def __init__(self, *, home: Path | str | None = None, env: Mapping[str, str] | None = None):
        self.home = Path(home).expanduser() if home is not None else Path.home()
        self.env = dict(os.environ if env is None else env)

    @staticmethod
    def _source(provider: str, roots: list[Path], *, explicit: bool, file_required: bool = False) -> dict:
        existing = [p for p in roots if (p.is_file() if file_required else p.exists())]
        status = "available" if existing else "missing"
        return {
            "provider": provider,
            "status": status,
            "explicit": explicit,
            "roots": [str(p) for p in roots],
            "existing_roots": [str(p) for p in existing],
            "access": "read_only",
        }

    def _claude_source(self) -> dict:
        override = self.env.get("CLAUDE_HISTORY_ROOT")
        if override:
            return self._source("claude-code", [Path(override).expanduser()], explicit=True)
        return self._source("claude-code", [self.home / ".claude" / "projects"], explicit=False)

    def _codex_source(self) -> dict:
        override = self.env.get("CODEX_HOME")
        base = Path(override).expanduser() if override else self.home / ".codex"
        candidates = [base / "sessions", base / "archived_sessions"]
        existing = [p for p in candidates if p.exists()]
        roots = existing if existing else [candidates[0]]
        return self._source("codex", roots, explicit=bool(override))

    def _chatgpt_source(self) -> dict:
        override = self.env.get("CHATGPT_CONVERSATIONS_JSON")
        if not override:
            return {
                "provider": "chatgpt-export",
                "status": "not_configured",
                "explicit": False,
                "roots": [],
                "existing_roots": [],
                "access": "explicit_export_only",
            }
        return self._source("chatgpt-export", [Path(override).expanduser()], explicit=True, file_required=True)

    def discover(self) -> dict:
        return {
            "authority": "candidate-discovery-only",
            "bounded": True,
            "home": str(self.home),
            "sources": [self._claude_source(), self._codex_source(), self._chatgpt_source()],
        }

    def build_adapter(self, discovery: dict | None = None):
        report = discovery or self.discover()
        adapters = []
        for source in report.get("sources", []):
            if source.get("status") != "available":
                continue
            provider = source.get("provider")
            for root in source.get("existing_roots") or source.get("roots") or []:
                if provider == "claude-code":
                    adapters.append(ClaudeCodeHistoryAdapter(root))
                elif provider == "codex":
                    adapters.append(CodexHistoryAdapter(root))
                elif provider == "chatgpt-export":
                    adapters.append(ChatGPTExportHistoryAdapter(root))
        if not adapters:
            return None
        if len(adapters) == 1:
            return adapters[0]
        return CompositeHistoryAdapter(adapters)
