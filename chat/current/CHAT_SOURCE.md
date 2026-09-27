# Current Chat Source / Handoff Index

## Identity

- Project: Project History Agent
- Current chat ID in project memory: `chat-current-project-history-agent`
- Explicit origin chat: `агент`
- Relationship: `агент -> current chat` (`continuation`, explicit evidence)
- Canonical repository requested by user: `https://github.com/loftfull/FIX`

## Development carried out in this chat

### v0.3

- deterministic project ledger;
- separate structural auditor;
- canonical `PROJECT_MEMORY.json`;
- A1-A5 verification and NOTE2 real-evidence fixture.

### v0.4

- first-run Chat Lineage Resolver;
- Project Passport and AI Quick Handoff;
- locations / plan->fact / version / visual evidence ledgers;
- real current-chat test and real TERMINAL test;
- GitHub analogue audit.

### v0.5

- append-only `PROJECT_HISTORY.events.jsonl` source of truth;
- SHA-256 hash chain and tamper detection;
- atomic snapshot persistence + bounded locks;
- pre-persistence secret redaction;
- host-neutral `HistoryAdapter` protocol;
- lifecycle hooks and `doctor`;
- deterministic replay of current-chat and TERMINAL state.

### v0.6 in progress

- canonical repository moved to `loftfull/FIX`;
- Claude Code JSONL adapter;
- Codex rollout/session adapter;
- explicit ChatGPT `conversations.json` export adapter;
- public-safe current-chat source bundle and exact GitHub provenance.

## Files containing the current-chat state

- `PROJECT_HISTORY.events.jsonl` — append-only current-chat source of truth.
- `PROJECT_MEMORY.json` — rebuilt current-chat snapshot.
- `PROJECT_MEMORY.md` — human/AI-readable current-chat handoff.
- `USER_MESSAGES.md` — user instructions available in this chat.

## Older release evidence

The project memory and repository history preserve v0.3, v0.4 and v0.5 provenance. Heavy release archives remain external evidence; their SHA-256 manifests are retained in the project transfer package rather than rewritten as source files.

## Коррекция состояния — наблюдение 2026-09-24

Разделы выше — исторический индекс до v0.6, НЕ актуальный полный архив.
После него реализованы v0.7, MCP, импорт/review/watch и компоненты терминала/vault.
Текущая сверка: ../../docs/CURRENT_CHAT_AUDIT_2026-09-24.md и корневая PROJECT_MEMORY.md.
`USER_REQUEST_2026-09-24.md` добавляет один наблюдаемый запрос. Ни один из этих файлов
не является полным оригинальным экспортом текущего чата. Полнота неизвестна.
