# PROJECT_MEMORY — AI handoff report

## 0. Карточка проекта
- Project ID: `project-history-agent`
- Имя: Project History Agent
- Описание: Portable project historian continued from chat “агент”; current chat is being transferred to canonical GitHub repository loftfull/FIX with host-native history adapters.
- Цель: Preserve evidence-based project history across chats, models, repositories and environments
- Каноническая версия: v0.6 candidate

## 0.1 Быстрый handoff для новой AI-модели
- Project ID: `project-history-agent`
- Каноническая версия: v0.6 candidate
- Текущий чат: chat-current-project-history-agent
- Следующий проверяемый шаг: Complete v0.6 host-native adapters, transfer exact project/chat tree to loftfull/FIX, verify remote SHA, then continue A6 independent-model audit preparation.
- Правило продолжения: сначала прочитать этот отчёт и PROJECT_MEMORY.json; не повышать reported/planned до verified без новой проверки.

## 1. Где находится проект
| Среда | Расположение | Branch | SHA | Статус | Проверено |
|---|---|---|---|---|---|
| — | GitHub location will be patched after exact remote SHA verification | — | — | pending | — |

## 2. Цепочка чатов
| Дата | Чат | Класс | Родитель | Основание |
|---|---|---|---|---|
| 2026-09-15 | агент | new | — | explicit_origin |
| 2026-09-15 | Продолжение проекта из чата «агент» | continuation | chat-agent-origin | explicit |

## 3. Планы → фактические изменения
| План | Статус плана | Связанные версии | Фактически внесено |
|---|---|---|---|
| — | Планы ещё не зафиксированы в chat-specific state | — | — |

## 4. Версии и фактические изменения
- Current chat state points to the project-level v0.6 candidate.

## 5. Скриншоты и визуальные подтверждения
- Visual evidence is stored at project level; current-chat state does not fabricate a version→screenshot mapping.

## 6. Хронология
- 2026-09-16 · **verified** · Current chat explicitly continues chat ‘агент’; origin chat was added to the handoff chain.
- 2026-09-16 · **verified** · Current ChatGPT lineage test migrated to v0.5 append-only journal and replayed successfully.
- 2026-09-16 · **requested** · User designated loftfull/FIX as the repository for the current project, requested transfer of all current-chat project data, and asked development to continue.

## 7. Варианты и ответвления
- Line-level development history is stored in the project-level memory.

## 8. Нерешённые противоречия
- Нет зафиксированных противоречий.

## 9. Очередь поиска
- Verify exact GitHub branch SHA after transfer and patch this current-chat state.

## 10. Источники
- `S-CHAT-ORIGIN` — Earlier ChatGPT chat titled ‘агент’
- `S-CHAT-CURRENT` — Current ChatGPT continuation request
- `S-CHAT-FIX` — Current user request to move project/chat data to loftfull/FIX

## 11. Передача
- Текущий чат: chat-current-project-history-agent
- Следующий шаг: Complete v0.6 host-native adapters, verify remote SHA, then continue A6 preparation.
