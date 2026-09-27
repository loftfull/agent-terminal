# GitHub analogue audit — Project History Agent

Последняя полная перепроверка: **2026-09-17**.

Актуальный сравнительный аудит сохранён в [`ANALOG_AUDIT_2026-09-17.md`](./ANALOG_AUDIT_2026-09-17.md).

Ключевой вывод после расширения выборки до CSM/AgentBook, Kairo, Qarinah, Agent Memory System, PROJECTMEM, Shinobi, DSM, Memoir, ChatMem, Basic Memory, handoff, claude-mem, agent-work-mem, Prism Coder и casefile:

- FIX пока **не самый зрелый готовый продукт**; по ширине реализации впереди прежде всего CSM/AgentBook и Kairo.
- Среди изученных аналогов FIX имеет **наиболее комплексный архитектурный план именно для evidence-first project-history reconstruction**: chat lineage + repo/path/branch/SHA provenance + plan→fact→version + development lines/dead ends + visual evidence + deterministic hash-chained replay + cross-host lifecycle.
- v0.8 roadmap должен заимствовать сильнейшие идеи конкурентов, не превращая FIX в универсальную memory-platform или agent orchestrator.

Следующий план: [`../docs/ROADMAP_V08.md`](../docs/ROADMAP_V08.md).
