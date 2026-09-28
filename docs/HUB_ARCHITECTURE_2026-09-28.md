# Agent Terminal — архитектура визуального хаба

Основание: запрос 2026-09-28. Решение: закончить общую навигацию, модель данных и
границы модулей; далее развивать вертикальные сценарии. Не создавать второй IDE
или универсальный чат. Это реализованный UI-каркас над существующим ядром,
а не заявление полной готовности всех интеграций и источников истории.

## Рабочие области

| Область | Реализованный сценарий | Граница |
|---|---|---|
| Панорама | Следующий шаг, 5 этапов с источниками, внимание, изображение checkpoint | Этапы не означают процент приёмки; текущий код не сравнен с изображением |
| План | Планы, изменения, проверки, задачи и история активности | Статусы исполнителей отделены от приёмки |
| Исполнители | Последние запуски, фильтры модели/сессии/статуса, вывод команды | Нет heartbeat и запуска модели из браузера |
| Версии | Commit/checkpoint, изображение, описание безопасного возврата | Restore выполняется существующим CLI в новый worktree |
| Контекст | Выбор задачи, сохранение guardrails, цепь supersedes, full JSON, предложение поправки | Компактный пакет частичный, предложение не применено |
| Подключения | GitHub/public snapshot, локальный MCP, перенос текста, каталог внешних продуктов | LangGraph/Langfuse показаны как внешние и не подключены |

Дополнительные представления: задачи, аудиты, сообщения, избранное, история,
компоненты, расположения, визуальные материалы. Ни один реестр не удалён.

## Модули и направление данных

1. Source adapters: evidence_import.py, history_watch.py, web/connections.js.
   HTTP-наблюдение GitHub остаётся отдельно до явного импорта с project_id.
2. Durable core: project_history_journal.py + runtime_journal.py: append-only,
   lock, replay, hash-chain, atomic batch. terminal_vault.py — внешний witness.
3. Work control: terminal_control.py (контракты/отчёты), terminal_runner.py
   (ограниченный явный запуск), terminal_versions.py (code checkpoints/restore).
4. Read API: project_history_mcp.py (локальный stdio), terminal_dashboard.py
   (HTTP read-only, fail-closed при нарушении цепочки).
5. Application projections: web/hub_model.js: routes, observations, context pack.
   web/hub_ui.js: страницы и пользовательские действия. Оба не пишут журнал.
6. UI shell: web/terminal.html + hub.css, общая типографика и навигация.
   Изменение backend не требует замены оболочки. Старые реестры переиспользуются.
7. Browser persistence: repository_cache.js и message_library.js. Это локальные
   удобства, не каноническое хранилище, резервная копия или межустройственная sync.

## Контракты и полномочия

- Новый адаптер обязан указывать project_id, source URI/revision, дату, класс
  доказательства, coverage и пропуски. Контракт для следующего этапа:
  schemas/hub-adapter-observation.schema.json. Он пока НЕ подключён к ingestion.
- Canonical mutation имеет отдельную проверку identity и expected journal tip,
  маскировку секретов, атомарную запись и receipt. Браузер не получает shell.
- Поправка: requested proposal → проверка исполнителем → новая запись с причиной
  и ссылкой на заменяемое свидетельство. Кнопка пока экспортирует proposal JSON;
  автоматическое применение и подтверждение не реализованы.
- Контекст содержит project_id/tip, обязательные ограничения всех задач,
  stop_conditions/acceptance, конфликты, поиск недоступных источников, выбранные
  задачи и свидетельства с прямой supersedes-цепью. Несвязанные события опущены
  явно; для них нужен полный JSON или MCP. Нет гарантии полноты внешних архивов.
- Полный JSON передаёт все имеющиеся поля read model. Откат кода не откатывает
  историю. Никаких фиктивных «активных моделей», денег или процентов готовности.

## Следующие вертикальные этапы

1. Apply/import gateway: импорт GitHub-наблюдений и предложений поправок с
   provenance, project binding, optimistic tip check, idempotency и dry-run.
2. Provider pilot: один реальный LangGraph/ACP backend с capability handshake,
   отменой, reconnect и receipts; только затем следующие провайдеры.
3. Visual artifact pipeline: actual screenshot + build SHA + viewport + timestamp;
   сравнение версий через существующий visual module.
4. Context budgets: токенизатор выбранной модели, явный тариф и использование;
   до этого показываем только число символов, не денежную экономию.
5. Desktop/mobile browser acceptance, внешний A6 и real archive coverage.

## Проверка и статус

Source review независимым агентом: 4 дефекта исправлены и повторно проверены.
DOM regression: 14 разделов, 6 основных маршрутов, context workflow, cache/transfer.
Model regression: guardrails вне выбранной задачи, needs_review, supersedes,
identity rejection и стабильный polling signature. Native rendering, качество
премиального дизайна, реальные downloads и focus trap остаются без визуальной
приёмки. Старый browser block не обходился по указанию пользователя пропустить его.

Итоги текущего прогона: 228 Python tests PASS, Node model/connection/cache/receipt/
run tests PASS, DOM routes and handoff PASS. Дизайн-детектор по новым hub-файлам
не выдал замечаний; это анализ исходников, не оценка реальных пикселей.
На предварительном снимке полный JSON = 492763 символа, пакет по умолчанию =
42976 символов до добавления сведений о контрольных точках и путях. Это разный
объём передаваемых сведений; не без потерь и не измерение денежных расходов.
