# Repository migration — 2026-09-27

Requested destination: https://github.com/loftfull/agent-terminal (existing empty public repository).
Source: local FIX development checkout at 4c915ba plus uncommitted visual-progress work.
The fetched FIX branch was compared by tree: local code includes the upstream implementation plus later doctor consistency repairs and audit records. Its commits have different IDs; neither history is rewritten.

Destination default branch: English. Preserve codex/history-mcp-foundation too.
Original FIX repository, unrelated InstaVault branches and PR #5 are not modified.
Only the selected agent branch history is transferred. PRs/issues/settings are not Git objects and are not migrated.

The existing local dashboard files and canonical journal are included. External private chat-trial directories, virtual environments and runtime locks are excluded.
Historical journal records and source URLs remain unchanged. The new destination is appended to the journal.

Pre-transfer checks: journal integrity, replay, snapshot equality and structural validation PASS (392 records); progress dashboard JS checks PASS. Doctor WARN reflects missing host adapters, not journal corruption. No claim of continuous ChatGPT ingestion or complete acceptance is made.

## Transport fallback

Direct Git push was unavailable because the terminal has no GitHub credentials. Authenticated GitHub connector uploads the exact committed file tree instead. Native destination history starts with an import commit. Complete original selected-branch history is preserved in `migration/agent-terminal-history.bundle`. Restore with `git clone agent-terminal-history.bundle recovered-agent-terminal`. SHA-256 is recorded beside the bundle. Source history is not represented as native destination commits.
