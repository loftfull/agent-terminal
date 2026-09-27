# Студия: готовая анимация и наблюдаемые запуски

Встроен loadingio/loading.css, MIT, revision ad7bfc0e864b319b9bd8a3478422f9be2a2732bf.
Исходные CSS и лицензия сохранены. ld-spin и ld-breath работают только при fetch
через существующий receiving lifecycle; в snapshot стоят. ld-float используется
однократно для появления иконок. Pause и prefers-reduced-motion останавливают
движение. Широкие панели без тяжёлых теней; объём добавлен только плиткам иконок.

Три последних run records показываются с сообщённой моделью либо «не указана».
Запись running не трактуется как heartbeat. Состояние связи с агентами явно
неподтверждённое. Карточка раскрывает event_id, argv, session и exit code.
Не добавлены ни провайдеры моделей, ни фиктивные агенты. Успех команды не означает
приёмку проекта. CSS встроен в HTML: без CDN и новых сетевых разрешений.

Проверено: пять существующих dashboard tests PASS, JS syntax checks PASS.
Browser navigation к localhost вернула ERR_BLOCKED_BY_CLIENT: визуальная
приёмка и браузерная проверка reduced-motion не выполнены. Скриншот не создан.
Предпросмотр docs/previews/Agent-Terminal-Studio.html — автономный снимок, не live.
