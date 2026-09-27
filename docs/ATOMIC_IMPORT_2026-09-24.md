# Структурная проверка и атомарный импорт

Продолжение audit repairs. Выбрана ограниченная доработка существующего JSONL:
используются готовые Portalocker3.2.0 и уже имеющийся atomic_write_text (fsync,
os.replace). GitHub сравнение transactional eventsourcing и стоимость миграции
описаны в BLIND_AUDIT; миграция canonical backend для этой правки не требуется.

runtime_journal.append_mutation_batch применяет всю группу на копии replay-state,
проверяет итог audit_state, формирует цепочку записей и под writer lock атомарно
заменяет текущий segment его старым содержимым плюс новая группа. Forward source
reference внутри группы допустима, dangling reference в итоговом состоянии — отказ.
append_mutation_set использует ту же проверку для одиночной записи.
Импорт собирает source/event/session metadata в одну группу; checkpoint-проекции
обновляются после публикации и при повторном запуске восстанавливаются из журнала.

Гарантия: cooperative writers на локальной FS; отказ до rename не публикует часть
batch. Потеря подтверждения после rename означает неопределённый ответ, а не rollback:
повторный импорт сверяет ID/revisions и не добавляет дубли. Не повторять произвольную
неидемпотентную мутацию вслепую. Полная durability при power loss/сетевой FS не испытана.

Независимый review воспроизвёл numeric overflow9999/10000 и риск быстрого достижения
vault MAX_FILES1024 при segment-per-write. Исправлено: numeric sorting и повторное
использование active segment. Vault limit остаётся: число явно закрытых сегментов
всё равно ограничено. Атомарная замена переписывает active segment: стоимость растёт
с его размером, производительность на больших журналах не измерена.

Проверки:213local testsPASS, включая4batch cases (dangling/forward references,
ошибка доrename, ошибка послеpublish, numeric rollover/reuse). Отдельный аудитор
проверил8concurrent writes и retry after lost acknowledgement. После правки prefix
читается bytes.decode для сохранения исходных переносов строк.
Реальные ранее сохранённые выборки28+15: exact preservationPASS, повтор0.
Это проверка сохранённого корпуса, не новый доступ к аккаунту и не полнота чатов.

CI прежних B1–B5 исправлений: run35989946526 success (Linux/Windows workflow).
CI новых изменений не включён в эти результаты.

Границы: низкоуровневые append_mutation/bootstrap_journal_from_state сохраняют
прежний последовательный bootstrap-контракт и не объявлены атомарными/полностью
структурно валидирующими. Runtime lifecycle/runner используют проверенные одиночные
записи, но вся их бизнес-операция не стала одной транзакцией. Следующий этап:
crash-safe bootstrap и перевод остальных связанных writer workflows на batch.
