# OpenViking: bounded adoption and quick chat entry

Research 2026-09-24, query: OpenViking github context database.
Repository https://github.com/volcengine/OpenViking
Reviewed commit c9a869cb145aac98f4be1586da32174d220c8800.
LICENSE blob27268c8e4ad8c300f7665fe6b20875c580d05f4b: AGPL-3.0.
MCP clients guide blobb5619949197887fefe36c76b60fcfafd2b214c5c.
README/concepts: L0 abstract, L1 overview, L2 details; scoped retrieval;
MCP memory access distinct from host hooks that capture sessions.

Decision before implementation: adapt these architectural ideas using existing
FIX journal/reader/importer, no upstream source code copied. No OpenViking runtime
installed. Full service needs model/provider configuration; replacing our journal
would not grant ChatGPT account-history access. Keep it an optional future derived
index, with canonical evidence IDs retained. No benchmark claims transferred.

Implemented scope: structural L0/L1/L2 on one checked journal, paginated source
loading, retrieval receipt bound to journal tip; one local command imports a selected
normalized/exported conversation, verifies it and returns L0. Summaries are structural,
not model-generated semantic summaries. No paid API needed for this implementation.

Quick command in FIX checkout:
`python fix.py attach --root PRIVATE_MEMORY --project-id PROJECT --input CHAT.json --session SESSION_ID`
Input: normalized sessions document or ChatGPT conversations.json. Explicit session
selection prevents importing all private conversations into the wrong project.
`python fix.py context --root PRIVATE_MEMORY --project-id PROJECT --level L1`
L2 adds `--offset 0 --limit 20`; subsequent next_offset pages retain all sources.
MCP clients can call read_context_layer(level, offset, limit).

Proposed in-chat wording (not a registered ChatGPT slash command):
«FIX, подключи этот чат к проекту PROJECT. Проверь доступные источники, прочитай
L0, сохрани доступные сообщения с источниками и составь историю. Не заявляй
полноту без исходного архива».
This wording only works when the host actually supplies tools/history; a prompt
cannot install a connector or obtain account privileges.

ChatGPT target architecture: authenticated MCP app exposes FIX memory; a separately
configured capture/import adapter supplies chat messages. Native Codex/Claude hooks
are appropriate where the host exposes session logs. For old ChatGPT conversations,
use explicit account export once, then incremental imports; original attachments
require separate bytes. Browser DOM stays a fallback, not the primary architecture.
OpenAI's official app setup controls actual plan/account availability, not upstream's
generic mcpServers JSON example. Current session custom-app installation and continuous
capture are not completed or claimed. No exposed public unauthenticated server.

Validation: two new tests and ten MCP tests PASS. Real previously captured private
samples28+15: attach/check/repeat0 and new MCP L0/L2 calls passed; all43message IDs
retrieved through pagination. This tests our adaptation, not OpenViking runtime.
L0 includes constraints, tasks, conflicts and unresolved queue; inspect evidence
before decisions. Pagination limits record count, not bytes/tokens. Compare
journal_tip across pages and restart if changed; do not combine different revisions.
No semantic quality, latency or token-cost improvement claimed from these tests.
