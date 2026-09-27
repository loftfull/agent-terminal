# Готовые решения: выбор и фактическое внедрение

Проверено 24.09.2026. Цель — закрывать конкретные пробелы готовыми компонентами,
сохраняя evidence-классы и доступную историю. Популярность репозитория не является
доказательством пригодности. Нет одного готового проекта, проверенно закрывающего
все наши требования и неизвестный откат файлов.

| Пробел | Готовое решение | Решение / проверяемая граница |
|---|---|---|
| Перегруженная подача, потеря следующего шага | [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd), MIT | Внедрены адаптированные правила в terminal_focus и бриф. Короткий индекс не удаляет данные; блокеры не обрезаются. Не утверждаем диагноз пользователя, не придумываем ETA, не просим «продолжай» вместо разрешённой работы. |
| Правильный hash-chain после удаления хвоста | [pyeventsourcing/eventsourcing](https://github.com/pyeventsourcing/eventsourcing), BSD-3-Clause | Внедрён отдельный SQLite witness через настоящий SQLiteAggregateRecorder 9.5.5. Транзакционная запись, конфликт версий, сравнение префикса, отдельное восстановление. Не доказывает устранение причины rollback и не защищает от одновременного отката обеих копий. |
| Независимая резервная копия вне компьютера | [restic/restic](https://github.com/restic/restic), BSD-2-Clause | Выбран следующим backend. Не установлен и не подключён: нужен выбранный отдельный носитель/репозиторий и восстановительный тест. Снимок SQLite получать через backup API или при остановленном writer; нельзя копировать один DB-файл без WAL. |
| Структурированные события Claude/Codex вместо разбора текста | [agentclientprotocol/python-sdk](https://github.com/agentclientprotocol/python-sdk), [codex-acp](https://github.com/agentclientprotocol/codex-acp), [claude-agent-acp](https://github.com/agentclientprotocol/claude-agent-acp), Apache-2.0 | Выбраны для provider pilot. Не выдаём протокольный echo за вызов модели. Нужны установленный host, фактическая авторизация и проверка cancel/permissions. Старый zed-industries/codex-acp перенесён; preview не использовать как прошедший CI release. |
| Снятие реального интерфейса, traces, baseline | [microsoft/playwright](https://github.com/microsoft/playwright), Apache-2.0 | Подходит для разрешённого browser host, но ранее browser policy дала ENV_BLOCKED. Не обходим запрет и не объявляем fixtures реальными скриншотами. Baseline не обновлять автоматически ради PASS. |
| Долгоживущие workflow и очередь | [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py), MIT; [temporalio/sdk-python](https://github.com/temporalio/sdk-python), MIT | Отложены: миграция workflow и эксплуатация server/database сейчас шире задачи. Изученный DBOS README описывает Postgres, Temporal требует server+worker. Возобновление workflow не заменяет архив проекта. |

Все перечисленные библиотеки/репозитории имеют открытые лицензии. Хостинг,
хранилище и обращения к моделям не становятся бесплатными от использования SDK.
Текущие focus/vault работают локально без платного API. Подписка ChatGPT/Claude
не интерпретируется как разрешение на произвольный платный API.

## Что именно перенесено из i-have-adhd

Прочитаны полный SKILL.md и LICENSE. Исходник правил: Git blob
`9138ae4af11065b7971eea17edc48a2498c1af35`; лицензия:
`19db5f1b0ca65e277c158bd4c4263139ccfd859c`. Это идентификаторы файлов, не SHA коммита.
Текст правил адаптирован в приложении; upstream hooks и install scripts не запускались,
глобальные настройки hosts не менялись. MIT attribution сохранена в
`third_party/i-have-adhd-LICENSE.txt`.

В брифе `output_profile: "focus"` включён по умолчанию; `"standard"` отключает
добавочный стиль. Источники, критерии, причины ограничений и неизвестное сохраняются.
В панели переключатель «Полный обзор»; полные задачи и JSON доступны в обоих режимах.

## Внешний witness: запуск

Python >=3.11. Зависимость фиксирована в requirements-vault.txt.
Локальный subclass connection pool закрывает SQLite handle при setup failure
(дефект9.5.5, обнаруженный Windows CI); BSD3 notice сохранён в third_party.
Обновление зависимости требует повторения ресурсных и Windows тестов.

```powershell
python -m pip install -r requirements-vault.txt
python terminal_vault.py capture --root 'D:\History\Project' --project-id 'project-id' --vault 'D:\HistoryVault\history.sqlite'
python terminal_vault.py verify --root 'D:\History\Project' --project-id 'project-id' --vault 'D:\HistoryVault\history.sqlite'
python project_history_mcp.py --root 'D:\History\Project' --project-id 'project-id' --vault 'D:\HistoryVault\history.sqlite'
python terminal_dashboard.py --root 'D:\History\Project' --project-id 'project-id' --vault 'D:\HistoryVault\history.sqlite'
```

Пути — примеры, а не обнаруженные папки пользователя. Один выбранный vault может
хранить несколько project_id. Файл vault должен находиться вне memory-root.
В runner request JSON добавляется поле `vault` с тем же абсолютным путём. Сначала
выполняется явный capture; runner отказывает при отсутствии ранее настроенного
witness, а не создаёт его молча. Перед запуском и после квитанции сохраняются
проверенные границы; не обещаем защиту каждой записи между этими границами.

Guard optional для совместимости. Без `--vault` MCP/панель честно показывают
`not_configured`; с vault — `matched` или `ahead_of_vault` и число ещё не защищённых
записей. Откат, расхождение, недоступность или повреждение witness дают отказ.
Чтение guard не меняет исходную память. Канонический журнал не переносится в SQLite.

Восстановление — только в НОВУЮ папку:

```powershell
python terminal_vault.py recover --project-id 'project-id' --vault 'D:\HistoryVault\history.sqlite' --destination 'D:\History\Project-Recovered'
```

Исходный повреждённый каталог сохраняется для диагностики. Восстановленные файлы
журнала совпадают с сохранёнными байтами; JSON/Markdown проекции перестраиваются.
Не выбирайте для recovery существующую папку. Никакого автоматического перезапуска
модели, повторной оплаты или исполнения инструкций из архива нет.

## Ограничения witness

- Это резервные контрольные точки, не исправление неустановленной причины потери.
- Локальная SQLite не является независимым off-device backup. Откат/удаление всей
  среды вместе с vault может остаться необнаруженным без внешнего якоря.
- До 64 MiB текстов журнала и 1024 файлов в одной точке. Хранятся полные снимки,
  поэтому размер DB растёт; retention/prune намеренно отсутствует.
- Прямое изменение DB доверенным OS-пользователем не предотвращается. Это не
  криптографическая подпись и не защищённое от администратора хранилище.
- Храним только уже redacted журнал. Обнаруженные токены, включая ключи JSON,
  отклоняются до backup. Произвольная чувствительная проза не распознаётся.
- Capture первоначального уже неполного журнала не восстанавливает никогда не
  наблюдавшуюся историю. Храним полноту источника отдельно от целостности.

## Критерии испытания

1. Реальные 18 сообщений/94 726 символов проходят исходное сравнение и MCP.
2. Повторный capture не добавляет версию; повторный импорт не создаёт сообщений.
3. Искусственный rollback на отдельной копии сохраняет внутренний hash-chain,
   но отвергается witness и MCP.
4. Восстановление в новый каталог сохраняет весь текст, metadata, оригинальные
   даты, модели, task constraints и квитанцию процесса.
5. Независимые проверки повреждения SQLite, конкурентной записи, отсутствующего
   witness, unsafe paths и Windows/Unicode не дают ложного успешного результата.

Исходные INSTA-чаты, пользовательские hosts и полноценная визуальная приёмка
остаются отдельными недоступными/непройденными проверками.

## Сквозной аудит переноса — 2026-09-24

[Полная матрица](CURRENT_CHAT_AUDIT_2026-09-24.md) включает также MCP SDK, Pillow
и более ранние аналоги из history/ANALOG_AUDIT_2026-09-17.md. Разделяет реальные
зависимости, адаптацию идей, планы и неустановленное происхождение. С этого цикла
перед новой функцией обязателен GitHub-first поиск по AGENTS.md. Restic/provider/UI
не являются главным следующим шагом: сначала полнота истории, актуальная память
и устранение конкретных дефектов сохранности. Старое указание «следующим backend»
означает кандидата для backup, а не приоритет над ядром историка.

## Контрольная панель и версии

См. CONTROL_DASHBOARD_PLAN.md: реально перенесён NProgress0.2.0 (MIT) для
индикатора получения данных; готовый Git используется для checkpoint/worktree.
Случайное продвижение NProgress отключено. Он не измеряет готовность проекта.
uPlot и ChatGPT exporters изучены, не интегрированы. Автоматическое подключение
текущего браузерного чата НЕ реализовано; факт CLI/MCP не заменяет его.

## OpenViking — 2026-09-24

volcengine/OpenViking, commit c9a869cb145aac98f4be1586da32174d220c8800,
AGPL-3.0. Adopted progressive structural L0/L1/L2 retrieval and project scoping as
ideas, implemented over existing FIX reader/importer. No upstream source copied,
no runtime installed. New MCP tool and one-command selected-chat import tested
on real43-message samples. See docs/OPENVIKING_ADOPTION.md for boundaries.

## Исправления независимого аудита

Принята готовая runtime dependency wolph/portalocker3.2.0, BSD-3-Clause.
Заменяет ProjectLock на OS-backed locking; не копирование исходников. Проверены
конкуренция с живым владельцем старого lock и освобождение при kill процесса.
Сравнение с eventsourcing/Gitleaks и границы: BLIND_AUDIT_2026-09-24.md;
реализованный объём: AUDIT_REPAIRS_2026-09-24.md.

## Пользовательские сообщения и избранное — 2026-09-24

До реализации исследован zenorocha/clipboard.js v2.0.11, MIT,
package.json blob8efc98c72f1ffbcafac734636d69ebea27fcecc1. Для панели уже есть
native navigator.clipboard: дополнительная библиотека не нужна. При отказе
Clipboard API текст выделяется для ручного копирования; ложного success нет.
Избранное — отдельный локальный browser store + переносимый JSON, без изменения
истории и нового HTTP write endpoint. Код донора не копировался.
Проверки: Unicode/пробелы/переносы, user-only, дедупликация, разные проекты и ревизии,
экспорт/импорт, отказы неправильных/слишком больших файлов. Clipboard и localStorage
зависят от разрешений браузера; при storage failure сохранение только на эту вкладку
с явным предупреждением. Между origin/устройствами перенос через экспорт/импорт.

## Раскрываемые сведения — 2026-09-24

GitHub-first: запросы `github progressive disclosure details summary`,
`accessible-ui/disclosure`. Изучены primer/design,
content/ui-patterns/progressive-disclosure.mdx и опубликованная редакция
https://primer.github.io/design/ui-patterns/progressive-disclosure/
(last edited 2023-02-10; commit SHA не закреплён), accessible-ui/disclosure.
React-компонент не подходит plain-JS панели без дополнительной зависимости.
Применён общий паттерн через native HTML details/summary: без копирования кода,
изображений или текста и без новой зависимости. Разрешение на перенос donor code
не заявляется. Цель: читать историю и следующий шаг, раскрывая IDs/SHA/команды
по запросу. Проверка: HTML preview, раскрытие и сохранение состояния при
перерисовке. Время освоения случайным пользователем пока не измерено.
