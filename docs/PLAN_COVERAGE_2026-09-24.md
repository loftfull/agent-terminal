# Coverage of all repository plan groups — 2026-09-24

Audit baseline: `f04ad095988cfb9389b54cae47cf67884414a125`. This is a source/code/test inventory and expert interface review, not an external A6 acceptance, user study, fresh account-history collection, or upstream product benchmark. No private message text is reproduced. The initial inventory did not change canonical history; the later reconciliation below adds sourced patches without rewriting earlier journal records.

Scope: all 12 `PROJECT_MEMORY.json` plan records; `PROJECT_HISTORY_AGENT.md` gates; `TASKS.md`; v0.6 design/implementation plan; `ROADMAP_V08.md`; terminal/control plans; both historical analogue audits; memory-service, recommendations, GitHub-solutions, OpenViking, repair, atomic-import and message-library documents; integration instructions and trial reports. Historical reports are evidence of their own runs, not proof of current end-to-end acceptance. No overall completion percentage is meaningful: groups have different scope and unavailable source history prevents an exhaustive request denominator.

Status vocabulary: **implemented** means a bounded component exists; **tested component** additionally has named executable tests / recorded trials; **partial** means some promised acceptance is absent; **not implemented** means no corresponding complete mechanism was found; **deferred** means explicitly optional/later work. A test filename below is evidence of test coverage, not a claim that this reviewer reran it. Fresh execution results belong in the accompanying audit receipt.

## Canonical plans and historical foundations

| Plan / requirement | Code and verification evidence | Assessed status and remaining work |
|---|---|---|
| P-V03: deterministic ledger, evidence classes, dedupe, structural auditor; A1–A5 | `project_history_agent.py`, `project_history_auditor.py`; `tests/test_repository_smoke.py`, import/MCP tests; historical acceptance records | Implemented/tested components. Fixture and replay correctness do not establish factual completeness of all historical claims. A6 remains separate. |
| P-V04: lineage/origin chain, passport, locations, plan→version ledger, visual registry; B1–B4 | `project_history_agent.py`, auditor, schemas, `PROJECT_MEMORY.md`; repository smoke/ranking/native-adapter tests | Implemented data model and projection. Earliest available parent only; undiscovered chats remain gaps. Visual registry does not prove a screenshot's build. Current plan/version projections contain stale descriptions listed below. |
| P-V05: hash chain, redaction, locks, atomic projections, migration, adapter boundary, hooks, doctor; C-gates | `project_history_journal.py`, `project_history_hooks.py`, `history_adapters.py`, `project_history_doctor.py`; segmented-journal, audit-repair, repository-smoke tests | Tested components; not a universal durability guarantee. Low-level bootstrap still sequential; historical tail-loss cause not established. OS lock repair does not prove the cause of earlier incidents. |
| P-V06 tasks 1–3: Claude/Codex native adapters and explicit ChatGPT export | `history_adapters.py`; `tests/test_host_native_adapters.py`, `test_chatgpt_message_evidence.py` | Implemented/tested bounded parsing. Host history read-only; explicit export is not a live ChatGPT connector. Unknown provider formats/complete account coverage unproven. |
| P-V06 task 4: current-chat bundle and repository transfer | `chat/current/`, `TRANSFER_MANIFEST.md`, recorded Git locations; repository-smoke tests | Implemented historical bundle/provenance. Partial chat content; old branch checkpoints are not current remote HEAD. No new remote verification in this review. |
| P-V06 task 5: regressions, compile, doctor, credential scan, exact remote branch/tree | tests and historical trial records, CI workflow | Verification process exists; acceptance is revision-specific. Historical secret scan/CI must not become a perpetual PASS. External A6 remains open. |
| P-V07: bounded discovery/doctor/CLI; P-V07-RANK: stable identity ranking | `host_history_discovery.py`, `host_history_cli.py`, `candidate_ranking.py`; discovery, CLI, doctor-discovery and ranking tests | Implemented/tested components. Candidate ranking never authorizes lineage. Discovery only covers accessible selected local stores. |
| v0.7 native lifecycle and immutable segments (historical audit/integration instructions) | `runtime_journal.py`, `native_hook_adapters.py`, `native_hook_config.py`, `native_hook_runner.py`, `host_lifecycle_bridge.py`; `test_native_lifecycle_stack.py`, `test_segmented_journal.py` | Implemented/tested normalization, templates, fail-open runner and checkpoint mechanics. Installation in a real user host and actual compaction lifecycle are not established by templates. |
| P-MCP: cross-process read-only memory | `project_history_mcp.py`, `requirements-mcp.txt`; `test_mcp_bridge.py`; MCP/real-chat trial reports | Tested stdio component and recorded real-sample handoff. Authenticated remote ChatGPT app, permanent service and continuous capture not implemented. |
| P-IMPORT: complete message import, revision preservation, dedupe, source dates/metadata | `evidence_import.py`, `terminal_chat_check.py`; evidence-import, evidence-dates, ChatGPT-message-evidence, terminal-chat-check tests | Tested selected-source component. Attachments remain references without supplied bytes; DOM samples do not prove complete conversations. Full current-chat/INSTA reconstruction remains partial. |
| P-IMPORT: decisions, supersession, failures/dead ends | `history_review.py`; `test_history_review.py` | Tested explicit sourced classification and supersession. No autonomous semantic reading of all chats, automatic root-cause attribution or full pre-action guard. |
| P-IMPORT: local observation and daily summaries | `history_watch.py`; `test_history_watch.py` | Tested selected-Git process and known-day catchup. User-installed persistent scheduler, all devices and transient between-poll changes are uncovered. |
| P-VAULT: focus, independent witness, rollback detection/recovery | `terminal_focus.py`, `terminal_vault.py`; focus/vault tests; `VAULT_REAL_CHAT_TRIAL_2026-09-24.md` | Tested bounded presentation and eventsourcing SQLite witness. Same-device witness is not independent off-device backup. Historical natural rollback cause unresolved; restic target/restore pilot absent. |

## Terminal, control dashboard and later increments

| Plan / requirement | Code and verification evidence | Assessed status and remaining work |
|---|---|---|
| P-TERMINAL T1: immutable contract/report/status, limits and evidence gating | `terminal_control.py`, `terminal_brief.py`; control/brief tests | Tested components. Seven structural ratings do not establish semantic quality; reported completion is not acceptance. |
| T2: Russian read-only dashboard, search, tabs, history/locations/visuals, snapshot | `terminal_dashboard.py`, `web/terminal.html`; dashboard tests and authenticated-preview trial | Implemented/tested HTTP and recorded HTML preview. Local server live polling/browser acceptance remains separately open. |
| T3: unit/HTTP/security, independent audit, browser/mobile, Windows/Linux | dashboard tests, independent trial/repair reports, CI | Partial composite gate. Historical checks at different SHAs cannot be combined into a universal PASS. Actual preview screenshot/tab checks supersede blanket browser-unavailable language only for that preview; full A6/user Windows/mobile coverage not established here. |
| T4: supervisor + real Claude/Codex, cancellation/recovery, time/attempt/cost limits | `terminal_runner.py`; runner tests; recommendations document | Tested explicit-command runner, bounded output/time/continuations, receipts and process cleanup. Real provider messaging/ACP pilot and spend-budget enforcement not implemented; crash recovery records interrupted, not guaranteed surviving-process recovery. |
| T5: reference/current/diff, scene/viewport/provenance, reviewer gate | `terminal_visual.py`, `terminal_versions.py`; visual/version tests | Tested selected-image pixel comparison and metadata. Real preview capture recorded, but build-linked same-scene reference/current acceptance of application versions is still partial. Pixel PASS is not design acceptance. |
| T6: selected Windows projects, one-command setup, autostart/uninstall | `terminal_projects.py`; project tests; launch-plan documentation | Tested registry/launch-plan generator. Installation, auto-start removal, real permissions/conflicts on user's Windows machine not accepted. |
| Recommendation details: purpose/constraints, questions, model/effort attribution, fallback, delegation | brief/control/runner/focus modules; corresponding tests; `RECOMMENDATIONS_IMPLEMENTATION.md` | Structural protocol implemented. Real host stop reasons/model metadata and automatic model continuation absent; historical independent work is not a installed swarm. |
| P-CONTROL-VERSIONS: criterion denominators, components registry, transport animation | `terminal_metrics.py`, dashboard, `web/vendor/`; dashboard/version tests; control trial | Implemented components. NProgress is polling activity, not overall project progress. Plugin availability is not installation/use. |
| P-CONTROL-VERSIONS: checkpoint, restore worktree, screenshot bytes | `terminal_versions.py`; `test_terminal_versions.py`; `CONTROL_DASHBOARD_PLAN.md` | Tested Git pinning/guards/new-worktree restore; reported screenshot provenance. Not environment/database/LFS/off-device restoration, nor an independently proven build capture. |
| Protected browser login and real selected-chat observation | `AUTHENTICATED_CHAT_TRIAL.md`, `terminal_metrics.py`, chat-check tests | Recorded successful historical 28+15-message samples and preview. No fresh login asserted here; no complete archive or continuous subscription. |
| B1–B5 audit repairs: OS locks, preflight, project isolation, cookies, full handoff | `project_history_journal.py`, hooks/native runner; `test_audit_repairs.py`; repair report | Implemented/tested repairs to concrete reproductions. Secret redaction not universal; mixed old/new locking clients unsupported. Full handoff is not token-budgeted. |
| Atomic import/strict runtime structural validation | `runtime_journal.py`, `evidence_import.py`; `test_atomic_batch.py`; `ATOMIC_IMPORT_2026-09-24.md` | Tested source/event batch, numeric segment order, lost-acknowledgement retry. Crash-safe bootstrap and remaining multi-step writer workflows remain open; large-segment cost and power-loss/network-FS durability unmeasured. |
| OpenViking idea adoption: L0/L1/L2 and quick attach | `terminal_context.py`, `fix.py`, MCP context tool; `test_terminal_context.py`, MCP tests; OpenViking report | Tested structural layered retrieval, pagination and selected import. No upstream OpenViking runtime/code integration, semantic compiler or byte/token budget. |
| User messages, copy, favorites, portable JSON | `web/terminal.html`, `web/message_library.js`; `tests/test_message_library.cjs`, dashboard tests; `MESSAGE_LIBRARY.md` | Implemented/tested bounded local-origin storage and validation; recorded preview/copy fallback. UI file-dialog import/export end-to-end untested; no cloud sync; no send-to-model action. |

## Every v0.8+ roadmap group (P-V08-REMAINING)

The 17 September analogue audit's proposed transfers map to these rows; research or an architectural similarity is not implementation.

| Roadmap group | Existing overlap | Remaining/status |
|---|---|---|
| P0 A6, immutable report, acceptance manifest | Auditor/doctor, component review reports and receipts | **Not completed.** Independent external-model raw-source A6; immutable cited accepted report; release acceptance manifest tying exact code SHA, journal tail, schemas and result. Component receipts are not that gate. |
| P1 typed attempt/failure/fix/decision/constraint + pre-action API | Events, constraints, explicit `history_review.py` | **Partial primitives; pre-action mechanism not implemented.** Required known_failed/superseded/unverified/no_evidence query contract and source-backed warnings absent. |
| P1 evidence promotion lifecycle | Evidence-status fields, append-only corrections, supersedes | **Partial primitives.** Enforced candidate→reviewed→verified/rejected→superseded/revoked workflow not implemented. |
| P1 token-budgeted tiny/normal/deep compiler | Full handoff; later structural L0/L1/L2 with tip receipt | **Partial.** Semantic prioritization, explicit token budget and cited compilation policy not implemented; count pagination is not a token bound. |
| P1 repository intelligence/read-first/safe-to-skip | Git location/branch observation and declared read-first instructions | **Not implemented as specified.** Automated fingerprint/framework/entry-point/risk-ranked conditional read-first product absent. |
| P2 cryptographic archive sealing | Hash-chained segmented journal, witness | **Partial base; optional seal/signature absent.** Segment length/digest/previous-tail manifest, seal event and optional Ed25519 not implemented as roadmap package. |
| P2 deterministic portable interchange | JSON/Markdown projection, MCP, source registry, JSON dashboard export | **Partial.** Single deterministic bundle integrating read-first plan, cited decisions/failures, audit references and visual index is not accepted. OKF adapter optional/absent. |
| P2 derived semantic/hybrid index | Literal evidence search | **Not implemented/deferred.** No semantic/hybrid rebuildable retrieval index; OpenViking research does not install one. |
| P2 visual evidence v2 | Viewport/scene/time/source metadata, pixel diff, screenshot digest/registry | **Partial.** Perceptual hashing absent; exact build proof and end-to-end comparison remain open. |
| P3 multi-writer/remote sync only if demanded | Local cooperative writer lock; atomic batch | **Deferred.** Remote synchronization/shared leases not implemented; local writer serialization is not remote sync. |
| P3 history UI | Tasks/plans/versions/locations/visual lists, chronology, metrics | **Partial.** Origin/continuation and fork graph, failure browser, plan-vs-actual/location timelines and dedicated contradiction/audit-receipt surfaces are not all present. |
| Pre-v1.0 frozen benchmark program | Fixture tests for identity, corruption, secrets, screenshots, hosts/restart cover subsets | **Not completed.** Frozen common corpus covering all listed cases, scored false/missed continuation and promotion errors, recovery, token cost, repeated-failure prevention and orientation time absent. Unit test count is not this benchmark. |

## Status reconciliation required

1. `TASKS.md` keeps historical browser-blocked, logged-out and screenshot-missing checkboxes, followed by corrective observations. Retain the old evidence, but add an explicit **superseded for HTML preview / selected sample only** pointer beside each old item; local-server polling and complete-chat capture remain open.
2. `PROJECT_MEMORY.md` plan/version descriptions still say “чат не подключён, снимок не получен” and P-TERMINAL says no real browser acceptance despite the later authenticated preview observation. Update those current projections through new journal patches; do not rewrite historical version evidence or imply continuous capture.
3. `CURRENT_CHAT_AUDIT_2026-09-24.md` says tiny/normal/deep compiler absent and Playwright browser blocked. Clarify that later structural L0/L1/L2 and preview checks exist; token-budgeted compiler and specific blocked local-server check remain incomplete.
4. `AUDIT_REPAIRS_2026-09-24.md` B2 describes missing structural batch validation as next work. Later atomic-import report closes that runtime/import scope only; low-level bootstrap and multi-step workflows remain open.
5. `integrations/README.md` calls native handoff compact; B5 now preserves full Markdown without the former truncation. Change current wording to full handoff; no token-budget promise.
6. v0.3–v0.7 “implemented” denotes component scope, not fully accepted product. `PROJECT_HISTORY_AGENT.md` v0.5 header is an older instruction edition; canonical candidate version and new modules must not be inferred from that heading alone.
7. Historical test totals (110, 190, 209, 213) and CI SHAs are dated receipts. Preserve them but present current-revision verification separately. Do not merge successes across revisions into one acceptance claim.
8. Message-library, layered-context, native lifecycle and atomic-writer work are not separate current `plans[]` entries. Existing twelve plans underdescribe later scope; add sourced subplan links or criteria before claiming the UI plan registry covers all development.

## First-time-user perspective (expert inspection, not a study)

The first screen already has a clear project name, Russian labels, focus mode, read-only status and copy/download actions. Messages/favorites offer a recognizable everyday workflow. Text rendering, keyboard tab navigation and clipboard fallback are useful. However, the current ten-tab navigation and default `monitorPanel → focusPanel → overview → runCards` sequence expose implementation concepts before explaining what the person can accomplish. Source/event/session IDs, witness record counts, raw English warning/status values and duplicated next-step blocks require technical knowledge. The primary “Скопировать передачу” action serializes the entire state as JSON, which is a poor match for an unexplained human-facing label. An empty installation says source unavailable without a concrete first step. These are reasoned usability risks, not measured user failures.

Recommended concrete changes, **not implemented by this audit**:

- Default to three destinations: “Сейчас”, “История”, “Сообщения”; put plans, versions, locations, components and raw receipts under “Подробнее”. Preserve all data and direct access.
- Lead with one sentence: “FIX хранит решения и сообщения проекта, чтобы продолжить работу в новом чате.” Follow with one next action and the few decisions requiring the user; collapse duplicate status panels.
- Show three independent plain-language statuses: “Сохранено до [time]”, “Получена часть переписки”, “Автосбор не настроен”. Keep critical stale/corruption/blocker notices visible. Do not collapse integrity, source coverage and completion into one green badge.
- Replace default IDs and witness counts with meaningful source names/dates; offer “Почему такой статус?” revealing evidence IDs, SHA, exact check and known gaps. Render operational English errors as short Russian messages with expandable technical detail.
- Rename current action “Скачать полные данные”; provide a separate “Подготовить контекст для нового чата” preview with goal, latest state, constraints, blockers and source links. Any bounded summary must link the full record and disclose omitted detail.
- Empty-state guidance should explain selecting a project and importing an available conversation file, plus what success looks like. Do not offer a fake “Connect ChatGPT” button or imply the read-only dashboard can install hooks.
- Keep favorites' local-device/address boundary beside the favorite/export action. Keep reported-vs-verified distinction beside task completion. Explain screenshot absence where a version is opened, not through repeated global technical warnings.
- Validate with actual first-time participants: find the next action, distinguish partial archive from live capture, copy a message, save/recover a favorite, explain whether a task is accepted. Record task success, time and misunderstandings before claiming simpler UX. This audit recruited no participants.

## Prioritized unfinished acceptance

First reconcile current plan/version facts and available-source coverage; complete causal durability investigation and crash-safe remaining writer paths; obtain raw-source A6. Then close real host/Windows/local-server/build-linked visual trials as separately scoped gates. Add roadmap governance/context/retrieval extensions only when their observable acceptance and need are explicit. Authenticated sample reads, more UI tabs and higher test counts cannot substitute for those gaps.

## Reconciliation follow-up and current validation scope

Current plan/version projections were reconciled through a validated append-only
batch and checkpoint, preserving historical records. Added explicit atomic-import,
layered-context and message-library subplans and linked factual development versions.
The current Russian purpose/next-step wording preserves the existing constraints.

The coordinating reviewer reports a fresh full 213-test unittest PASS after UI
edits began, plus message-library JS PASS. This is not a claim that the final
subsequent documentation/journal state was covered by that earlier full run. The UI
editor directly reran all four dashboard tests and JS checks after its changes;
JavaScript syntax passed. Doctor's reported WARN concerns unavailable local host
adapters/hooks/browser capture; integrity, replay, snapshot and structural checks
passed. No live host installation or new UI browser acceptance is inferred.

The coordinating reviewer observed additional selected authenticated INSTA chat
content. Public documentation intentionally omits private identifiers, message text
and sample counts. Virtualized rendered samples are partial evidence, not original
complete exports. Automatic new-chat transition after a message limit remains
unproven. Source coverage and the overall audit therefore remain partial; A6 open.

A bounded subset of the UX recommendations is now implemented in web/terminal.html:
plain-language purpose/start guidance, clearer data actions, next-step emphasis and
native disclosure for technical metadata, constraints and run logs. Open state and
summary focus survive polling; limitations/blockers stay visible. Full tab
reorganization, human-readable context compiler and actual first-time-user study
remain proposals. Fresh real-browser testing of these UI changes is pending.


## Актуализация после bootstrap и проверки терминалом

См. [STATE_AUDIT_2026-09-24.md](STATE_AUDIT_2026-09-24.md). Bootstrap, полный экспорт и сохранение
отменённых решений исправлены в указанном там объёме. 219 Python tests и JS PASS.
Doctor внутри runner дал snapshot mismatch; вне параллельной записи — WARN
с PASS integrity/replay/snapshot/structure. Это новый открытый дефект чтения.
Все 16 текущих планов сопоставлены; полная приёмка и автосбор остаются открытыми.
