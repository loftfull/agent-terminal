# Project History Agent — v0.8+ leading architecture roadmap

Date: 2026-09-17

## North star

Build the most reliable **project historian and cross-agent continuation layer**, not a generic memory database or agent orchestrator.

Evidence remains the source of truth. Retrieval, summaries, graphs, embeddings and UI are derived and rebuildable.

## P0 — acceptance and integrity

1. Complete A6 independent external-model audit against raw sources, segmented journal, deterministic snapshot, current-chat bundle and visual evidence.
2. Persist the A6 report as an immutable cited audit artifact.
3. Add an acceptance manifest with exact code SHA, journal tail hash, schema versions and audit result.

Exit gate: no fully-accepted / production-ready claim before A6 PASS.

## P1 — failure-first Memory-as-Governance

Adopt the strongest PROJECTMEM/Shinobi idea without turning FIX into an orchestrator.

Add typed `attempt`, `failure`, `fix`, `decision`, `constraint` events and a pre-action query API returning:
- `known_failed`;
- `superseded`;
- `unverified`;
- `no_evidence`.

Default behavior is warning, not blocking. Semantic similarity may retrieve candidates, but only source-backed typed evidence can produce a strong warning.

## P1 — evidence promotion lifecycle

Inspired by Agent Memory System and casefile:

`raw evidence -> candidate claim -> reviewed -> verified/rejected -> superseded/revoked`

Rules:
- every promotion cites source IDs;
- model agreement alone is never verification;
- corrections append records instead of rewriting history;
- contradictions remain first-class until resolved.

## P1 — token-budgeted cited context compiler

Inspired by CSM, Kairo and Qarinah.

Produce three projections:
- `tiny` — session bootstrap;
- `normal` — handoff;
- `deep` — audit/recovery.

Priority order:
1. current verified constraints;
2. current branch/version/location;
3. unresolved blockers;
4. recent verified changes;
5. read-first files/artifacts;
6. older history on demand.

The compiler is a projection, never source of truth.

## P1 — repository intelligence / read-first plan

Inspired by Kairo.

Capture repository fingerprint, frameworks/languages/entry points, changed/high-risk files, branch/worktree relations, read-first files and a conditional safe-to-skip list.

Repo intelligence may guide orientation but must never silently override explicit historical evidence.

## P2 — cryptographic archive sealing

Inspired by DSM.

Extend the existing SHA-256 segmented journal with optional:
- segment manifest;
- byte length + digest;
- previous-segment tail hash;
- optional Ed25519 signature;
- archive/seal event.

Signatures stay optional; normal local verification must work without them.

## P2 — portable interchange bundle

Inspired by Qarinah/Memoir.

Deterministic export should contain:
- Project Passport;
- chat lineage;
- locations;
- versions;
- constraints;
- cited decisions;
- failures/dead ends;
- read-first plan;
- journal/audit references;
- visual evidence index.

Prefer neutral JSON/Markdown; an OKF-compatible adapter may be optional.

## P2 — derived semantic/hybrid index

Inspired by CSM, Basic Memory, ChatMem and agent-history.

Optional index over summaries, decisions, failures, filenames, artifact metadata and policy-approved transcript excerpts.

Hard rules:
- index is deletable/rebuildable;
- index never creates lineage;
- embeddings never promote evidence status;
- stable identifiers outrank semantic similarity.

## P2 — visual evidence v2

Add perceptual hash, viewport/device, URL/deployment, capture time, latest/intermediate state and optional visual-diff references.

Exact version/SHA is linked only when proven; date proximity is never enough.

## P3 — multi-writer/remote sync only if demanded

Core remains local-first and single-writer-safe. Shared storage, leases and private remote synchronization are optional later features, not core dependencies.

## P3 — project-history UI

Only after the evidence model stabilizes. Useful surfaces:
- origin -> continuation chat tree;
- development-line/fork graph;
- plan-vs-implemented timeline;
- location/SHA timeline;
- failure/dead-end browser;
- screenshots by version;
- contradictions/unresolved evidence;
- acceptance/audit receipts.

## Benchmark program before v1.0

Frozen evaluation cases must include:
- direct continuation;
- unrelated same-topic chat;
- renamed repo;
- old local checkout vs newer remote SHA;
- parallel branches;
- abandoned dead end;
- superseded plan;
- corrupted journal segment;
- source containing a secret;
- screenshot with unknown SHA;
- mixed Claude + Codex history;
- context compaction and restart.

Measure false/missed continuation, evidence-promotion errors, replay determinism, corruption recovery, session-start token cost, repeated-dead-end prevention and time to correct project orientation.

## Strategic boundary

FIX should win on **historical truth + provenance + continuation**, not on having the largest MCP tool count.

Do not make mandatory: vector DB, knowledge graph, daemon, cloud account, background LLM distillation or swarm runtime. Those may exist only as optional adapters.
