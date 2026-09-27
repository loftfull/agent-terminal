# Competitive architecture audit — 2026-09-17

Scope: current public analogues for Project History Agent / `loftfull/FIX`.

This audit separates two questions:
1. Which implementation is most mature today?
2. Which architecture is strongest for the narrower FIX target: evidence-first reconstruction of project history across chats, agents, repositories, branches, versions and environments?

## Current FIX strengths

The v0.7 line already combines:
- evidence-gated `new / continuation / unknown` chat lineage;
- parent-chain reconstruction instead of topic-similarity merging;
- repo/path/branch/SHA provenance with historical-vs-current distinction;
- plan -> fact -> version history;
- development lines, forks/supersession and dead-end semantics;
- append-only SHA-256 chained deterministic replay;
- Git-native ordered journal segments;
- redaction before persistence;
- JSON snapshot + human/AI Markdown projection;
- visual evidence provenance rules;
- Claude Code, Codex and explicit ChatGPT-export adapters;
- bounded host-history discovery;
- stable-identity ranking that is explicitly not lineage authority;
- native SessionStart / PreCompact / SessionEnd lifecycle integration;
- structural auditor, doctor and repository-owned CI.

## Strongest re-checked analogues

### CSM / AgentBook — strongest all-round implementation
https://github.com/NovasPlace/CSM

Advantages over FIX today:
- much broader implemented runtime and retrieval surface;
- vector/text/entity/relationship retrieval;
- merge/supersede/archive governance;
- causal stitching, context-pressure management, backup/restore;
- native Claude/Codex packaging;
- README reports >1,500 automated tests.

FIX differentiator: stronger explicit project-origin/chat-lineage model, location/SHA history, plan-to-fact versions and visual provenance.

### Kairo — strongest continuity/control-plane analogue
https://github.com/sandeepbollavaram/Kairo

Advantages:
- repo intelligence and risk-ranked onboarding;
- continuation briefs and token-budgeted Atlas Capsule;
- large MCP surface, snapshots, coordination and telemetry.

FIX differentiator: evidence-gated chat lineage, tamper-evident segmented journal and richer multi-location/version history.

### Qarinah — strongest evidence-linked context engine
https://github.com/AjnasNB/qarinah

Advantages:
- versioned append-only hash-chained ledger;
- cited/evidence-aware context packs;
- rebuildable graph/index/Markdown/OKF exports;
- polished project-local Claude/Codex/Cursor integration.

FIX differentiator: explicit first-run parent-chain reconstruction plus locations, development lines, plan/fact/version and visual history.

### Agent Memory System — strongest evidence/promotion pipeline
https://github.com/rrrrrredy/agent-memory-system

Advantages:
- content-addressed raw evidence;
- evidence -> episode -> candidate -> validation -> promotion/supersede/revoke lifecycle;
- redacted portable Git projection;
- replay-verifiable receipts and fail-closed compatibility.

Lesson for FIX: formalize evidence promotion and review rather than relying only on `evidence_status`.

### PROJECTMEM — strongest failure-first governance
https://github.com/riponcm/projectmem
Paper: arXiv:2606.12329

Advantages:
- typed issues/attempts/fixes/decisions;
- deterministic event-sourced projections;
- pre-action/pre-commit warning before repeating a failed approach;
- published real-project evaluation.

Lesson: add deterministic failure/dead-end guard as a P1 feature.

### Shinobi — strongest dead-end/task-spine automation
https://github.com/numbererikson/shinobi

Advantages:
- searches previous dead ends before work;
- persistent project/subtask spine;
- approvals, remote MCP and worktree swarm.

Do not copy the orchestration/swarm scope into FIX core.

### Daryl / DSM — strongest narrow cryptographic audit layer
https://github.com/daryl-labs-ai/daryl

Advantages: hash-chain, optional Ed25519 authorship, sealing and attestations.
Lesson: optional segment sealing/signatures are useful, but should not become a mandatory local dependency.

## Other relevant systems

- Memoir — portable project handoffs, commit-aware resume, encrypted sync.
- ChatMem — broad local history ingestion across multiple coding agents.
- Basic Memory — mature MCP/Markdown knowledge layer, semantic/hybrid retrieval and host-native packages.
- handoff — excellent low-friction hooks, append-only JSONL, locks, redaction and doctor.
- claude-mem — automatic capture/injection, progressive disclosure and citations.
- agent-work-mem — extremely portable vendor-neutral Markdown protocol and hot/warm/cold context tiers.
- Prism Coder — drift detection, context modes and screenshot evidence.
- casefile — epistemic grades and the important rule that model agreement is not verification.

## Conclusion

### Product maturity today

FIX is **not yet the most mature ready-to-install product** in this category. CSM/AgentBook and Kairo are broader implementations today; PROJECTMEM and Qarinah are more polished in specific workflows.

Claiming otherwise would not be evidence-based.

### Architecture for FIX's target problem

For the specific problem FIX is solving — reconstructing and preserving the actual development history of a project across chats, models, repositories, local folders, branches, versions, dead ends, plans, deployments and visual states — this audit found no analogue combining all of the following in one evidence model:

1. evidence-gated chat lineage;
2. parent-chain reconstruction toward origin;
3. repo/path/branch/SHA/deployment provenance;
4. plan -> fact -> version ledger;
5. branches/forks/supersession/dead ends;
6. visual provenance;
7. hash-chained deterministic replay;
8. immutable Git-native journal segments;
9. cross-host discovery + stable-identity ranking that cannot itself assert lineage;
10. host-native lifecycle checkpoints;
11. structural auditor + independent external-AI acceptance gate.

**Defensible conclusion:** among the studied analogues, FIX has the most comprehensive architectural plan for evidence-first project-history reconstruction and cross-agent continuation. It is not yet the most mature implementation.

## Roadmap consequences

The plan should now adopt:
- PROJECTMEM/Shinobi: failure-first pre-action guard;
- Agent Memory System/casefile: evidence candidate -> review -> verify/reject -> supersede/revoke;
- CSM/Kairo/Qarinah: token-budgeted cited context compiler;
- Kairo: repo intelligence + risk-ranked read-first plan;
- DSM: optional signed/sealed segment manifests;
- Qarinah/Memoir: portable evidence/handoff export;
- Basic Memory/ChatMem: optional semantic/hybrid index only as rebuildable derived cache;
- empirical benchmark corpus before any v1.0 claim.

## Strategic boundary

Do not turn FIX into a mandatory vector DB, daemon, cloud service, swarm runtime or second Git. Its competitive advantage is historical truth, provenance and continuation, not feature count.
