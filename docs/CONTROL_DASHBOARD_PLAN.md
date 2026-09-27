# Контроль реализации, версии и реальное подключение чата

Запрос пользователя наблюдён 2026-09-24. GitHub-first поиск до кода:
`animated dashboard vanilla javascript chart uplot`, `gitpython git worktree release
snapshot screenshot`, `ChatGPT conversation export browser extension JSON`.

| Кандидат | Решение |
|---|---|
| rstacruz/nprogress v0.2.0 MIT, JS blob b23b30060e4ad71081e36e6a9b0f63ba562c48eb | Включаем готовый JS с notice для индикации загрузки данных. Отключаем random trickle; не используем done/inc и не называем полоску процентом проекта |
| leeoniya/uPlot | Не нужен для счётчиков состояний: временных числовых рядов нет; график создавал бы ложную метрику |
| git/git, git-worktree.adoc (upstream master, изучено 24 сентября) | Используем установленный Git, pin полного SHA, application-protected checkpoint ref, отдельный worktree; не копируем GPL код Git |
| gitpython-developers/GitPython | Не добавляем Python dependency ради двух команд уже установленного Git |
| maks-bond/chatgpt-conversation-exporter | Исследован экспорт открытой вкладки; не установлен, не объявлен надёжным subscription. DOM/export может пропустить сообщения и не доказывает полноту |

## Контракт

1. Панель: прогресс только по зарегистрированным критериям с явным знаменателем;
   reported pass отдельно от accepted. Общий процент проекта неизвестен.
2. Интеграции: repo/dependency/plugin/skill, версия, происхождение, статус и evidence.
   Доступность плагина в окружении не равна его использованию/установке у пользователя.
3. Версии: `vMAJOR.MINOR.PATCH-candidate.N`; SHA commit/tree, дата наблюдения,
   источник, тестовое свидетельство, screenshot status. Название не означает release.
4. Создание checkpoint требует чистых tracked файлов; игнорирует только служебный
   .terminal-runner.lock, созданный существующим runner. Остальные untracked — отказ.
5. Восстановление создаёт новый worktree. Текущая папка/незакоммиченные изменения и
   каноническая история сохраняются. В восстановленной папке есть указатель на
   АКТУАЛЬНУЮ память; старая память из commit не является текущим источником истории.
6. Screenshot: фактический PNG/JPEG, digest/размеры, заявленный commit и источник
   захвата. Ручная привязка имеет reported provenance. Без снимка — NOT_CAPTURED;
   нельзя генерировать изображение интерфейса и выдавать его за скриншот.
7. Подключение этого ChatGPT-чата пока NOT_CONNECTED: в доступном browser нет входа.
   Локальный stdio MCP и импорт18 сообщений — отдельные проверенные сценарии.

## Проверки

Реальные18 сообщений: точное сравнение и повторный импорт; отображение imports не
означает live connection. Временный Git: checkpoint, отказ dirty/duplicate/path
collision, восстановление старого кода после новой версии с сохранением dirty work.
HTTP/security текущей панели, сводки без ложного accepted, missing/tampered screenshot,
синтаксис JS и поведение NProgress при polling. Browser screenshot и чаты аккаунта
проверяются только при фактическом доступе. Внешний A6 остаётся открытым.

## Исправления независимой проверки

Воспроизведены и устранены коллизии имён квитанций (включая разный регистр Windows)
и исполнение Git smudge-фильтра при checkout. Теперь операции игнорируют global/system
Git config, отключают hooks/fsmonitor/submodule recursion и отказывают при локальных
filter drivers. Коллизии проверяются до worktree. Изображения читаются ограниченно,
только как обычные файлы; ошибка записи checkpoint убирает только собственный
orphan ref, если версия ещё не попала в журнал. При уже записанной версии ref
сохраняется, проекции восстанавливаются штатным checkpoint/doctor.

## Команды и границы

```sh
python terminal_versions.py --root MEMORY --project-id PROJECT create --repo CHECKOUT --label v0.8.1-candidate.1 --summary "Описание результата" --evidence EXISTING_EVENT_ID
python terminal_versions.py --root MEMORY --project-id PROJECT list
python terminal_versions.py --root MEMORY --project-id PROJECT restore --label v0.8.1-candidate.1 --destination NEW_FOLDER
python terminal_versions.py --root MEMORY --project-id PROJECT screenshot --label v0.8.1-candidate.1 --image ACTUAL_CAPTURE.png --source "Источник реального захвата" --commit FULL_SHA
```

Замените обозначения явно выбранными путями/ID. Checkpoint фиксирует committed
код, не untracked файлы, окружение, базы данных, submodules или LFS binaries.
Restore ничего не устанавливает и не запускает. Локальный refs/fix-checkpoints
не является опубликованным release и сам не отправляется на GitHub. Для переноса
на другой компьютер нужны Git-объекты и refs (отдельный backup/bundle/push).
Сохранённый SHA локального commit не следует заменять SHA опубликованного commit
с тем же деревом. Данная функция — безопасный возврат кода в исходном checkout;
независимый off-device backup остаётся отдельным этапом.

Кнопки отката в HTTP нет: панель только читает. Восстановленная папка содержит
RESTORE_HANDOFF.md с путём к текущей памяти. Исторические файлы журнала внутри
старого commit остаются историческими; не используйте их как актуальную память.
Поле screenshot_status=NOT_CAPTURED блокирует заявление визуальной приёмки.

## Более позднее наблюдение аккаунта

Защищённый вход выполнен; выборки двух реальных чатов испытаны. Исторический пункт7
о logged-out больше не описывает последнее чтение. Непрерывной подписки всё ещё нет.
Реальный screenshot HTML preview candidate.1 получен. См. AUTHENTICATED_CHAT_TRIAL.md.
