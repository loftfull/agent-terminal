"""Scoped, polling Git observer. No network access or project code execution."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

from project_history_agent import empty_state, render_markdown
from project_history_hooks import checkpoint
from project_history_journal import (ProjectLock, bootstrap_journal_from_state,
    redact_secrets, replay_journal_set, verify_journal_set)
from runtime_journal import append_mutation_set


class ObservationChangedError(ValueError):
    """Transient concurrent edit; a watch loop may retry on its next interval."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def git(root, *args, optional=False):
    # Git status can run clean/process filters. Discover names only, then override
    # every configured driver for each probe. Never print/store configured commands.
    base = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', str(root)]
    kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False,
                  env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_PAGER': 'cat'})
    try:
        config = subprocess.run(base + ['config', '--null', '--name-only', '--get-regexp',
                                       r'^filter\..*\.(clean|process|required)$'], **kwargs)
        if config.returncode not in (0, 1):
            raise ValueError('Cannot inspect Git filter configuration safely')
        if len(config.stdout) > 8_000_000:
            raise ValueError('Git configuration exceeded 8 MB limit')
        overrides = []
        for key in config.stdout.decode('utf-8', errors='surrogateescape').split('\0'):
            if key.startswith('filter.') and key.rsplit('.', 1)[-1] in {'clean', 'process', 'required'}:
                overrides.extend(['-c', key + ('=false' if key.endswith('.required') else '=')])
        result = subprocess.run(base + overrides + list(args), **kwargs)
    except FileNotFoundError as exc:
        raise ValueError('Git executable is unavailable') from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Git observation timed out') from exc
    if result.returncode:
        if optional: return None
        raise ValueError('Git observation failed: ' + str(redact_secrets(result.stderr.decode(errors='replace'))))
    if len(result.stdout) > 8_000_000:
        raise ValueError('Git probe exceeded 8 MB limit')
    return result.stdout.decode('utf-8', errors='surrogateescape')


def git_metadata(root):
    return {
        "head": git(root, "rev-parse", "--verify", "HEAD", optional=True),
        "branch": git(root, "symbolic-ref", "--quiet", "--short", "HEAD", optional=True),
        "remotes": git(root, "remote", "-v"),
        "status": git(root, "status", "--porcelain=v1", "-z", "--untracked-files=normal", "--ignore-submodules=all"),
        "worktrees": git(root, "worktree", "list", "--porcelain"),
        "refs": git(root, "for-each-ref", "--format=%(refname) %(objectname)"),
        "index_entries": git(root, "ls-files", "-s", "-z"),
    }


def snapshot(root):
    root = Path(root).resolve(strict=True)
    actual = Path(git(root, 'rev-parse', '--show-toplevel').strip()).resolve()
    if actual != root:
        raise ValueError('--root must identify the Git working tree root')
    before_metadata = git_metadata(root)
    changed = git(root, 'ls-files', '-m', '-z').split('\0')
    hashes = {}
    for name in filter(None, changed):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            hashes[name] = 'not-read:symlink-or-outside-root'; continue
        try:
            # Reject symlink components; bound reads and detect concurrent edits.
            if any(p.is_symlink() for p in [path, *path.parents] if p != root):
                hashes[name] = 'not-read:symlink'; continue
            before = path.stat()
            if not stat.S_ISREG(before.st_mode) or before.st_size > 16_000_000:
                hashes[name] = {'not_read': 'nonregular-or-over-16MB', 'size': before.st_size,
                                'mtime_ns': before.st_mtime_ns}; continue
            with path.open('rb') as stream:
                data = stream.read(16_000_001)
            after = path.stat()
            if len(data) > 16_000_000 or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ObservationChangedError('Tracked file changed during observation; retry next tick')
            hashes[name] = hashlib.sha256(data).hexdigest()
        except FileNotFoundError:
            hashes[name] = 'deleted'
    if before_metadata != git_metadata(root):
        raise ObservationChangedError('Git metadata changed during observation; retry next tick')
    return redact_secrets({'root': str(root), **before_metadata,
        'modified_tracked_sha256': [{'path': name, 'content': value} for name, value in hashes.items()],
        'coverage': 'Local Git only; no remote refresh. Untracked file contents not read. No model attribution inferred.'})


def tick(root, memory_root, project_id, *, initialize=False, now=None):
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("Nonempty project_id required")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('Timezone-aware timestamp required')
    now = now.astimezone(timezone.utc)
    observed = snapshot(root)
    memory = Path(memory_root).resolve()
    checkout = Path(root).resolve()
    if memory == checkout or memory.is_relative_to(checkout):
        raise ValueError('--memory-root must be outside observed checkout to avoid self-observation')
    memory.mkdir(parents=True, exist_ok=True)
    with ProjectLock(memory / '.history-watch.lock', timeout=5):
        journal = memory / 'PROJECT_HISTORY.events.jsonl'
        if not journal.exists():
            if (memory / 'PROJECT_MEMORY.json').exists() or (memory / 'PROJECT_MEMORY.md').exists():
                raise ValueError('Existing snapshot without journal; explicit recovery required')
            if not initialize: raise ValueError('Missing journal; use --initialize explicitly')
            bootstrap_journal_from_state(empty_state(project_id, project_id, 'Scoped local project observation'), journal)
        verified = verify_journal_set(memory)
        if not verified['ok']: raise ValueError('Journal integrity failure')
        state = replay_journal_set(memory)
        if state['project']['project_id'] != project_id: raise ValueError('Project identity mismatch')
        watcher = digest({'project_id': project_id, 'root': observed['root']})[:20]
        events = [e for e in state['events'] if e.get('watcher_id') == watcher]
        observations = [e for e in events if e.get('event_type') == 'git.observation']
        fp = digest(observed)
        added = 0
        if not observations or observations[-1]['fingerprint'] != fp:
            eid = 'WATCH-' + digest([watcher, len(observations), fp])[:24]
            sid = eid + '-source'
            existing_source = next((s for s in state['sources'] if s['source_id'] == sid), None)
            if existing_source is None:
                append_mutation_set(memory, 'source.add', {'source_id': sid, 'kind': 'local-git-observation',
                'title': 'Read-only local Git snapshot', 'locator': observed['root'],
                'captured_at': now.isoformat(), 'snapshot': observed}, timestamp=now.isoformat())
            if existing_source is not None:
                if existing_source.get('snapshot') != observed:
                    raise ValueError('Observation source identity conflict')
                observation_time = existing_source['captured_at']
            else:
                observation_time = now.isoformat()
            event = {'event_id': eid, 'event_type': 'git.observation', 'watcher_id': watcher,
                'occurred_at': observation_time, 'evidence_status': 'observed', 'source_ids': [sid],
                'fingerprint': fp, 'summary': 'Local Git snapshot changed: ' + fp,
                'tool': 'history_watch', 'model_id': 'unknown', 'author': 'local observer'}
            append_mutation_set(memory, 'event.add', event, timestamp=now.isoformat())
            observations.append(event); added = 1
        completed = {e.get('summary_date') for e in events if e.get('event_type') == 'git.daily_summary'}
        days = defaultdict(list)
        for event in observations:
            day = event['occurred_at'][:10]
            if day < now.date().isoformat() and day not in completed: days[day].append(event)
        for day, items in sorted(days.items()):
            append_mutation_set(memory, 'event.add', {
                'event_id': 'DAY-' + digest([watcher, day])[:24], 'event_type': 'git.daily_summary',
                'watcher_id': watcher, 'summary_date': day, 'occurred_at': now.isoformat(),
                'source_ids': sorted({s for e in items for s in e['source_ids']}),
                'evidence_status': 'observed', 'observation_count': len(items),
                'summary': f'{day} UTC: {len(items)} changed Git snapshots observed. This is not a feature-progress measure; offline changes may be missing.',
                'tool': 'history_watch', 'model_id': 'unknown'}, timestamp=now.isoformat())
        current = replay_journal_set(memory)
        try:
            projections_current = (json.loads((memory / 'PROJECT_MEMORY.json').read_text(encoding='utf-8')) == current
                and (memory / 'PROJECT_MEMORY.md').read_text(encoding='utf-8') == render_markdown(current))
        except (OSError, ValueError):
            projections_current = False
        if added or days or not projections_current: checkpoint(memory)
        return {'observations_added': added, 'daily_summaries_added': len(days), 'fingerprint': fp}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--memory-root', required=True)
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--initialize', action='store_true')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once', action='store_true'); mode.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=float, default=60)
    args = parser.parse_args()
    if not 1 <= args.interval <= 86400: parser.error('interval must be between 1 and 86400 seconds')
    try:
        while True:
            try:
                result = tick(args.root, args.memory_root, args.project_id, initialize=args.initialize)
            except ObservationChangedError as exc:
                if args.once:
                    raise
                result = {'status': 'observation-skipped', 'retry_next_tick': True,
                          'reason': str(redact_secrets(str(exc)))}
            print(json.dumps(result), flush=True)
            if args.once: break
            time.sleep(args.interval)
    except KeyboardInterrupt: return 0
    except (ValueError, OSError) as exc:
        parser.exit(1, str(redact_secrets(str(exc))) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
