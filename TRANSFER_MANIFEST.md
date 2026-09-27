# Transfer Manifest — ChatGPT current project → `loftfull/FIX`

Date: 2026-09-16

## Canonical repository

- Repository: `loftfull/FIX`
- Working branch: `project-history-agent-v0.6`
- Default branch at transfer start: `English`
- Repository visibility observed at transfer time: public

## Current-chat data stored directly in Git

`chat/current/` contains the current-chat project record available to this session:

- `USER_MESSAGES.md` — user-visible project instructions from this continuation chat;
- `CHAT_SOURCE.md` — lineage and development index;
- `PROJECT_HISTORY.events.jsonl` — hash-chained append-only chat journal;
- `PROJECT_MEMORY.json` — machine snapshot;
- `PROJECT_MEMORY.md` — AI/human handoff.

The chat lineage is explicitly preserved as:

```text
агент [new]
  -> current Project History Agent chat [continuation, explicit]
```

Private model chain-of-thought is not project data and is not copied into the repository.

## Project-level data stored directly in Git

- root project journal/snapshot/handoff;
- `PROJECT_HISTORY_AGENT.md` and independent auditor protocol;
- durable journal/auditor/doctor/hooks/core modules;
- v0.6 host-native history adapters;
- v0.6 adapter regression tests;
- JSON schemas;
- v0.6 design and implementation plan;
- host integration notes.

## Historical evidence

v0.3, v0.4 and v0.5 remain preserved in ChatGPT Library as immutable historical baselines. Their factual changes are summarized in root project memory and current-chat development history.

Heavy historical ZIP archives and screenshot binary bytes were not re-encoded through the text-only GitHub Contents transfer path. They remain external evidence rather than being silently replaced with corrupted base64. Relevant provenance/report records remain in project history.

## v0.6 source archive produced during transfer

A public-safe local source archive was generated during transfer:

`ProjectHistoryAgent-v0.6-public-source.zip`

SHA-256:

`214c548e1ad3090a524c1da3767cc3f578d8f3e3b01f7565af7ab4b43eb8002d`

It is evidence of the transfer workspace but is not claimed as uploaded to GitHub unless a later GitHub artifact/release explicitly contains that hash.

## Truth rule

A GitHub branch SHA recorded inside the repository is a historical checkpoint. The true latest branch HEAD must be queried from GitHub because a metadata commit necessarily advances the branch after recording the previous SHA.
