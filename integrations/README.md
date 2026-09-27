# Native lifecycle hook integration

Project History Agent can receive lifecycle events from Claude Code and Codex without writing to either host's conversation store.

## Safety boundary

- `native_hook_runner.py` is fail-open: an historian error must not block the coding-agent session.
- Host history remains read-only. PHA writes only its own segmented journal and projections.
- Hook templates are **template-only**. The generator never edits `.claude/settings.json`, `$CODEX_HOME/hooks.json`, or other user/global configuration.
- Chat continuation still requires the evidence-gated lineage resolver. A hook or ranked candidate cannot declare a parent chat by itself.

## Generate project-local templates

From the project root:

```bash
python native_hook_config.py write .
```

This writes:

```text
integrations/claude-code/hooks.json
integrations/codex/hooks.json
```

Run `python project_history_doctor.py . --no-screenshot-probe` to see whether the project-local templates exist. A template being present does **not** mean it has been installed in the host.

## Claude Code

The template handles the confirmed lifecycle events:

- `SessionStart`
- `PreCompact`
- `SessionEnd`

The command uses `$CLAUDE_PROJECT_DIR`, so the generated Claude template is project-portable. Review the template, then merge it into the Claude Code project hook configuration using the host's documented mechanism. Do not replace unrelated existing hooks.

## Codex

The template uses the confirmed `hooks.json` wrapper and the same lifecycle events:

- `SessionStart`
- `PreCompact`
- `SessionEnd`

Codex commands contain the absolute project path generated on the target machine. Generate the template **after cloning on that machine**. Review it before merging with any existing Codex hooks.

## Runner behavior

`SessionStart`:
- discovers bounded local Claude/Codex history roots;
- runs evidence-gated lineage resolution;
- returns a compact `PROJECT_MEMORY.md` handoff to the host model.

`PreCompact`:
- appends an observed checkpoint before context compaction;
- rebuilds deterministic snapshot/Markdown projections.

`SessionEnd`:
- checkpoints the final state;
- updates handoff state;
- closes the active runtime journal segment.

All runtime mutations continue the global hash chain without changing the immutable base journal.

## Later handoff correction — 2026-09-24

The SessionStart wording “compact” above describes the earlier implementation.
B5 now passes the full Markdown handoff, without the old character truncation.
This preserves constraints but has no token budget. Templates still do not prove
installation or a successful real-host lifecycle. See ../docs/AUDIT_REPAIRS_2026-09-24.md.
