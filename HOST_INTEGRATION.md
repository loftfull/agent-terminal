# Host integration notes — v0.6

## Universal lifecycle

1. `session_start` — verify/replay journal, discover predecessor sessions via HistoryAdapter, run Chat Lineage Check, provide quick handoff.
2. `record_mutation` — redact first, append to hash-chain journal, then checkpoint.
3. `checkpoint` — verify journal → replay → atomic JSON + Markdown projection.
4. `session_stop` — record next step/result and checkpoint.

## HistoryAdapter boundary

Core accepts only:

```text
search(scope, query, limit) -> normalized sessions
inspect(session_id) -> normalized session | null
```

Search ranking finds candidates; it never proves continuation. The evidence-gated lineage resolver remains authoritative.

## v0.6 provider adapters

- Claude Code: read local/project JSONL session files through `ClaudeCodeHistoryAdapter`.
- Codex: read rollout/session JSONL metadata and response items through `CodexHistoryAdapter`.
- ChatGPT: only an explicitly supplied `conversations.json` export through `ChatGPTExportHistoryAdapter`; no claim of hidden account access.

## Repository agents

`AGENTS.md` and `CLAUDE.md` point agents to `PROJECT_HISTORY_AGENT.md`, root journal and handoff.

## Safety

Provider adapters are read-only. Secrets are redacted before project-journal persistence. Topic similarity alone is never a lineage proof.
