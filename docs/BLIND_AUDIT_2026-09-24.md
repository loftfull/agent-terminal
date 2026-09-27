# Независимый аудит FIX — 2026-09-24

Проверенная ревизия: `a8287d64258a6836e6f3c59fa5b637d54ae60c13`.
Рабочая копия: `/workspace/scratch/c911ac0d5396/repos/FIX`.
Аудитор: отдельный агент текущей среды, которому не передали описание проекта.
Это независимое обследование кода, **не внешний A6 другой моделью** и не проверка
достоверности всех исходных частных разговоров.

## Результат

Проект содержит работающий локальный историк, а не только набор инструкций:
импорт явно выбранных сообщений, версионные наблюдения, воспроизводимый журнал,
структурный аудит и read-only MCP доступны в реализации. Однако доверять ему как
безусловно безопасной границе записи пока нельзя: воспроизведены пять дефектов,
включая смешение идентичности проектов и запись мутации, после которой replay
перестаёт работать. Существующие 204 теста проходят, поэтому они не покрывают эти
границы. Причина ранее описанных потерь истории этим аудитом **не установлена**.

Исполняемый код не изменён. Все вредоносные/ошибочные входы ниже — синтетические,
испытаны в TemporaryDirectory; канонический журнал аудитор не модифицировал.
Из исходного дерева при старте замечен только untracked `.terminal-runner.lock`.

## Метод и границы независимости

AGENTS.md требует прочитать PROJECT_HISTORY_AGENT.md, PROJECT_MEMORY.md, TASKS.md,
TERMINAL_PLAN и CURRENT_CHAT_AUDIT. Они прочитаны как инструкции/заявления. Поэтому
«слепой» означает отсутствие вводного описания от автора, а не буквальную изоляцию
от документации. Предыдущие аудитные выводы не использованы как доказательство
обнаруженных дефектов: каждому соответствует собственное чтение кода и fixture.

Критерии: восстановить реальные сценарии, проверить границы записи и передачи
контекста, прогнать штатные проверки, сравнить решения именно для найденных
ограничений. Остановка: после воспроизведения существенных проблем и конкретного
плана; без переписывания системы, импорта частных архивов, установки hooks или
публикации. Полный security audit, Windows execution и нагрузочный benchmark
не выполнены. Реальные секреты и сообщения в отчёт не включены.

## Что удалось восстановить без вводного контекста

| Сценарий пользователя | Реализация и фактическая граница |
|---|---|
| Передать историю проекта новой сессии | project_history_journal.py → replay → PROJECT_MEMORY.json/md; MCP HistoryReader проверяет hash-chain и структурный аудит. Это чтение зарегистрированного корпуса, не всех чатов пользователя |
| Импортировать выбранный разговор | fix.py attach → ChatGPTExportHistoryAdapter / normalized input → evidence_import.import_sessions → terminal_chat_check. Нужны файл, project ID и session ID; непрерывной загрузки нет |
| Не спутать сообщение с доказанным действием | evidence_import сохраняет presence observed, content reported; terminal_control переводит done в review и accepted=False |
| Начать/закончить работу в AI-host | native_hook_runner → normalize_hook_event → host_lifecycle_bridge → project_history_hooks; hooks требуют установки; ошибки возвращают continue=True с предупреждением |
| Запустить выбранную локальную проверку | terminal_runner: subprocess argv без shell, timeout, выход/вывод/receipt. Сам модуль явно не является sandbox; прав процесса не снижает |
| Увидеть состояние | terminal_dashboard: localhost HTTP, проверка Host/Origin, read-only API, статический HTML. Данные — проекция журнала |
| Обнаружить rollback / восстановить архив | terminal_vault: внешний относительно root SQLite witness через eventsourcing, capture на выбранных границах. Не резервирует незахваченный хвост и не гарантирует независимость от сбоя того же компьютера |
| История локального Git / снимки | history_watch — работающий процесс наблюдения; terminal_visual — пиксельное сравнение предоставленных изображений. Это не автоматический смысловой анализ истории или дизайна |

Архитектура: файловые/ad-hoc host adapters → явные команды импорта/lifecycle →
JSONL base + отсортированные segments → replay/domain state → Markdown, CLI,
MCP, dashboard. Vault — отдельный свидетель, не первичное хранилище.
Транзакции на уровне бизнес-операции нет: источник, событие и checkpoint записываются
отдельными вызовами. В проекте 5 634 строки Python верхнего уровня на момент чтения;
это не метрика качества и не оценка всего репозитория.

## Выполненные проверки

Рабочий каталог для команд — указанный checkout. Python:
`/workspace/scratch/c911ac0d5396/mcp-venv/bin/python`.

```bash
/workspace/scratch/c911ac0d5396/mcp-venv/bin/python project_history_doctor.py .
/workspace/scratch/c911ac0d5396/mcp-venv/bin/python -m unittest discover -s tests -q
```

Наблюдаемые результаты: doctor **WARN**, 222 записи; integrity, replay,
snapshot match, structural audit, atomic persistence и его secret probe PASS.
WARN: отсутствуют доступные Claude/Codex истории, ChatGPT export не настроен,
hook templates отсутствуют, Playwright не установлен в использованном Python.
204 теста за 9.619 s, OK. Это один локальный запуск, не benchmark и не Windows CI.

Совместный минимальный reproducer: `docs/BLIND_AUDIT_REPRO_2026-09-24.py`.
Команда: `/workspace/scratch/c911ac0d5396/mcp-venv/bin/python docs/BLIND_AUDIT_REPRO_2026-09-24.py`.
Результат отдельного запуска: B1, B2, B3, B4, B5 — REPRODUCED; exit 0.
Он создаёт только временные fixture roots, не пишет каноническую память.
Exit 0 означает воспроизведение дефектов этой ревизии, а не их исправление.
Doctor PASS для redaction означает прохождение одного probe, а не полноту маскирования.

## Воспроизведённые дефекты

Severity: High — нарушение целостности/изоляции или сохранение credential input;
Medium — потеря обязательной информации на отдельном пути. Вероятность и охват
указаны отдельно, а не подменяют воспроизведённый эффект.

### B1 — High: ProjectLock можно украсть у живого владельца

Место: `project_history_journal.py:108–143`, особенно `age > stale_after` и два
`unlink`. Lock живёт как pathname, по умолчанию становится «устаревшим» через
300 секунд без heartbeat/проверки процесса. Второй владелец удаляет его и создаёт
новый. Выход первого затем удаляет lock второго. Это нарушает взаимное исключение,
на котором держатся append/checkpoint/import. Тест ускоряет возраст через utime;
он доказывает механизм, **не доказывает**, что реальная операция уже длилась 300 s
или что это причина прежнего rollback. В runner отдельный kernel lock уже реализован.

```python
import os, time, tempfile
from pathlib import Path
from project_history_journal import ProjectLock
with tempfile.TemporaryDirectory() as d:
    p = Path(d)/'lock'
    a = ProjectLock(p); a.__enter__()
    os.utime(p, (time.time()-301,)*2)
    b = ProjectLock(p, timeout=.01); b.__enter__()
    print(a.acquired, b.acquired)  # True True
    a.__exit__(None,None,None)
    print(not p.exists())         # True: удалён lock второго
    b.__exit__(None,None,None)
```

Исправление: единый OS-backed lock с сохранением inode на всех writer paths;
не переносить age-based steal в новый backend. Приёмка: два процесса, возраст
>300 s/имитация времени, kill владельца, Windows+Linux — максимум один writer,
после завершения/crash следующий получает lock, чужой lock не удаляется.

### B2 — High: публичная запись принимает необрабатываемую мутацию

Место: `runtime_journal.py:80–130`; `project_history_journal.py:192–229`;
`project_history_hooks.py:101–104`; `_patch_entity` около строки 259.
Проверяются op и целостность существующего журнала, но не применимость нового
payload к текущему состоянию. source.patch несуществующей сущности записывается
успешно; verify_journal_set говорит ok, replay падает. Через record_mutation
исключение придёт уже после необратимого append. Последующей patch недостаточно:
replay остановится раньше её. Это API-level дефект для ошибочного вызывающего
кода/ручной мутации; не заявляется удалённая эксплуатация dashboard.

```python
import tempfile
from pathlib import Path
from project_history_journal import append_mutation, verify_journal_set, replay_journal_set
from runtime_journal import append_mutation_set
with tempfile.TemporaryDirectory() as d:
    p=Path(d)
    append_mutation(p/'PROJECT_HISTORY.events.jsonl','project.patch',
                    {'project_id':'fixture','name':'fixture'})
    append_mutation_set(p,'source.patch',{'source_id':'missing','title':'x'})
    print(verify_journal_set(p)['ok'])  # True
    replay_journal_set(p)  # ValueError: cannot patch missing sources entity missing
```

Исправление: preflight применения/валидации под тем же writer lock до append;
batch source+event с определённой crash semantics. Обновлять схему вместе с
валидацией. Приёмка: rejected mutation не меняет ни байта журнала, replay после
отказа работает; прерывание batch даёт либо старое, либо целиком новое состояние.

### B3 — High: lifecycle смешивает проекты при неверном project_id

Место: `project_history_hooks.py:76–99`; доступно через
`host_lifecycle_bridge.py:34–59`. Существующий журнал читается, но identity из
аргумента не сравнивается с state.project.project_id. Для root проекта A можно
начать сессию B: B появляется в chats, current_chat_id становится chat-b, тогда
как project остаётся A. MCP и import такую проверку имеют; lifecycle — нет.

```python
from tempfile import TemporaryDirectory
from history_adapters import InMemoryHistoryAdapter
from project_history_hooks import session_start
with TemporaryDirectory() as d:
    a=InMemoryHistoryAdapter([])
    session_start(d,{'chat_id':'chat-a','project_id':'A'},a,
                  project_id='A',name='A',goal='A')
    r=session_start(d,{'chat_id':'chat-b','project_id':'B'},a,
                    project_id='B',name='B',goal='B')
    print(r['state']['project']['project_id'])             # A
    print(r['state']['handoff']['current_chat_id'])         # chat-b
    print([(c['chat_id'],c.get('project_id')) for c in r['state']['chats']])
    # [('chat-a','A'), ('chat-b','B')]
```

Исправление: единая проверка identity на writer boundary, включая current и
миграцию snapshot; при несовпадении отказ до любых записей. Это небольшой FIX-
специфичный инвариант, новая orchestration библиотека его сама не обеспечит.

### B4 — High: Cookie header в свободном тексте сохраняется открытым

Место: `project_history_journal.py:49–86`. SECRET_KEY_RE включает cookie для
словарей/URL query, но free-text assignment regex строки 82 не включает cookie.
Текст `Cookie: session=synthetic-placeholder` проходит неизменным. Этот тип текста
может попасть из экспорта или stdout runner; это стандартный credential-bearing
header, а не требование угадывать произвольный секрет в прозе.

```python
from project_history_journal import redact_secrets
x='Cookie: session=synthetic-placeholder'
print(redact_secrets(x)==x)  # True
```

Исправление: явно обрабатывать Cookie/Set-Cookie целиком (включая несколько пар),
проверить multiline и вложенный message.text до persistence. Уже сохранённый
секрет нельзя исправить только новой patch: понадобится отдельный контролируемый
процесс удаления/ротации с сохранением аудита. Реального утёкшего cookie здесь не
искали и наличие утечки не утверждается. Не обещать универсальное распознавание.

### B5 — Medium: native handoff обрезает обязательные ограничения

Место: `native_hook_runner.py:57–65`, `_handoff_context(max_chars=3500)`;
`project_history_agent.py:454–460` намеренно помещает constraints до раздела 1.
Весь этот блок всё равно режется до 3500 символов, без сохранения хвостовых
ограничений. MCP context содержит полный список, но native hook — отдельный путь.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from project_history_agent import empty_state, render_markdown
from native_hook_runner import _handoff_context
with TemporaryDirectory() as d:
    s=empty_state('fixture','fixture','fixture')
    s['project']['constraints']=['A'*4000,'CRITICAL_LAST_CONSTRAINT']
    p=Path(d); (p/'PROJECT_MEMORY.md').write_text(render_markdown(s))
    r=_handoff_context(p)
    print('CRITICAL_LAST_CONSTRAINT' in r, len(r))  # False 3581
```

Указание прочитать файл полезно, но не исполняет требование передать все mandatory
constraints в каждой handoff-проекции. Приёмка: большой паспорт/next_step и длинный
список constraints; все ограничения переданы либо выдаётся явный неполный handoff
с обязательным отдельным retrieval. Не обрезать правило посреди строки молча.

## Риски и отсутствующие возможности — не смешивать с дефектами выше

- `history_adapters.py:179–204`: bounded roots не означают bounded workload.
  rglob читает все JSONL, _sessions материализует весь корпус, limit применяется
  после чтения. Один повреждённый JSONL вызывает ValueError и обрывает поиск.
  Это видно по коду; large-corpus latency и partial-write сценарий не измерены.
- `project_history_mcp.py:92–106`: поиск буквальный по JSON события. Текст,
  сохранённый только внутри source, может не совпасть; семантического поиска нет.
  Endpoint честно ограничивает coverage событиями. Это ограничение, не ложная
  гарантия полноты и не основание автоматически добавлять embeddings.
- `terminal_context.py:23`: L0 прямо не имеет token-size bound; L1/L2 имеют
  пагинацию по числу событий, не по размеру текста. Большое сообщение может
  заполнить контекст. Нужны измерения на разрешённом репрезентативном корпусе.
- `terminal_control.py:121`: acceptance_gate=not_implemented. done → review,
  accepted=False — правильная осторожность, но конечная приёмка задачи отсутствует.
- Hash-chain без независимого witness не обнаруживает корректно усечённый хвост;
  vault опционален и защищает только captured prefix. Нельзя назвать его резервной
  копией другого устройства только из-за пути вне root.
- Внутренний hash и passage of tests не доказывают истинность reported claims,
  полноту источников, реальную установку host integration или смысловой анализ.

## GitHub-first: альтернативы именно найденным ограничениям

Поиск 2026-09-24: `github portalocker portalocker license lock Python`,
`github pyeventsourcing eventsourcing SQLite recorder transaction license`,
`github gitleaks gitleaks MIT detect secrets`. Первичные исходники и LICENSE
получены через GitHub connector; попытки raw web fetch были недоступны.
Ни один upstream script не запускался, библиотека в ходе аудита не установлена.
Теги разрешены через GitHub commits API в точные SHA ниже. Это исследование,
не внедрение и не доказательство лучшей производительности.

| Проблема / вариант | Проверенная ревизия, код, лицензия | Пригодность и конкретное преимущество | Стоимость, ограничения, acceptance |
|---|---|---|---|
| B1: заменить только ProjectLock на Portalocker | [wolph/portalocker v3.2.0](https://github.com/wolph/portalocker/tree/7415a5d20aa64ac347b0c734915ddbe49ce844f3), `portalocker/portalocker.py`: PosixLocker использует fcntl.flock, Windows — msvcrt/Win32; LICENSE BSD-3-Clause прочитан | Убирает именно age-based pathname ownership; готовые межплатформенные primitives вместо собственного stale-lock алгоритма | Низкая/средняя: заменить ВСЕ writer locks, сохранить inode, выбрать Windows зависимости, сохранить notice. Advisory locks не блокируют некооперативных писателей; сетевые FS требуют отдельных испытаний. Acceptance B1, не обещание ускорения |
| B1/B2 и отдельные source/event записи: transactional recorder | [pyeventsourcing/eventsourcing v9.5.5](https://github.com/pyeventsourcing/eventsourcing/tree/575d42c10a821828639b90178ed56703abe9c9f1), `eventsourcing/sqlite.py`: SQLiteAggregateRecorder.insert_events входит в transaction(commit=True), executemany, primary key (originator_id, originator_version); LICENSE BSD-3-Clause прочитан | Готовая атомарность batch и конфликт версий на DB уровне; библиотека уже используется для witness в FIX, но не для canonical journal | Высокая для замены canonical JSONL: миграция, совместимость, export/replay, backup/restore, source schema. SQL не проверит FIX entity semantics автоматически, B2 preflight всё равно нужен. Не менять backend до доказанной необходимости; сначала малая правка инвариантов. Приёмка: crash/concurrent writes, идентичный replay/export, старые SHA/history сохранены |
| B4: Gitleaks как дополнительный scanner / донор ограниченных правил | [gitleaks/gitleaks v8.24.3](https://github.com/gitleaks/gitleaks/tree/107a41827bb6698dbbff756b2300537774a1d84c), `config/gitleaks.toml` прочитан, включая generic-api-key/entropy/allowlists; LICENSE MIT прочитан | Готовый каталог provider-specific patterns и policy для обнаружения до публикации; полезен как отдельный gate или лицензированная адаптация точных правил | Средняя: Go binary/процесс, формат результатов и безопасное логирование; FP/FN, tuning. Generic rule не гарантирует обнаружение cookie и не является redaction. **Не решает B4 сам по себе**: нужен явный header scrubber + regression fixtures. Acceptance: отсутствие синтетических credentials в сохранённых bytes, тест ordinary text и отчет scanner без secret values |
| B3/B5: сохранить нынешний core, усилить границы | Сопоставление с проверенными выше компонентами: ни lock, ни event recorder, ни scanner не определяют project identity или список обязательных constraints | Минимальное исправление domain инвариантов сохраняет evidence schema и интерфейсы | Низкая/средняя; отдельные тесты всех entrypoints. Новая агентная платформа увеличит миграцию, не доказывая исправления этих ошибок. Проверяемый отказ cross-project и полный handoff — критерии выбора |

Прочитанные файлы:
[Portalocker code](https://github.com/wolph/portalocker/blob/v3.2.0/portalocker/portalocker.py),
[Portalocker LICENSE](https://github.com/wolph/portalocker/blob/v3.2.0/LICENSE),
[eventsourcing code](https://github.com/pyeventsourcing/eventsourcing/blob/v9.5.5/eventsourcing/sqlite.py),
[eventsourcing LICENSE](https://github.com/pyeventsourcing/eventsourcing/blob/v9.5.5/LICENSE),
[Gitleaks rules](https://github.com/gitleaks/gitleaks/blob/v8.24.3/config/gitleaks.toml),
[Gitleaks LICENSE](https://github.com/gitleaks/gitleaks/blob/v8.24.3/LICENSE).
Полный сравнительный benchmark, свежесть всех последних релизов, стоимость
в человеко-днях и гарантия поддержки не установлены; low/medium/high выше —
инженерная оценка площади изменений, а не измерение скорости.

## Приоритетный план

1. **P0, целостность записи:** B2 preflight и B3 identity guard до append.
   Отрицательные тесты проверяют неизменность байтов и работоспособный replay.
   Не заменять JSONL целиком ради одной валидации.
2. **P0, блокировки:** B1 единый kernel-lock backend, regression с живым старым
   владельцем, concurrent append, аварийный exit, Windows/Linux. Причину исторических
   rollback расследовать отдельно; не считать найденный механизм её доказательством.
3. **P0, credentials:** B4 header scrubber и corpus синтетических secret fixtures.
   Scanner добавить как второй барьер с ограниченными claims, не вместо redaction.
4. **P1, перенос ограничений:** B5 полная передача constraints на native пути,
   явные признаки неполноты/страницы; проверить различие MCP/native/Markdown.
5. **P1, отказоустойчивость корпуса:** один broken/дописываемый JSONL не должен
   скрывать здоровые источники без диагностического coverage результата. Измерить
   загрузку/память/размер context на 100/1 000/10 000 синтетических сообщениях.
   Индекс вводить только после baseline; размер события ограничивать отдельно.
6. **P2, приёмка реального сценария:** выбранный исходный экспорт → import →
   повторный import → новая MCP/native сессия → решение с source IDs. Отдельный
   reviewer проверяет raw evidence, неизвестные данные остаются неизвестными.
   Provider/UX расширения не являются завершением этого критерия.

## Что осталось неизвестным

Первоначальный полный замысел автора, весь корпус требований и все реальные чаты
не восстанавливаются из кода. Не проверены полнота экспортов, точность всех
исторических asserted facts, пользовательская Windows-среда, установка hooks,
доступ к аккаунтам, UI в настоящем браузере, upstream production пригодность после
интеграции. Каноническая source-backed история может быть точной в пределах
зарегистрированного корпуса и одновременно неполной. Для этих вопросов нужен
отдельный источник/исполнительное испытание; доктор и этот аудит их не заменяют.
