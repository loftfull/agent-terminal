import json
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import history_watch as watch
from project_history_journal import replay_journal_set, verify_journal_set


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'checkout'
        self.root.mkdir()
        self.memory = Path(self.tmp.name) / 'memory'
        self.git('init', '-q')
        self.git('config', 'user.name', 'Observer Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.root / 'app.txt').write_text('initial', encoding="utf-8")
        self.git('add', 'app.txt')
        self.git('commit', '-qm', 'initial')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True)

    def tick(self, day=1, **kw):
        return watch.tick(self.root, self.memory, 'test-project',
                          now=datetime(2026, 9, day, 12, tzinfo=timezone.utc), **kw)

    def state(self):
        return replay_journal_set(self.memory)

    def test_initial_repeat_restart_idempotent(self):
        self.assertEqual(self.tick(initialize=True)['observations_added'], 1)
        count = verify_journal_set(self.memory)['records']
        self.assertEqual(self.tick()['observations_added'], 0)
        self.assertEqual(verify_journal_set(self.memory)['records'], count)
        self.assertEqual(len(self.state()['events']), 1)

    def test_twice_modified_same_status(self):
        self.tick(initialize=True)
        file = self.root / 'app.txt'
        file.write_text('one', encoding="utf-8")
        one = self.tick()
        file.write_text('two', encoding="utf-8")
        two = self.tick()
        self.assertEqual(two['observations_added'], 1)
        self.assertNotEqual(one['fingerprint'], two['fingerprint'])

    def test_staged_changes_same_status(self):
        self.tick(initialize=True)
        file = self.root / 'app.txt'
        file.write_text('one', encoding="utf-8"); self.git('add', 'app.txt')
        one = self.tick()
        file.write_text('two', encoding="utf-8"); self.git('add', 'app.txt')
        two = self.tick()
        self.assertEqual(two['observations_added'], 1)
        self.assertNotEqual(one['fingerprint'], two['fingerprint'])

    def test_daily_catchup_only_days_with_observations(self):
        self.tick(initialize=True)
        self.assertEqual(self.tick(day=4)['daily_summaries_added'], 1)
        self.assertEqual(self.tick(day=5)['daily_summaries_added'], 0)
        summaries = [e for e in self.state()['events'] if e['event_type'] == 'git.daily_summary']
        self.assertEqual([e['summary_date'] for e in summaries], ['2026-09-01'])

    def test_project_mismatch_and_blank(self):
        self.tick(initialize=True)
        for identity in ['other', ' ', '']:
            with self.assertRaises(ValueError):
                watch.tick(self.root, self.memory, identity)

    def test_secret_remote_redacted_before_persistence(self):
        self.git('remote', 'add', 'origin', 'https://alice:private-password@github.com/example/repo.git')
        self.tick(initialize=True)
        for path in self.memory.rglob('*'):
            if path.is_file():
                self.assertNotIn('private-password', path.read_text(encoding="utf-8"))

    def test_watch_retries_concurrent_edit_then_observes(self):
        argv = ['history_watch.py', '--root', str(self.root), '--memory-root', str(self.memory),
                '--project-id', 'test-project', '--watch']
        output = io.StringIO()
        with patch('sys.argv', argv), patch('sys.stdout', output), \
             patch('history_watch.tick', side_effect=[watch.ObservationChangedError('concurrent edit'),
                   {'observations_added': 1}]) as tick, \
             patch('history_watch.time.sleep', side_effect=[None, KeyboardInterrupt]):
            self.assertEqual(watch.main(), 0)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertTrue(records[0]['retry_next_tick'])
        self.assertEqual(records[1]['observations_added'], 1)
        self.assertEqual(tick.call_count, 2)

    def test_once_concurrent_edit_and_watch_corruption_are_fatal(self):
        for mode, error in [('--once', watch.ObservationChangedError('concurrent edit')),
                            ('--watch', ValueError('Journal integrity failure'))]:
            argv = ['history_watch.py', '--root', str(self.root), '--memory-root', str(self.memory),
                    '--project-id', 'test-project', mode]
            with patch('sys.argv', argv), patch('sys.stderr', io.StringIO()), \
                 patch('history_watch.tick', side_effect=error), \
                 patch('history_watch.time.sleep') as sleep:
                with self.assertRaises(SystemExit) as raised:
                    watch.main()
                self.assertEqual(raised.exception.code, 1)
                sleep.assert_not_called()

    def test_git_fsmonitor_hook_disabled(self):
        with patch('history_watch.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = b'ok'
            self.assertEqual(watch.git(self.root, 'status'), 'ok')
            command = run.call_args.args[0]
            self.assertIn('core.fsmonitor=false', command)

    def test_configured_clean_filter_is_not_executed(self):
        marker = self.root / 'executed-marker'
        self.git('config', 'filter.audit.clean', 'echo executed > executed-marker; cat')
        self.git('config', 'filter.audit.required', 'true')
        (self.root / '.gitattributes').write_text('app.txt filter=audit\n', encoding="utf-8")
        (self.root / 'app.txt').write_text('changed', encoding="utf-8")
        self.tick(initialize=True)
        self.assertFalse(marker.exists())
        self.git('config', 'filter.audit.process', 'echo executed > executed-marker; cat')
        (self.root / 'app.txt').write_text('another', encoding="utf-8")
        self.tick()
        self.assertFalse(marker.exists())

    def test_secret_in_tracked_filename_redacted(self):
        secret = 'ghp_' + 'A' * 36
        file = self.root / secret
        file.write_text('initial', encoding="utf-8")
        self.git('add', secret)
        self.git('commit', '-qm', 'synthetic secret filename')
        file.write_text('changed', encoding="utf-8")
        self.tick(initialize=True)
        for path in self.memory.rglob('*'):
            if path.is_file():
                self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_missing_git(self):
        with patch('history_watch.subprocess.run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                self.tick(initialize=True)
        self.assertFalse(self.memory.exists())

    def test_explicit_initialize_and_orphan_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'initialize'):
            self.tick()
        (self.memory / 'PROJECT_MEMORY.json').write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, 'snapshot without journal'):
            self.tick(initialize=True)

    def test_timezone_required(self):
        with self.assertRaisesRegex(ValueError, 'Timezone'):
            watch.tick(self.root, self.memory, 'test-project', now=datetime(2026, 9, 1))

    def test_projection_recovery(self):
        self.tick(initialize=True)
        (self.memory / 'PROJECT_MEMORY.json').write_text('{}', encoding="utf-8")
        (self.memory / 'PROJECT_MEMORY.md').write_text('stale', encoding="utf-8")
        self.assertEqual(self.tick()['observations_added'], 0)
        self.assertEqual(json.loads((self.memory / 'PROJECT_MEMORY.json').read_text(encoding="utf-8")), self.state())
        self.assertNotEqual((self.memory / 'PROJECT_MEMORY.md').read_text(encoding="utf-8"), 'stale')

    def test_recover_crash_between_source_and_event(self):
        original = watch.append_mutation_set
        def crashing(root, op, payload, **kw):
            if op == 'event.add':
                raise OSError('simulated interruption')
            return original(root, op, payload, **kw)
        with patch('history_watch.append_mutation_set', side_effect=crashing):
            with self.assertRaises(OSError):
                self.tick(initialize=True)
        self.assertEqual(self.tick(day=2)['observations_added'], 1)
        self.assertEqual(len(self.state()['sources']), 1)
        observation = next(e for e in self.state()['events'] if e['event_type'] == 'git.observation')
        self.assertTrue(observation['occurred_at'].startswith('2026-09-01'))

    def test_metadata_change_during_observation_rejected(self):
        original = watch.git_metadata
        calls = 0
        def changing(root):
            nonlocal calls
            calls += 1
            result = original(root)
            if calls == 2: result['head'] = 'changed'
            return result
        with patch('history_watch.git_metadata', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'metadata changed'):
                self.tick(initialize=True)
        self.assertFalse(self.memory.exists())


if __name__ == '__main__':
    unittest.main()
