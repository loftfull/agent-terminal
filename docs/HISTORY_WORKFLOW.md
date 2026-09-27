# Импорт и наблюдение истории

Состояние: экспериментальная версия. Испытания описаны в
`REAL_EVIDENCE_TRIAL_2026-09-24.md`. Полная история INSTA пока недоступна.

## Импорт

```sh
python evidence_import.py --root /absolute/memory/project --project-id project-id --input normalized.json --session-id exact-session-id
```

Вход `{"sessions":[{"session_id":"exact-session-id","source_uri":"source","messages":[{"id":"message-id","role":"user","text":"full text","create_time":null,"metadata":{}}]}]}`.
Повторяемый `--session-id` выбирает несколько сессий. ID не угадываются из темы.
Содержимое остаётся `reported`, включая слова ассистента «тест прошёл».

Для ChatGPT conversations.json используйте `ChatGPTExportHistoryAdapter.inspect(id)`;
результат можно положить в массив sessions. Сохраняются все экспортированные ветви,
активная цепочка выделяется только при достоверном current_node. Неизвестный путь
помечается. Ссылки на вложения сохраняются, сами внешние файлы не скачиваются.

## Наблюдатель в отдельном терминале

```sh
python history_watch.py --root /absolute/git/project --memory-root /absolute/memory/project --project-id project-id --initialize --once
python history_watch.py --root /absolute/git/project --memory-root /absolute/memory/project --project-id project-id --watch --interval 60
```

На Windows используйте абсолютные Windows-пути в кавычках. Например, каталог
кода и каталог памяти должны быть разными, причём память находится вне наблюдаемого
checkout. Это предотвращает запись собственных отчётов как новых изменений проекта.

`--initialize` явно создаёт журнал. Без него отсутствие журнала — ошибка.
Собираются локальные Git refs/HEAD/branch/status/remotes/worktrees и контрольные суммы
изменённых отслеживаемых файлов. Fetch/push и проектный код не запускаются.
Неотслеживаемые файлы перечисляются по Git status; содержимое не считывается.
Секреты известных форматов очищаются, но это не универсальное распознавание секретов.

По умолчанию день считается по UTC. Итог завершившегося дня создаётся на следующем
такте или после перезапуска, только если в журнале есть наблюдения за этот день.
Число наблюдений не является числом исправленных ошибок или готовых функций.
Закрытие терминала останавливает процесс. Автозапуск/Windows Task Scheduler этим
изменением не устанавливаются; на компьютере пользователя ничего не запущено.

## Доступ модели

MCP-процесс указывает на тот же каталог памяти и project ID:

```sh
python project_history_mcp.py --root /absolute/memory/project --project-id project-id
```

Нужен Python с зависимостями из `requirements-mcp.txt`. Host запускает stdio MCP
с указанной командой. Обычный браузерный ChatGPT автоматически к локальному процессу
не подключается. Запись через MCP пока не предусмотрена: её выполняют импортёр,
наблюдатель и существующие lifecycle hooks.

## Оценка хода проекта

`python history_review.py review-input.json` проверяет источники, явную замену
решений и непрерывность заданной цепочки base/head. Категории work_items задаются
исследователем, а не извлекаются эвристически. `reported_runtime_verified_count`
считает входные заявления, не проверяет их истинность. Пример формата — тесты
`tests/test_history_review.py`. Процент готовности не вычисляется без полного
набора критериев приёмки; автоматического статуса dead_end нет.
