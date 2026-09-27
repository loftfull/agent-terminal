# Запуск панели агента-терминала

Требуется Python 3.12+ и скачанный репозиторий FIX. Панель и task CLI используют
стандартную библиотеку Python. MCP отдельно использует requirements-mcp.txt.

## Посмотреть этот проект

Из каталога FIX:

```sh
python terminal_dashboard.py --root . --project-id project-history-agent
```

Откройте `http://127.0.0.1:8765` на том же компьютере. Окно терминала должно оставаться
открытым. Ctrl+C останавливает панель. На Windows вместо python можно использовать py.
Панель не запускает модели и не устанавливает автозапуск. Она читает выбранный
журнал каждые 5 секунд; эта частота не является частотой работы модели.

Панель показывает задачи, историю, расположения, ветви и реестр изображений.
`Источник недоступен` означает, что новое чтение не удалось; прежние данные
остаются историческим снимком с прежней датой. Изображения не загружаются
автоматически; pixel diff и приёмка дизайна ещё не реализованы.

## Подключить выбранный проект

Для проекта без журнала сначала выполните явно разрешённую инициализацию из
`HISTORY_WORKFLOW.md`: watcher --initialize --once создаёт память в отдельном
каталоге. Затем передайте этот memory-root и его project-id панели. Выбор
папки явный: программа не сканирует все диски и чаты компьютера автоматически.

```sh
python terminal_dashboard.py --root "D:\Projects\History\my-project" --project-id my-project
```

Для живого наблюдения нужен отдельный процесс `history_watch.py --watch`.
Это два процесса: observer пишет, панель читает. MCP читает ту же память.

## Зарегистрировать задание

Сохраните JSON в task.json (это вход CLI, не исполняемый сценарий):

```json
{
  "task_id": "search-fix-1",
  "title": "Сохранить поисковый запрос при возврате",
  "purpose": "Пользователь продолжает просмотр без повторного ввода запроса",
  "deliverables": ["Исправление состояния поиска", "Результат regression-теста"],
  "acceptance": ["После открытия и закрытия карточки введённый запрос сохранён"],
  "constraints": [{"rule": "Сохранить структуру навигации", "reason": "Другие экраны используют тот же маршрут"}],
  "stop_conditions": ["Нужен недоступный исходник", "Изменение выходит за разрешённый проект"],
  "max_continuations": 2
}
```

```sh
python terminal_control.py --root "D:\Projects\History\my-project" --project-id my-project submit --input task.json
python terminal_control.py --root "D:\Projects\History\my-project" --project-id my-project status
```

Один task_id соответствует неизменному контракту. Изменение цели требует нового
ID, чтобы история не переписалась. Секреты распознаваемых форматов очищаются до записи.

## Передать отчёт модели

В report.json укажите task_id, status, summary, model_id и session_id, если они
действительно известны. Допустимые status: queued, running, blocked, review, done.
Пример честного блокера:

```json
{
  "task_id": "search-fix-1",
  "status": "blocked",
  "summary": "Для проверки нужен исполняемый preview приложения",
  "model_id": "unknown",
  "session_id": "unknown",
  "blockers": ["Нет доступного preview"],
  "continuation_count": 0,
  "evidence_event_ids": [],
  "acceptance_results": []
}
```

```sh
python terminal_control.py --root "D:\Projects\History\my-project" --project-id my-project report --input report.json
```

`pass` в acceptance_results требует существующих evidence_event_ids и точного
criterion из контракта. Это по-прежнему заявление исполнителя. `done` отображается
как `review`: отдельный acceptance gate ещё не реализован. Нет поддельного зелёного
«принято». Счётчик продолжений ограничен контрактом; отправка продолжений в модели
в этой версии отсутствует. Процесс может быть остановлен, даже если последний
отчёт имеет статус running; прямого heartbeat нет.

## Передача и автономный предпросмотр

```sh
python terminal_control.py --root . --project-id project-history-agent status --markdown
python terminal_dashboard.py --root . --project-id project-history-agent --export terminal-preview.html
```

HTML содержит состояние на момент экспорта, не обновляется и не обращается к
серверу. Можно открыть его обычным браузером. Snapshot содержит историю выбранного
проекта: перед пересылкой учитывайте конфиденциальность. Исходные истории не
выдаются в публичную сеть автоматически.
