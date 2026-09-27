"""Standalone audit fixtures. Run from any cwd; canonical history is never written."""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history_adapters import InMemoryHistoryAdapter
from native_hook_runner import _handoff_context
from project_history_agent import empty_state, render_markdown
from project_history_hooks import session_start
from project_history_journal import (ProjectLock, append_mutation, redact_secrets,
                                    replay_journal_set, verify_journal_set)
from runtime_journal import append_mutation_set


def main():
    reproduced = []
    with tempfile.TemporaryDirectory(prefix='fix-blind-lock-') as d:
        p = Path(d) / 'lock'
        a = ProjectLock(p)
        a.__enter__()
        os.utime(p, (time.time() - 301,) * 2)
        b = ProjectLock(p, timeout=.01)
        b.__enter__()
        both = a.acquired and b.acquired
        a.__exit__(None, None, None)
        deleted_other = not p.exists()
        b.__exit__(None, None, None)
        reproduced.append(('B1', both and deleted_other))

    with tempfile.TemporaryDirectory(prefix='fix-blind-mutation-') as d:
        p = Path(d)
        append_mutation(p / 'PROJECT_HISTORY.events.jsonl', 'project.patch',
                        {'project_id': 'fixture', 'name': 'fixture'})
        append_mutation_set(p, 'source.patch', {'source_id': 'missing', 'title': 'x'})
        integrity = verify_journal_set(p)['ok']
        failed = False
        try:
            replay_journal_set(p)
        except ValueError as exc:
            failed = 'cannot patch missing' in str(exc)
        reproduced.append(('B2', integrity and failed))

    with tempfile.TemporaryDirectory(prefix='fix-blind-identity-') as d:
        adapter = InMemoryHistoryAdapter([])
        session_start(d, {'chat_id': 'chat-a', 'project_id': 'A'}, adapter,
                      project_id='A', name='A', goal='A')
        result = session_start(d, {'chat_id': 'chat-b', 'project_id': 'B'}, adapter,
                               project_id='B', name='B', goal='B')['state']
        reproduced.append(('B3', result['project']['project_id'] == 'A'
                           and result['handoff']['current_chat_id'] == 'chat-b'))

    header = 'Cookie: session=synthetic-placeholder'
    reproduced.append(('B4', redact_secrets(header) == header))

    with tempfile.TemporaryDirectory(prefix='fix-blind-handoff-') as d:
        state = empty_state('fixture', 'fixture', 'fixture')
        state['project']['constraints'] = ['A' * 4000, 'CRITICAL_LAST_CONSTRAINT']
        root = Path(d)
        (root / 'PROJECT_MEMORY.md').write_text(render_markdown(state), encoding='utf-8')
        reproduced.append(('B5', 'CRITICAL_LAST_CONSTRAINT' not in _handoff_context(root)))

    for finding, result in reproduced:
        print(f'{finding}: {"REPRODUCED" if result else "NOT_REPRODUCED"}')
    return 0 if all(result for _, result in reproduced) else 1


if __name__ == '__main__':
    raise SystemExit(main())
