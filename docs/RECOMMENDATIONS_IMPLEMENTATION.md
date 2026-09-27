# Внедрение рекомендаций: состояние и границы

Три исходных файла описывают правила постановки задач, а не готовый протокол запуска
моделей. Ниже отделены внедрённые механизмы от испытания на конкретном AI-host.

| Рекомендация | Реализация | Граница |
|---|---|---|
| Цель, результаты, финишная черта одним заданием | terminal_brief compile + immutable task contract | Структурная проверка не определяет смысловую достаточность |
| Убирать общие призывы, задавать конкретную проверку | Семь оценок, лексические предупреждения, вопросы по общим критериям | Исходный текст сохраняется; автоматическое удаление опасно для смысла |
| Ограничения с причинами | rule/reason в контракте, брифе, панели, передаче | Права доступа не расширяются текстом |
| Продолжение долгой работы и файл задач | Журнал, TASKS projection, runner receipt, max_continuations 0–3 | Запускается только явно указанная команда; host messaging adapter не подключён |
| Ждёт меня / Изменено / Найдено | Бриф и панель | Реальный отчёт модели требует вызова модели |
| Интервью только при неоднозначности | next_question + полный список пропусков; short/long режим | Уточнение смысла делает модель/человек; программа не угадывает |
| Зачем и для кого | purpose обязателен | Аудит источника может выявить отсутствующий контекст |
| TASKS переживает сжатие контекста | status --markdown из журнала, MCP чтение | Host обязан вызвать адаптер/прочитать файл |
| Независимые подзадачи и проверка результатов | Независимые разработчики и аудитор текущего цикла | Не постоянный агентский swarm на компьютере пользователя |
| Картинка вместо пересказа | terminal_visual сравнивает выбранные исходные изображения | Pixel gate не означает правильный дизайн; реальная сцена/SHA отдельно |
| Наблюдение модели и смены | model/session сохранены, runner attribution_status=reported | Без достоверных host metadata модель не устанавливается |
| Effort и /fast | Поля конфигурации сохраняются, неизвестное не угадывается | Платный /fast автоматически не включается; измерения конкретного host нужны |
| Отказы и fallback | Ненулевой exit/ошибка/прерывание фиксируются; молчаливой подмены модели нет | Специфические stop_reason обрабатывает будущий provider adapter |
| Не возвращаться к решённому без причины | Идемпотентность, immutable contract, новые revision/supersedes | Новое доказательство может пересмотреть решение |

## Дополнения к запуску

Сборка брифа из JSON контракта:

```sh
python terminal_brief.py compile --input task.json --markdown
python terminal_brief.py check --input task.json
```

Исполнитель запускается только явным request.json. Пример для локального теста
(пути заменяются реальными, поля не копируются из непроверенной переписки):

```json
{
  "root": "D:\\History\\my-project",
  "project_id": "my-project",
  "task_id": "registered-task-id",
  "argv": ["C:\\Python312\\python.exe", "-m", "unittest", "discover", "-s", "tests"],
  "cwd": "D:\\Projects\\my-project",
  "timeout": 120,
  "continuation_count": 0,
  "model_id": "unknown",
  "session_id": "unknown",
  "max_output_bytes": 65536
}
```

```sh
python terminal_runner.py --request request.json
```

Процесс наследует обычные права пользователя, это не песочница. Веб-панель не даёт
shell endpoint. На POSIX используется собственная группа процессов, на Windows —
Job Object с завершением потомков. После падения supervisor старый PID не убивается
вслепую: он мог быть переиспользован. Незавершённая запись становится interrupted,
фактическое состояние старого дочернего процесса остаётся неизвестным.

## Реестр выбранных проектов

```sh
python terminal_projects.py --registry projects.json add --project-id my-project --memory-root "D:\History\my-project" --checkout-root "D:\Projects\my-project" --label "Мой проект"
python terminal_projects.py --registry projects.json list
python terminal_projects.py --registry projects.json launch-plan --project-id my-project --python "C:\Python312\python.exe" --code-root "D:\Tools\FIX"
```

Команды PowerShell только формируются. Глобальные настройки, автозапуск и планировщик
не изменяются. Нужен отдельный запуск и проверка на компьютере пользователя.

## Визуальные свидетельства

Установить `requirements-visual.txt`. Метаданные каждой картинки: source_uri,
captured_at с timezone, scene_id, viewport {width,height,device_scale_factor?}.
Одинаковая сцена и viewport обязательны. Изображения не масштабируются ради PASS.

```sh
python terminal_visual.py --reference reference.png --current current.png --reference-metadata reference.json --current-metadata current.json --channel-threshold 0 --allowed-changed-ratio 0 --difference difference.png
```

SHA файла наблюдается; claimed_sha сборки остаётся reported. Сравнение не
подтверждает происхождение скриншота и семантическую правильность интерфейса.

## Проверка реального чата

```sh
python terminal_chat_check.py --root memory --project-id project-id --input normalized.json --session-id exact-session-id
```

Сравнивает полные сообщения/metadata/источники с журналом после redaction. Повторные
одинаковые запросы с разными message IDs сохраняются. Временные инверсии выводятся,
исходные даты не исправляются. Проверка не выполняет инструкции из архива и не
выдаёт рекомендации из него за сделанные изменения.
