# PROJECT_MEMORY — AI handoff report

## 0. Карточка проекта
- Project ID: `project-history-agent`
- Имя: Project History Agent
- Описание: История проекта с источниками: решения, сообщения, планы, версии и передача контекста между чатами и моделями.
- Цель: Сохранять решения, сообщения и изменения проекта с проверяемыми источниками, чтобы продолжать работу в новом чате или другой модели без потери требований и с явными пробелами истории.
- Каноническая версия: v0.8.1-candidate.1 + browser observation correction; continuous ingestion and A6 open

## 0.1 Быстрый handoff для новой AI-модели
- Project ID: `project-history-agent`
- Каноническая версия: v0.8.1-candidate.1 + browser observation correction; continuous ingestion and A6 open
- Текущий чат: chat-current-project-history-agent
- Следующий проверяемый шаг: Проверить интерфейс в доступном браузере: мобильный layout, клавиатура, контраст; затем спроектировать авторизованное подключение приватных репозиториев. A6 и непрерывный сбор чатов остаются открытыми.
- Правило продолжения: сначала прочитать этот отчёт и PROJECT_MEMORY.json; не повышать reported/planned до verified без новой проверки.

## CRITICAL_CONSTRAINTS — обязательные ограничения
- Never infer chat continuation from topic similarity alone
- Keep requested/planned/reported/observed/verified distinct
- Redact secrets before persistence
- Do not call the system fully accepted before A6 independent external-model audit passes
- Before any new functionality search GitHub first; reuse suitable licensed code or dependencies; record exact provenance, scope, tests and reasons when none fits.
- Prioritize evidence-based project history and source coverage over optional UI, provider or orchestration expansion.
- Current chat archive is partial; never claim complete context preservation or all plans implemented without raw-source evidence.

## 1. Где находится проект
| Среда | Расположение | Branch | SHA | Статус | Проверено |
|---|---|---|---|---|---|
| github_code_checkpoint | https://github.com/loftfull/FIX | project-history-agent-v0.6 | f27e837e5941a9ecd6a36160f5efccc743e155f1 | historical_code_checkpoint | 2026-09-16 |
| chatgpt_library | /Project History Agent/v0.5 | — | — | observed | 2026-09-16 |
| github_branch | https://github.com/loftfull/FIX/tree/project-history-agent-v0.6 | project-history-agent-v0.6 | — | historical_observation | 2026-09-16 |
| github_branch | https://github.com/loftfull/FIX/tree/project-history-agent-v0.7 | project-history-agent-v0.7 | — | historical_observation | 2026-09-16 |
| github_code_checkpoint | https://github.com/loftfull/FIX/commit/bfbc90f6200150e171036a8367def055f49fd106 | project-history-agent-v0.7 | bfbc90f6200150e171036a8367def055f49fd106 | verified_code_checkpoint | 2026-09-16 |
| github_code_checkpoint | https://github.com/loftfull/FIX/commit/f2628d2a65294c063b0098ceb84b3d011b8208a4 | project-history-agent-v0.7 | f2628d2a65294c063b0098ceb84b3d011b8208a4 | verified_code_checkpoint | 2026-09-16 |
| local_checkout | /workspace/scratch/c911ac0d5396/repos/FIX | codex/history-mcp-foundation | f583fd84ea7505f399295b8c86ac17a868f92343 | historical_observation_before_audit_changes; resolve current checkout via git rev-parse HEAD | 2026-09-24 |
| github_working_branch | https://github.com/loftfull/FIX/tree/codex/history-mcp-foundation | codex/history-mcp-foundation | 0b86b8391b9c5c532bc4f09bfa905bfcc7f22c71 | historical_ci_code_checkpoint; branch exists; latest HEAD not asserted | 2026-09-24 |
| github_repository | https://github.com/loftfull/agent-terminal | English | fed0be04318d58100678fd21288db01437435fb8 | verified_import_checkpoint_before_context_changes | 2026-09-27 |

## 2. Цепочка чатов
| Дата | Чат | Класс | Родитель | Основание |
|---|---|---|---|---|
| 2026-09-15 | агент | new | — | explicit_origin |
| 2026-09-15 | Продолжение проекта из чата «агент» | continuation | chat-agent-origin | explicit |

## 3. Планы → фактические изменения
| План | Статус плана | Связанные версии | Фактически внесено |
|---|---|---|---|
| v0.3 deterministic ledger + structural auditor | implemented | v0.3 deterministic ledger + auditor | canonical PROJECT_MEMORY.json; deterministic dedupe; separate structural auditor; A1-A5 acceptance tests |
| v0.4 chat lineage + AI handoff + visual evidence | implemented | v0.4 chat lineage + handoff + visuals | first-run Chat Lineage Resolver; Project Passport and Quick Handoff; plan→fact/version ledger; visual evidence registry; current-chat and TERMINAL real tests |
| v0.5 durable journal + adapters + lifecycle + doctor | implemented | v0.5 durable project history | append-only SHA-256 journal; atomic persistence and lock; pre-persistence secret redaction; HistoryAdapter boundary; lifecycle hooks; doctor; deterministic replay |
| v0.6 canonical FIX transfer + host-native history adapters | implemented | v0.6 FIX canonical transfer + host-native adapters | canonical repository loftfull/FIX; current chat bundle in chat/current; Claude Code JSONL adapter; Codex rollout/session adapter; explicit ChatGPT conversations.json export adapter; v0.6 regression tests |
| v0.7 bounded direct host-history wiring | implemented | v0.7 direct host-history wiring | HostHistoryDiscovery with bounded Claude Code/Codex roots; ChatGPT explicit-export-only discovery; doctor auto-wires discovered adapter; discover-history and history-search CLI; provider discovery remains candidate-only, not lineage authority; stable-identity candidate ranking with explicit ref > repository > project+identity > path > project > artifact > topic; CLI optional current-context ranking without lineage classification |
| v0.7 stable-identity candidate ranking | implemented | v0.7 direct host-history wiring | HostHistoryDiscovery with bounded Claude Code/Codex roots; ChatGPT explicit-export-only discovery; doctor auto-wires discovered adapter; discover-history and history-search CLI; provider discovery remains candidate-only, not lineage authority; stable-identity candidate ranking with explicit ref > repository > project+identity > path > project > artifact > topic; CLI optional current-context ranking without lineage classification |
| MCP memory transport | component_implemented_host_acceptance_open | MCP memory transport (development checkpoint) | Official mcp2.2.0 stdio read-only transport, source-preserving handoff |
| Evidence import, decisions and local observation | partial | Evidence import, decisions and local observation (development checkpoint) | Revision-preserving selected chat import; Explicit sourced strategy review; no autonomous semantic completeness; Scoped Git watcher and known-day catchup; no installed daily service |
| Requested agent-terminal supporting workflow | partial | Requested agent-terminal supporting workflow (development checkpoint) | Task contracts, brief, bounded runner, selected-project registry; Offline pixel receipts and read-only dashboard; historical HTML preview observed, local-server/provider/Windows acceptance remains open |
| Focus and persistence witness | partial | Focus and persistence witness (development checkpoint) | Adapted presentation ideas, full-data preservation; eventsourcing9.5.5 witness and isolated recovery; original rollback cause unknown |
| v0.8 historical governance and acceptance roadmap | open | — | — |
| Truthful dashboard, code rollback and version screenshots | partial | v0.8.1-candidate.1 | Контрольные индикаторы, реестр компонентов и безопасный возврат кода; Позднее наблюдались выбранные authenticated чаты и фактический HTML preview screenshot; непрерывный сбор и полнота не подтверждены |
| Атомарный импорт и структурная проверка runtime | partial | Атомарный импорт и структурная проверка runtime — компонент | Runtime batch и импорт публикуют согласованную группу; числовой порядок и повтор active segment исправлены; Тесты компонента есть; power-loss/network FS и оставшиеся writer workflows не приняты |
| Слои контекста и подключение выбранного архива | partial | Слои контекста и подключение выбранного архива — компонент | Структурные слои памяти и fix.py attach/context с выбранным источником; Проверено сохранение источников; upstream OpenViking runtime не установлен |
| Сообщения пользователя и переносимое избранное | partial | Сообщения пользователя и переносимое избранное — компонент | Просмотр сообщений и local-origin избранное с JSON импортом/экспортом; JS проверки и исторический preview подтверждены; нет облачной синхронизации |
| Проверка всех планов и покрытия исходной истории | partial | — | — |
| Наглядные планы, аудиты и динамика истории | partial | — | — |

## 4. Версии и фактические изменения
### v0.8.1-candidate.1 · 2026-09-24T09:07:00.573490+00:00 · observed
- Контрольные индикаторы, реестр компонентов и безопасный возврат кода
- Позднее наблюдались выбранные authenticated чаты и фактический HTML preview screenshot; непрерывный сбор и полнота не подтверждены
### v0.3 deterministic ledger + auditor · 2026-09-15 · verified
- canonical PROJECT_MEMORY.json
- deterministic dedupe
- separate structural auditor
- A1-A5 acceptance tests
### v0.4 chat lineage + handoff + visuals · 2026-09-16 · verified
- first-run Chat Lineage Resolver
- Project Passport and Quick Handoff
- plan→fact/version ledger
- visual evidence registry
- current-chat and TERMINAL real tests
### v0.5 durable project history · 2026-09-16 · verified
- append-only SHA-256 journal
- atomic persistence and lock
- pre-persistence secret redaction
- HistoryAdapter boundary
- lifecycle hooks
- doctor
- deterministic replay
### v0.6 FIX canonical transfer + host-native adapters · 2026-09-16 · verified
- canonical repository loftfull/FIX
- current chat bundle in chat/current
- Claude Code JSONL adapter
- Codex rollout/session adapter
- explicit ChatGPT conversations.json export adapter
- v0.6 regression tests
### v0.7 direct host-history wiring · 2026-09-16 · verified
- HostHistoryDiscovery with bounded Claude Code/Codex roots
- ChatGPT explicit-export-only discovery
- doctor auto-wires discovered adapter
- discover-history and history-search CLI
- provider discovery remains candidate-only, not lineage authority
- stable-identity candidate ranking with explicit ref > repository > project+identity > path > project > artifact > topic
- CLI optional current-context ranking without lineage classification
### MCP memory transport (development checkpoint) · 2026-09-23 · observed
- Official mcp2.2.0 stdio read-only transport, source-preserving handoff
### Атомарный импорт и структурная проверка runtime — компонент · 2026-09-24 · observed
- Runtime batch и импорт публикуют согласованную группу; числовой порядок и повтор active segment исправлены
- Тесты компонента есть; power-loss/network FS и оставшиеся writer workflows не приняты
### Слои контекста и подключение выбранного архива — компонент · 2026-09-24 · observed
- Структурные слои памяти и fix.py attach/context с выбранным источником
- Проверено сохранение источников; upstream OpenViking runtime не установлен
### Evidence import, decisions and local observation (development checkpoint) · 2026-09-24 · observed
- Revision-preserving selected chat import
- Explicit sourced strategy review; no autonomous semantic completeness
- Scoped Git watcher and known-day catchup; no installed daily service
### Сообщения пользователя и переносимое избранное — компонент · 2026-09-24 · observed
- Просмотр сообщений и local-origin избранное с JSON импортом/экспортом
- JS проверки и исторический preview подтверждены; нет облачной синхронизации
### Requested agent-terminal supporting workflow (development checkpoint) · 2026-09-24 · observed
- Task contracts, brief, bounded runner, selected-project registry
- Offline pixel receipts and read-only dashboard; historical HTML preview observed, local-server/provider/Windows acceptance remains open
### Focus and persistence witness (development checkpoint) · 2026-09-24 · observed
- Adapted presentation ideas, full-data preservation
- eventsourcing9.5.5 witness and isolated recovery; original rollback cause unknown

## 5. Скриншоты и визуальные подтверждения
- `VIS-v0.8.1-candidate.1-d62b38fb3a48d1a7983c701132c2cd25b1f5afe0da5380936991a17d0e13c7e2` · Screenshot for v0.8.1-candidate.1 · version=v0.8.1-candidate.1 · status=file_observed_build_link_reported — `/workspace/scratch/c911ac0d5396/repos/FIX/version-images/d62b38fb3a48d1a7983c701132c2cd25b1f5afe0da5380936991a17d0e13c7e2.jpg`

## 6. Хронология
- 2026-09-24T06:55:26.704539+00:00 · **reported** · Визуальный контроль разработки — первый этап
- 2026-09-24T06:55:26.738625+00:00 · **reported** · Код и HTTP-проверки реализованы. Браузерное испытание заблокировано политикой среды; внешний вид не принят.
- 2026-09-24T08:37:09.540119+00:00 · **reported** · Аудит собственного проекта в текущем чате
- 2026-09-24T08:37:09.568416+00:00 · **reported** · Аудит и актуализация памяти выполнены; запускается проверка передачи.
- 2026-09-24T08:37:47.906886+00:00 · **observed** · Local run starting
- 2026-09-24T08:37:47.949022+00:00 · **observed** · Local run running
- 2026-09-24T08:37:51.684809+00:00 · **observed** · Own FIX task executed by terminal_runner:31 testsPASS and real MCP read preserves existing events, identities and7critical constraints. Independent scope audit agrees; full chat coverage/A6 not accepted.
- 2026-09-24T08:37:51.688448+00:00 · **observed** · Local run succeeded
- 2026-09-24T08:39:33.461408+00:00 · **reported** · Аудит выполнен: паспорт обновлён, доноры разделены по фактическому внедрению, GitHub-first закреплён; проверка MCP и31 тест прошли. Полная история чата и A6 остаются открытыми.
- 2026-09-24T09:00:52.858218+00:00 · **reported** · Контрольная панель, версии и проверка подключения чата
- 2026-09-24T09:00:52.893123+00:00 · **reported** · Компоненты реализуются и проверяются. Вход в ChatGPT браузере отсутствует.
- 2026-09-24T09:01:53.186769+00:00 · **observed** · Local run starting
- 2026-09-24T09:01:53.207561+00:00 · **observed** · Local run running
- 2026-09-24T09:01:57.761676+00:00 · **observed** · Local run succeeded
- 2026-09-24T09:06:43.552134+00:00 · **reported** · Панель и безопасные версии реализованы и испытаны локально. Подключение текущего чата и скриншот не подтверждены.
- 2026-09-24T09:07:31.627244+00:00 · **observed** · Restored code v0.8.1-candidate.1 into separate worktree; current memory retained
- 2026-09-24T09:38:06.037363+00:00 · **reported** · Панель, безопасный возврат, реальный screenshot HTML snapshot и две выборки аккаунта испытаны. Автосбор текущего чата не реализован.
- 2026-09-24T13:49:23.305501+00:00 · **reported** · HTML preview открыт и проверен: вводная справка и раскрывающиеся сведения работают, их состояние сохраняется. Исходные результаты критериев сохранены: полная браузерная приёмка локального сервера остаётся открытой.
- 2026-09-24T13:49:23.401535+00:00 · **reported** · Все сохранённые группы планов сопоставлены с реализацией и пробелами; память уточнена. Обновлённый HTML preview проверен. Полнота исходной истории и независимая приёмка остаются открытыми.
- 2026-09-24T18:20:44.674034+00:00 · **reported** · Аудит цели, планов и сторонних решений
- 2026-09-24T18:20:44.792590+00:00 · **observed** · Local run starting
- 2026-09-24T18:20:44.854394+00:00 · **observed** · Local run running
- 2026-09-24T18:20:55.132694+00:00 · **observed** · Local run succeeded
- 2026-09-24T18:21:12.202168+00:00 · **reported** · Audit DOCTOR
- 2026-09-24T18:21:12.345623+00:00 · **observed** · Local run starting
- 2026-09-24T18:21:12.419062+00:00 · **observed** · Local run running
- 2026-09-24T18:21:12.541216+00:00 · **observed** · Local run failed
- 2026-09-24T18:21:12.631301+00:00 · **reported** · Audit JS
- 2026-09-24T18:21:12.766543+00:00 · **observed** · Local run starting
- 2026-09-24T18:21:12.835306+00:00 · **observed** · Local run running
- 2026-09-24T18:21:12.923812+00:00 · **observed** · Local run succeeded
- 2026-09-24T18:23:32.232532+00:00 · **reported** · Аудит записан; doctor внутри runner FAIL сохранён, продукт не принят.
- 2026-09-24T18:23:32.343223+00:00 · **reported** · Аудит записан; doctor внутри runner FAIL сохранён, продукт не принят.
- 2026-09-24T18:23:32.455989+00:00 · **reported** · Аудит записан; doctor внутри runner FAIL сохранён, продукт не принят.
- 2026-09-24T18:27:37.913522+00:00 · **reported** · Doctor consistency TESTS
- 2026-09-24T18:27:38.068273+00:00 · **observed** · Local run starting
- 2026-09-24T18:27:38.146137+00:00 · **observed** · Local run running
- 2026-09-24T18:27:49.024233+00:00 · **observed** · Local run succeeded
- 2026-09-24T18:27:49.122946+00:00 · **reported** · Doctor consistency DOCTOR
- 2026-09-24T18:27:49.276879+00:00 · **observed** · Local run starting
- 2026-09-24T18:27:49.368062+00:00 · **observed** · Local run running
- 2026-09-24T18:27:49.568847+00:00 · **observed** · Local run succeeded
- 2026-09-24T18:28:39.379853+00:00 · **reported** · Scoped checks passed; doctor overall WARN, product not accepted.
- 2026-09-24T18:28:39.504931+00:00 · **reported** · Scoped checks passed; doctor overall WARN, product not accepted.
- 2026-09-27T09:21:26.211983+00:00 · **reported** · Повторный аудит Arena и согласованная передача контекста
- 2026-09-27T09:21:26.381854+00:00 · **observed** · Local run starting
- 2026-09-27T09:21:26.484398+00:00 · **observed** · Local run running
- 2026-09-27T09:21:37.869354+00:00 · **observed** · Local run succeeded
- 2026-09-27T09:22:41.629921+00:00 · **reported** · 228 tests passed through terminal_runner; page consistency and synthetic stdio transfer verified; product acceptance open.
- 2026-09-27T10:23:54.492631+00:00 · **reported** · GitHub и передача контекста в AI-чат
- 2026-09-27T10:23:54.665829+00:00 · **observed** · Local run starting
- 2026-09-27T10:23:54.753798+00:00 · **observed** · Local run running
- 2026-09-27T10:23:54.841048+00:00 · **observed** · Local run succeeded
- 2026-09-27T10:23:54.967072+00:00 · **reported** · Реализованы GitHub observation и scoped chat handoff; независимое code UX review. 228 Python tests и Node PASS; визуальная приёмка открыта.
- 2026-09-15 · **verified** · Project History Agent originated in ChatGPT chat агент.
- 2026-09-15 · **verified** · Current chat explicitly requested continuation from chat агент.
- 2026-09-16 · **verified** · v0.5 durable history package passed its deterministic and real-project candidate gates; A6 remained NOT_RUN.
- 2026-09-16 · **requested** · User designated loftfull/FIX as repository for the current project and asked to transfer all current-chat project data and continue development.
- 2026-09-16 · **observed** · Current chat bundle, standing instructions, host-native adapters and v0.6 tests were transferred to FIX working branch.
- 2026-09-16 · **verified** · Local v0.6 regression: 58 tests discovered, 57 PASS, 0 FAIL/ERROR, 1 pre-existing ENV_BLOCKED browser-navigation skip.
- 2026-09-16 · **verified** · GitHub Actions run 35062306733 passed Compile, Repository smoke, Structural audit and Doctor on head 589bea6d60aed243da840b7d0fe2ac5101fee5e6.
- 2026-09-16 · **requested** · User requested continued autonomous development after v0.6 transfer and verification.
- 2026-09-16 · **observed** · Implemented bounded host-history discovery, doctor auto-wiring and CLI discovery/search for v0.7.
- 2026-09-16 · **verified** · GitHub Actions run 35064023880 passed the v0.7 host-history wiring gate on code checkpoint bfbc90f6200150e171036a8367def055f49fd106.
- 2026-09-16 · **verified** · GitHub Actions run 35064575273 passed stable-identity candidate ranking on code checkpoint f2628d2a65294c063b0098ceb84b3d011b8208a4.
- 2026-09-23 · **observed** · Implemented experimental read-only MCP bridge using official SDK 2.2.0; 42 local tests passed, including 10 bridge checks. Independent agent audit found redaction and provenance defects, corrected with regressions. INSTA completeness, remote ChatGPT access and daily autonomy remain untested; A6 remains open.
- 2026-09-24 · **observed** · Implemented revision-preserving normalized import, branch-aware ChatGPT adapter, sourced strategy review and local Git watcher with daily catchup. 90 local tests PASS; real 18-message chat and 139 INSTA issue comments plus two documents imported; repeated imports idempotent. Independent audits closed reproduced metadata/date/filter/redaction and handoff constraints defects. Original INSTA chats, user-machine deployment and full A6 remain unavailable/unaccepted.
- 2026-09-24 · **observed** · Initial Windows CI executed 58 tests with 1 failure and 6 errors from implicit cp1252 reads in test assertions; Linux jobs passed. Four test modules now explicitly read/write UTF-8. Windows rerun pending; no production readiness claim.
- 2026-09-24 · **verified** · GitHub Actions run 35960378708 completed success at code checkpoint 502677ec58429775bb24c3d602f0ebda22221875; Windows58 tests passed, Linux and repository verification jobs passed.
- 2026-09-24 · **observed** · Analyzed all three uploaded brief documents; implemented journal-backed terminal tasks and read-only dashboard.110 local tests passed; independent component audit20 passed after3 reproduced fixes. Browser local/file navigation blocked; visual appearance and user-machine deployment not verified.
- 2026-09-24 · **observed** · Added brief compiler, explicit bounded command supervisor, scoped project registry, offline pixel receipts and real-chat preservation checker.168 local tests and57 independent component tests passed.18-message real archive preserved and read over MCP in successful control trials; cold handoff recovered scope. Two earlier journal-tail-loss incidents remain unexplained; full acceptance blocked. Claude/Codex CLI and user-machine autostart not tested.
- 2026-09-24 · **observed** · Current ChatGPT live connection was not established by previous CLI/MCP trial. Browser on2026-09-24 is logged out; account chat history unavailable until secure authentication. Dashboard must show NOT_CONNECTED.
- 2026-09-24 · **observed** · 201local testsPASS; real18messages exact/idempotent import and MCP passed. Independent rollback collision/filter defects corrected. Current ChatGPT account browser logged out; live connection and real screenshot not accepted.
- 2026-09-24 · **observed** · Audited own history and donor implementation; found stale structured memory and incomplete raw-chat coverage. Independent reviewer agrees core coherence but priority risk; no full acceptance.
- 2026-09-24 · **reported** · agentclientprotocol/python-sdk: researched
- 2026-09-24 · **observed** · control-browser: used_in_session
- 2026-09-24 · **observed** · pyeventsourcing/eventsourcing: tested
- 2026-09-24 · **observed** · ayghri/i-have-adhd: ideas_adapted
- 2026-09-24 · **observed** · git/git: implemented
- 2026-09-24 · **observed** · GitHub connector: used_in_session
- 2026-09-24 · **observed** · modelcontextprotocol/python-sdk: tested
- 2026-09-24 · **observed** · rstacruz/nprogress: code_integrated
- 2026-09-24 · **observed** · python-pillow/Pillow: tested_fixtures
- 2026-09-24 · **reported** · microsoft/playwright: researched
- 2026-09-24 · **reported** · restic/restic: researched
- 2026-09-24 · **observed** · Actual FIX checkpoint restored into separate worktree. Code SHA and3changed component files match. Canonical history retained at original root; no app execution or real screenshot.
- 2026-09-27 · **observed** · No Arena commits found on published refs. Added optional journal-tip guard and real subprocess synthetic transmission: 228 Python tests through terminal_runner and both JS suites PASS. Original archive completeness, continuous ingestion and A6 remain open.
- 2026-09-27 · **observed** · Vendored MIT loading.css; fetch-gated motion and factual run cards. Five dashboard tests pass; browser localhost blocked, visual acceptance open.
- unknown date · **observed** · Windows ran136 tests:3 assertions compared short8.3 paths with canonical paths. Expected paths corrected;30 affected local tests pass. Windows rerun pending. Journal-tail loss reproduced in diagnostic probe; cause remains unknown.
- unknown date · **observed** · Integrated adapted MIT i-have-adhd focus and eventsourcing9.5.5 SQLite witness.190 local testsPASS,47 independent component checksPASS. Real18messages MCP preserved; controlledrollback rejected and recovered in newfolder. Natural loss cause and reappearinglock remain unknown. ACP/restic/Playwright evaluated, not connected.
- unknown date · **observed** · Windows158tests found4cleanup errors: SQLite handle leaked by eventsourcing9.5.5 connection setup failure and test fixtures. Narrow local pool closes handle on setup error; fixtures explicitly close. New resource regression added;48 related local checksPASS. Windowsrerun pending; original journal rollback stillunknown.
- unknown date · **observed** · Воспроизведена частичная публикация bootstrap. Исправлено создание полного журнала под writer lock с одной атомарной публикацией. 218 тестов полного прогона PASS и 4 bootstrap теста PASS после добавления concurrency. Это не доказательство первопричины прежнего rollback и не power-loss испытание.
- unknown date · **observed** · 213local testsPASS; runtime batch structural validation and atomic segment publication; real stored28+15messages preservationPASS/repeat0. Numeric rollover fixed and active segment reused. Prior repair CI35989946526success. Legacy bootstrap remains separate.
- unknown date · **observed** · Initial B1-B5 audit cases fixed.209local testsPASS including5targeted regressions. Portalocker3.2.0 OS locks, replay preflight, lifecycle identity checks, Cookie headers scrub, full native handoff. Structural references/batch atomicity and Windows CI remain separate boundaries.
- unknown date · **observed** · Authenticated browser observed current request. Private samples28+15 imported exactly after redaction, repeat0, fresh MCP reads43. Partial DOM only; original completeness unknown; continuous ingestion absent. Supersedes earlier logged-out availability observation only.
- unknown date · **observed** · Independent no-brief audit:204existing testsPASS but five defects reproduced in temporary fixtures: stale-lock stealing, unreplayable appended mutation, lifecycle cross-project identity, Cookie header redaction gap, native handoff truncation. No fixes applied. Alternatives assessed; not external A6.
- unknown date · **observed** · Observed on2026-09-24: previous-code CI35971960099 success at0b86b839; supersedes pending rerun expectation, not historical failed records.
- unknown date · **observed** · Проверены планы и доступные сообщения пяти чатов: сохранность выборки, повторный импорт без дублей, чтение новым процессом. Полный переход после лимита не доказан. Интерфейс проверен в HTML preview: раскрытие, закрытие и сохранение состояния после перерисовки. 213 локальных тестов PASS; A6, полный экспорт и live polling открыты.
- unknown date · **observed** · Browser access evidence updated after secure login
- unknown date · **observed** · Correct integration limitation field; manual browser reading observed, subscription absent
- unknown date · **observed** · Исправлена потеря canonical полей в экспорте панели. Все поля сравнены при JSON roundtrip новым процессом и с HTML payload. Пять dashboard тестов PASS. README/current checkpoint уточнены. Browser copy/download и семантическая передача новой модели ещё не проверены.
- unknown date · **observed** · Reproduced mixed-generation read; locks and bounded checkpoint retry added. 223 tests PASS; real runner doctor WARN with state checks PASS on attempt2.
- unknown date · **reported** · Внешняя независимая приёмка A6
- unknown date · **reported** · Самостоятельный сбор текущего чата
- unknown date · **reported** · Частично созданный первоначальный журнал
- unknown date · **reported** · Ложное расхождение при работе терминала
- unknown date · **reported** · Потеря полей при передаче контекста
- unknown date · **reported** · Полная история и переход между чатами
- unknown date · **reported** · Захват блокировки по возрасту
- unknown date · **reported** · Причина исторической потери хвоста
- unknown date · **reported** · Потеря отменённых решений
- unknown date · **reported** · Понимание интерфейса новым пользователем
- unknown date · **observed** · Реальный browser clipboard после ручного копирования точно совпал с полным JSON пакетом. Независимый читатель без контекста восстановил 7 ограничений, 3 конфликта, 2 вопроса и цепочку чатов. Download bytes не проверены; отменённое решение отсутствует в эталоне; A6 открыт.
- unknown date · **observed** · Installed Portalocker and runtime import confirmed
- unknown date · **observed** · Message viewing, copy fallback, local favorites and portable JSON added. JS logic tests and4dashboard testsPASS. Actual HTML preview rendered15user messages; favorite addition observed; clipboardAPI blocked, manual selected-copy235chars exact. Private preview excluded from Git.
- unknown date · **observed** · Progressive context tool and selected-chat quick import implemented;12tests PASS; private real43message sample pagination/import checks PASS. No OpenViking runtime or account subscription installed.
- unknown date · **observed** · Все сохранённые группы планов сопоставлены с кодом/проверками/пробелами; текущие описания уточнены append-only patches. Добавлены atomic/context/messages подпланы. Полнота исходников и A6 открыты; дополнительные authenticated выборки частичны. Упрощённый UI проверен экспертно и локальными проверками; новое browser испытание ожидается.
- unknown date · **observed** · User requested migration to loftfull/agent-terminal; destination verified empty and writable; selected local agent history and dashboard prepared for push. Original FIX preserved.
- unknown date · **observed** · 219 Python tests and JS pass; runner doctor snapshot mismatch observed, quiescent doctor WARN. Core user scenario incomplete; donor ideas distinguished from runtime.
- unknown date · **observed** · Исправлена потеря текстов/источников заменённых решений в review output. Новый тест RED→GREEN, 215 локальных тестов PASS. Читатель без контекста правильно разобрал документированный curated пример. Browser download event timed out; скачанные bytes не подтверждены.
- unknown date · **reported** · Координатор наблюдал работающий HTML preview: вводная справка открывается, правила сохраняют открытое и закрытое состояние после перерисовки и перехода История → Обзор. Локальный live polling, пользовательская установка и внешний A6 не проверены этим испытанием.
- unknown date · **requested** · Use terminal in current chat; audit history, plan completeness, context loss and donor benefits; GitHub-first before new features. Original message timestamp unknown; observed this session.
- unknown date · **observed** · Independent source UX review; constraints/focus preserved, wrong-project MCP removed, GitHub API 7/7 sections observed. See docs/UX_REVIEW_2026-09-27.md. Browser visual acceptance remains open.

## 7. Варианты и ответвления
- `v0.3-ledger-auditor` — v0.3 deterministic ledger · archived
- `v0.4-lineage-handoff` — v0.4 lineage + handoff · archived
  - continues → `v0.3-ledger-auditor`
- `v0.5-durable-journal` — v0.5 durable journal · archived
  - continues → `v0.4-lineage-handoff`
- `v0.6-host-native-adapters` — v0.6 FIX canonical repo + host-native adapters · candidate
  - continues → `v0.5-durable-journal`
- `v0.7-host-wiring` — v0.7 bounded direct host-history wiring · candidate
  - continues → `v0.6-host-native-adapters`
- `history-runtime` — MCP/import/watch historian continuation · candidate
  - continues → `v0.7-host-wiring`
- `terminal-support` — Requested terminal supporting components · candidate
  - continues → `history-runtime`
- `vault-integrity` — Persistence witness investigation · candidate
  - continues → `history-runtime`

## 8. Нерешённые противоречия
- Полные экспорты текущего чата и INSTA отсутствуют. Позднее получены авторизованные частичные наблюдения сообщений; они не подтверждают полноту истории или отсутствие потерь.
- Integrity incident: natural journal-tail rollback and reappearing stale locks remain unexplained. Witness recovery does not establish root cause.
- Priority risk: terminal UI/supervisor advanced before A6 and P1 historian governance; prioritize history completeness now.

## 9. Очередь поиска
- Run A6 independent external-model audit against primary evidence + segmented journal + snapshot + current-chat bundle.
- Evaluate pre-compaction/session-end hooks for discovered Claude Code and Codex hosts.

## 10. Источники
- `S001` — Earlier ChatGPT chat агент
- `S002` — Current ChatGPT continuation chat bundle
- `S003` — v0.5 Library baseline
- `S004` — FIX GitHub code checkpoint
- `S005` — v0.6 local regression output
- `S006` — GitHub Actions run 35062306733
- `S007` — User continuation request for v0.7
- `S008` — FIX v0.7 working branch
- `S009` — v0.7 GitHub Actions run 35064023880
- `S010` — v0.7 ranking GitHub Actions run 35064575273
- `S011` — MCP foundation local trial and research 2026-09-23
- `S012` — Real evidence import, INSTA partial reconstruction and local observer trial
- `S013` — Windows CI encoding failure and explicit UTF-8 correction
- `S014` — Windows and Linux CI passed after UTF-8 correction
- `S015` — Analysis of three uploaded Claude brief materials and implementation plan
- `S016` — Terminal component local trial and independent audit
- `SRC-TERMINAL-3a777a8df424c5c632b9596ee8a04d0049e15b3655a959cd7817bb4058e5c90c` — terminal-cli:terminal-visual-control-2026-09-24/3a777a8df424c5c632b9596ee8a04d0049e15b3655a959cd7817bb4058e5c90c
- `SRC-TERMINAL-6fedbe8affe0b55dc0cbd64b8fbe05e94708e8dc7f2c4f4b5dbf707d874a4395` — terminal-cli:terminal-visual-control-2026-09-24/6fedbe8affe0b55dc0cbd64b8fbe05e94708e8dc7f2c4f4b5dbf707d874a4395
- `S017` — Recommendation implementation and real-chat terminal trial
- `S018` — Windows CI path normalization failures
- `S019` — GitHub integration and real vault trial
- `S020` — Windows SQLite resource failure and fix
- `S021` — Current visible user request, partial chat coverage
- `S022` — Source and implementation audit of FIX
- `S023` — CI35971960099 success rechecked
- `SRC-TERMINAL-6700a8a7383052d78f91281cb4b26f785ef8d1da3b9a22a90c9d1ec4e894152c` — terminal-cli:current-chat-audit-2026-09-24/6700a8a7383052d78f91281cb4b26f785ef8d1da3b9a22a90c9d1ec4e894152c
- `SRC-TERMINAL-a84ad43efe3409331e01513993cc4fae4fcd6418f168745e34825e9901b04f56` — terminal-cli:current-chat-audit-2026-09-24/a84ad43efe3409331e01513993cc4fae4fcd6418f168745e34825e9901b04f56
- `SRC-EV-RUN-0f9623ad8baf4c3c9671355fc99fb27c-starting` — local-run:0f9623ad8baf4c3c9671355fc99fb27c
- `SRC-EV-RUN-0f9623ad8baf4c3c9671355fc99fb27c-running` — local-run:0f9623ad8baf4c3c9671355fc99fb27c
- `SRC-EV-RUN-0f9623ad8baf4c3c9671355fc99fb27c-succeeded` — local-run:0f9623ad8baf4c3c9671355fc99fb27c
- `S024` — Current project runner and MCP audit receipt
- `S025` — Independent audit scope review
- `SRC-TERMINAL-c96b6a2251ecd69dad30b37726282c9eddcb0dff072d69cedb1db8365b13f765` — terminal-cli:current-chat-audit-2026-09-24/c96b6a2251ecd69dad30b37726282c9eddcb0dff072d69cedb1db8365b13f765
- `S026` — User dashboard/version request and observed logged-out ChatGPT browser
- `S027` — GitHub-first dashboard and checkpoint plan
- `SRC-TERMINAL-317df8d223f508328ecae0075de6c9cb21fcfec25f1c540f901fd0970e078dc1` — terminal-cli:dashboard-versions-20260924/317df8d223f508328ecae0075de6c9cb21fcfec25f1c540f901fd0970e078dc1
- `SRC-TERMINAL-69804b086f088c5de6db8de7a4162611cf25cccf000cb44b0b1151721b552797` — terminal-cli:dashboard-versions-20260924/69804b086f088c5de6db8de7a4162611cf25cccf000cb44b0b1151721b552797
- `SRC-EV-RUN-e6a2027dc3284f469a9173c2b84cd330-starting` — local-run:e6a2027dc3284f469a9173c2b84cd330
- `SRC-EV-RUN-e6a2027dc3284f469a9173c2b84cd330-running` — local-run:e6a2027dc3284f469a9173c2b84cd330
- `SRC-EV-RUN-e6a2027dc3284f469a9173c2b84cd330-succeeded` — local-run:e6a2027dc3284f469a9173c2b84cd330
- `S028` — Dashboard/version validation and real-chat limitations
- `SRC-TERMINAL-f68dd67aca7989dd1f1808bca90acc519d64619e7af403269a7cf20b425c8775` — terminal-cli:dashboard-versions-20260924/f68dd67aca7989dd1f1808bca90acc519d64619e7af403269a7cf20b425c8775
- `SRC-CHECKPOINT-v0.8.1-candidate.1` — Observed code checkpoint v0.8.1-candidate.1
- `SRC-SCREENSHOT-d62b38fb3a48d1a7983c701132c2cd25b1f5afe0da5380936991a17d0e13c7e2-v0.8.1-candidate.1` — Actual ChatGPT Library HTML preview browser capture; snapshot dated 2026-09-24T09:07:32Z; application area only; no live polling tested
- `S029` — Authenticated browser sample and snapshot trial, private originals excluded
- `SRC-TERMINAL-f2e7a1bee17fed0a5879a66bea4bfae7fb2837b1698c31a3afa31acc83ae4cb2` — terminal-cli:dashboard-versions-20260924/f2e7a1bee17fed0a5879a66bea4bfae7fb2837b1698c31a3afa31acc83ae4cb2
- `S030` — OpenViking bounded adoption and real-sample trial
- `S031` — Independent no-brief code audit and synthetic reproductions
- `S032` — Audit repair decisions and209test validation
- `S033` — Atomic import and structural runtime validation
- `S034` — User messages and portable favorites trial
- `S-PLAN-COVERAGE-20260924` — All-plan coverage, scoped status reconciliation and expert newcomer review
- `S-UI-DISCLOSURE-OBSERVATION-20260924` — Coordinating reviewer browser observation of updated HTML preview
- `SRC-TERMINAL-c3db5ce0582a0081d4f6a3a6c9f5849015952974419457b911657fccbc5d115b` — terminal-cli:terminal-visual-control-2026-09-24/c3db5ce0582a0081d4f6a3a6c9f5849015952974419457b911657fccbc5d115b
- `SRC-TERMINAL-2e55cf3f5d0d32ed8f7dd9bdad393b5af062ae76efcf7487165cfa1fb449b73a` — terminal-cli:current-chat-audit-2026-09-24/2e55cf3f5d0d32ed8f7dd9bdad393b5af062ae76efcf7487165cfa1fb449b73a
- `S-CONTINUITY-UI-20260924` — Bounded account continuity and UI trial
- `S-CRITIC-REPAIRS-20260924` — Critic findings and scoped export repairs
- `S-HANDOFF-BROWSER-20260924` — Real clipboard and package-only reader trial
- `S-SUPERSESSION-TRIAL-20260924` — Superseded decision preservation and reader trial
- `S-ATOMIC-BOOTSTRAP-20260924` — Atomic initial journal publication repair
- `SRC-TERMINAL-f3a3029dcb9acef6c19391baca050a762448017f6d99f6d4ea8cd19164da19c4` — terminal-cli:AUDIT-STATE-20260924-FINAL/f3a3029dcb9acef6c19391baca050a762448017f6d99f6d4ea8cd19164da19c4
- `SRC-EV-RUN-a6657d73e8114beebee3f88992a2f2f6-starting` — local-run:a6657d73e8114beebee3f88992a2f2f6
- `SRC-EV-RUN-a6657d73e8114beebee3f88992a2f2f6-running` — local-run:a6657d73e8114beebee3f88992a2f2f6
- `SRC-EV-RUN-a6657d73e8114beebee3f88992a2f2f6-succeeded` — local-run:a6657d73e8114beebee3f88992a2f2f6
- `SRC-TERMINAL-f3197809fdfa19dba710b89ade056c9c234897f688a124a1e1c682da6ce12955` — terminal-cli:AUDIT-STATE-20260924-DOCTOR/f3197809fdfa19dba710b89ade056c9c234897f688a124a1e1c682da6ce12955
- `SRC-EV-RUN-b6f36ef6a91d48f7bcedf917e7121a04-starting` — local-run:b6f36ef6a91d48f7bcedf917e7121a04
- `SRC-EV-RUN-b6f36ef6a91d48f7bcedf917e7121a04-running` — local-run:b6f36ef6a91d48f7bcedf917e7121a04
- `SRC-EV-RUN-b6f36ef6a91d48f7bcedf917e7121a04-failed` — local-run:b6f36ef6a91d48f7bcedf917e7121a04
- `SRC-TERMINAL-2a445981b5de51e79b6671c1705dd1fa1e6e10734de3171d14fb9c731b537568` — terminal-cli:AUDIT-STATE-20260924-JS/2a445981b5de51e79b6671c1705dd1fa1e6e10734de3171d14fb9c731b537568
- `SRC-EV-RUN-7b9efe19f632485c949934b8a355d78b-starting` — local-run:7b9efe19f632485c949934b8a355d78b
- `SRC-EV-RUN-7b9efe19f632485c949934b8a355d78b-running` — local-run:7b9efe19f632485c949934b8a355d78b
- `SRC-EV-RUN-7b9efe19f632485c949934b8a355d78b-succeeded` — local-run:7b9efe19f632485c949934b8a355d78b
- `S-STATE-AUDIT-20260924` — Аудит цели, планов и интеграций
- `SRC-TERMINAL-5d29a261974dd8068ba449e7ce91f3cb498edd9a1f53b81cf264eb41932a48ba` — terminal-cli:AUDIT-STATE-20260924-FINAL/5d29a261974dd8068ba449e7ce91f3cb498edd9a1f53b81cf264eb41932a48ba
- `SRC-TERMINAL-5835ef6b24097c498b629276e60dac259ec8b7b4be44b66185588821fd90ecae` — terminal-cli:AUDIT-STATE-20260924-DOCTOR/5835ef6b24097c498b629276e60dac259ec8b7b4be44b66185588821fd90ecae
- `SRC-TERMINAL-e1c7170cd672a0116032fc2cbef99ba82eaa31b53387187c27adfc8384d96138` — terminal-cli:AUDIT-STATE-20260924-JS/e1c7170cd672a0116032fc2cbef99ba82eaa31b53387187c27adfc8384d96138
- `SRC-TERMINAL-46efc4c8afc73207cd5bc298df547609d5a425b7a8ac1f33f078cb0427775e77` — terminal-cli:DOCTOR-CONSISTENCY-20260924-TESTS/46efc4c8afc73207cd5bc298df547609d5a425b7a8ac1f33f078cb0427775e77
- `SRC-EV-RUN-f29698a5251840b9954ec29777bf567d-starting` — local-run:f29698a5251840b9954ec29777bf567d
- `SRC-EV-RUN-f29698a5251840b9954ec29777bf567d-running` — local-run:f29698a5251840b9954ec29777bf567d
- `SRC-EV-RUN-f29698a5251840b9954ec29777bf567d-succeeded` — local-run:f29698a5251840b9954ec29777bf567d
- `SRC-TERMINAL-2dad7f53965aaee297e806dcc6bec41b5bdca6d5190782141810eb85cda9c1c9` — terminal-cli:DOCTOR-CONSISTENCY-20260924-DOCTOR/2dad7f53965aaee297e806dcc6bec41b5bdca6d5190782141810eb85cda9c1c9
- `SRC-EV-RUN-b8e516a75e9b4486abce0ec1a67f1930-starting` — local-run:b8e516a75e9b4486abce0ec1a67f1930
- `SRC-EV-RUN-b8e516a75e9b4486abce0ec1a67f1930-running` — local-run:b8e516a75e9b4486abce0ec1a67f1930
- `SRC-EV-RUN-b8e516a75e9b4486abce0ec1a67f1930-succeeded` — local-run:b8e516a75e9b4486abce0ec1a67f1930
- `S-DOCTOR-CONSISTENCY-20260924` — Doctor consistent read repair
- `SRC-TERMINAL-eb367dfe3ccb753532d2cda41040137effb7618868a647a0dae60da15417247e` — terminal-cli:DOCTOR-CONSISTENCY-20260924-TESTS/eb367dfe3ccb753532d2cda41040137effb7618868a647a0dae60da15417247e
- `SRC-TERMINAL-a597839b8aa1eb67b3ac0e7956973a564ef9bbdbe7dc986c95cfab78f38b8f07` — terminal-cli:DOCTOR-CONSISTENCY-20260924-DOCTOR/a597839b8aa1eb67b3ac0e7956973a564ef9bbdbe7dc986c95cfab78f38b8f07
- `S-VISUAL-PROGRESS-20260924` — Визуальная карта планов и аудитов
- `S-REPO-MIGRATION-20260927` — Agent Terminal repository migration
- `SRC-TERMINAL-02b2593a2a39ba15ef7af3f82af69146162aeed6fcdd16d994c8bd590f2cd39c` — terminal-cli:CONTEXT-CONSISTENCY-20260927/02b2593a2a39ba15ef7af3f82af69146162aeed6fcdd16d994c8bd590f2cd39c
- `SRC-EV-RUN-120d1e4ee9e74daea4293931100c59fc-starting` — local-run:120d1e4ee9e74daea4293931100c59fc
- `SRC-EV-RUN-120d1e4ee9e74daea4293931100c59fc-running` — local-run:120d1e4ee9e74daea4293931100c59fc
- `SRC-EV-RUN-120d1e4ee9e74daea4293931100c59fc-succeeded` — local-run:120d1e4ee9e74daea4293931100c59fc
- `S-ARENA-REAUDIT-20260927` — Arena re-audit and actual context transmission tests
- `SRC-TERMINAL-2a029d596d0708dcaf47ba4805ceb94925f15be9128474615c67b3e06ae8b6a6` — terminal-cli:CONTEXT-CONSISTENCY-20260927/2a029d596d0708dcaf47ba4805ceb94925f15be9128474615c67b3e06ae8b6a6
- `S-STUDIO-MOTION-20260927` — Vendored studio motion
- `SRC-TERMINAL-c5227df03d632d375a36849dc82f94df623da7e0826d0148845ce9d074c1656f` — terminal-cli:ux-connections-20260927/c5227df03d632d375a36849dc82f94df623da7e0826d0148845ce9d074c1656f
- `SRC-EV-RUN-5e565ba474054c6cb6743495831d4679-starting` — local-run:5e565ba474054c6cb6743495831d4679
- `SRC-EV-RUN-5e565ba474054c6cb6743495831d4679-running` — local-run:5e565ba474054c6cb6743495831d4679
- `SRC-EV-RUN-5e565ba474054c6cb6743495831d4679-succeeded` — local-run:5e565ba474054c6cb6743495831d4679
- `SRC-TERMINAL-8dd56a8978ba026706e927fb9cccbe391f68fa5c02cdd954b988fb5864710fa5` — terminal-cli:ux-connections-20260927/8dd56a8978ba026706e927fb9cccbe391f68fa5c02cdd954b988fb5864710fa5

## 11. Передача
- Текущий чат: chat-current-project-history-agent
- Следующий шаг: Проверить интерфейс в доступном браузере: мобильный layout, клавиатура, контраст; затем спроектировать авторизованное подключение приватных репозиториев. A6 и непрерывный сбор чатов остаются открытыми.
- Обновлено: 2026-09-27T10:23:55.100230+00:00
