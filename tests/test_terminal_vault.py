import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
import threading
from contextlib import closing
from unittest.mock import patch
from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state, journal_paths, replay_journal_set, verify_journal_set
from runtime_journal import append_mutation_set
from terminal_vault import capture, verify, recover
from project_history_mcp import HistoryReader


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'память'
        self.root.mkdir()
        self.vault = self.base / 'backup' / 'history.sqlite'
        bootstrap_journal_from_state(empty_state('p', 'Пример', 'History'), self.root/'PROJECT_HISTORY.events.jsonl')

    def test_exact_restore_idempotency_and_fresh_process(self):
        append_mutation_set(self.root, 'handoff.patch', {'next_step': 'Проверить полный текст'})
        first = capture(self.root, 'p', self.vault)
        self.assertEqual(first['version'], 1)
        self.assertEqual(capture(self.root, 'p', self.vault)['status'], 'unchanged')
        restored = self.base / 'recovered'
        code = Path(__file__).resolve().parents[1] / 'terminal_vault.py'
        process = subprocess.run([sys.executable, str(code), 'recover', '--project-id', 'p',
            '--vault', str(self.vault), '--destination', str(restored)], capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(replay_journal_set(self.root), replay_journal_set(restored))
        for path in journal_paths(self.root):
            self.assertEqual(path.read_bytes(), (restored / path.relative_to(self.root)).read_bytes())
        self.assertEqual(json.loads((restored/'PROJECT_MEMORY.json').read_text(encoding='utf-8')), replay_journal_set(restored))

    def test_valid_tail_rollback_refused_by_capture_and_mcp(self):
        capture(self.root, 'p', self.vault)
        record = append_mutation_set(self.root, 'handoff.patch', {'next_step': 'Finish'})
        capture(self.root, 'p', self.vault)
        tail = journal_paths(self.root)[-1]
        tail.write_bytes(b'')  # Fault injection: clean tail removal keeps the old hash-chain valid.
        self.assertTrue(verify_journal_set(self.root)['ok'])
        for call in [lambda: verify(self.root, 'p', self.vault),
                     lambda: capture(self.root, 'p', self.vault),
                     lambda: HistoryReader(self.root, 'p', vault=self.vault).context()]:
            with self.assertRaisesRegex(ValueError, 'rollback'):
                call()
        restored = self.base/'recovered'
        recover('p', self.vault, restored)
        self.assertEqual(verify_journal_set(restored)['last_hash'], record['hash'])

    def test_new_records_reported_as_unprotected(self):
        capture(self.root, 'p', self.vault)
        append_mutation_set(self.root, 'handoff.patch', {'next_step': 'Next'})
        self.assertEqual(verify(self.root, 'p', self.vault)['unprotected_records'], 1)
        capture(self.root, 'p', self.vault)
        self.assertEqual(verify(self.root, 'p', self.vault)['status'], 'matched')

    def test_verify_and_mcp_never_acquire_project_lock_or_write_files(self):
        capture(self.root, 'p', self.vault)
        lock = self.root / '.project-history.lock'
        lock.write_text('existing external lock; do not touch', encoding='utf-8')
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with patch('terminal_vault.ProjectLock', side_effect=AssertionError('read-only verification attempted a lock')):
            self.assertEqual(verify(self.root, 'p', self.vault)['status'], 'matched')
            HistoryReader(self.root, 'p', vault=self.vault).context()
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_oversized_serialized_envelope_is_not_committed(self):
        capture(self.root, 'p', self.vault)
        append_mutation_set(self.root, 'handoff.patch', {'next_step': '\\' * 4000})
        with patch('terminal_vault.MAX_ENVELOPE_BYTES', 8000):
            with self.assertRaisesRegex(ValueError, 'envelope exceeds'):
                capture(self.root, 'p', self.vault)
        self.assertEqual(verify(self.root, 'p', self.vault)['version'], 1)

    def test_diverging_branch_cannot_replace_vault(self):
        append_mutation_set(self.root, 'handoff.patch', {'next_step': 'A'})
        capture(self.root, 'p', self.vault)
        journal_paths(self.root)[-1].write_bytes(b'')
        append_mutation_set(self.root, 'handoff.patch', {'next_step': 'B'})
        with self.assertRaisesRegex(ValueError, 'divergence'):
            capture(self.root, 'p', self.vault)

    def test_missing_witness_and_wrong_project_fail_closed(self):
        with self.assertRaises(FileNotFoundError):
            verify(self.root, 'p', self.vault)
        self.assertFalse(self.vault.exists())
        with self.assertRaises(ValueError):
            capture(self.root, 'wrong', self.vault)
        self.assertFalse(self.vault.exists())
        capture(self.root, 'p', self.vault)
        with self.assertRaises(ValueError):
            verify(self.root, 'wrong', self.vault)

    def test_no_overwrite_or_in_project_vault(self):
        with self.assertRaises(ValueError):
            capture(self.root, 'p', self.root/'backup.sqlite')
        capture(self.root, 'p', self.vault)
        before = {str(p): p.read_bytes() for p in journal_paths(self.root)}
        with self.assertRaises(FileExistsError):
            recover('p', self.vault, self.root)
        self.assertEqual(before, {str(p): p.read_bytes() for p in journal_paths(self.root)})

    def test_failed_transaction_keeps_previous_capture(self):
        capture(self.root, 'p', self.vault)
        append_mutation_set(self.root, 'handoff.patch', {'next_step': 'New'})
        with patch('eventsourcing.sqlite.SQLiteAggregateRecorder.insert_events', side_effect=RuntimeError('disk error')):
            with self.assertRaises(RuntimeError):
                capture(self.root, 'p', self.vault)
        self.assertEqual(verify(self.root, 'p', self.vault)['version'], 1)
        self.assertEqual(verify(self.root, 'p', self.vault)['unprotected_records'], 1)

    def test_vault_payload_tamper_refused(self):
        capture(self.root, 'p', self.vault)
        with closing(sqlite3.connect(self.vault)) as db, db:
            db.execute('UPDATE fix_vault_events SET state=?', (b'{}',))
        with self.assertRaises(ValueError):
            verify(self.root, 'p', self.vault)

    def test_runner_captures_final_receipt(self):
        from terminal_control import submit_contract
        from terminal_runner import run_command
        submit_contract(self.root, 'p', {'task_id':'t','title':'Check','purpose':'Check process',
            'deliverables':['receipt'],'acceptance':['exit0'],'constraints':[], 'stop_conditions':['failure']})
        capture(self.root, 'p', self.vault)
        result = run_command(self.root, 'p', 't', [sys.executable, '-c', 'print("ok")'],
                             self.root.resolve(), vault=self.vault)
        self.assertEqual(result['status'], 'succeeded')
        self.assertEqual(verify(self.root, 'p', self.vault)['status'], 'matched')
        restored = self.base/'restored'
        recover('p', self.vault, restored)
        self.assertIn(result['event_id'], [e['event_id'] for e in replay_journal_set(restored)['events']])

    def test_secret_in_dictionary_key_refuses_capture(self):
        secret = 'ghp_' + 'A' * 40
        append_mutation_set(self.root, 'source.add', {'source_id': 'S', 'kind': 'test',
            'metadata': {'nested': [{secret: 'value'}]}})
        with self.assertRaisesRegex(ValueError, 'unredacted secret'):
            capture(self.root, 'p', self.vault)
        self.assertFalse(self.vault.exists())

    def test_malformed_database_returns_controlled_failure(self):
        capture(self.root, 'p', self.vault)
        self.vault.write_bytes(b'not sqlite')
        with self.assertRaisesRegex(ValueError, 'Vault storage'):
            HistoryReader(self.root, 'p', vault=self.vault).context()

    def test_malformed_envelope_is_rejected(self):
        capture(self.root, 'p', self.vault)
        for invalid in [[], {'schema': 'fix-journal-vault/v1', 'project_id': 'p'}]:
            with closing(sqlite3.connect(self.vault)) as db, db:
                db.execute('UPDATE fix_vault_events SET state=?', (json.dumps(invalid).encode(),))
            with self.assertRaisesRegex(ValueError, 'digest or identity'):
                verify(self.root, 'p', self.vault)

    def test_path_traversal_and_nonobject_records_are_rejected(self):
        from terminal_vault import _validate
        for path in ['../escape.jsonl', 'PROJECT_HISTORY.segments/../escape.jsonl',
                     'PROJECT_HISTORY.segments/../../escape.jsonl', '/absolute.jsonl',
                     'PROJECT_HISTORY.segments\\escape.jsonl']:
            with self.assertRaisesRegex(ValueError, 'manifest'):
                _validate({'PROJECT_HISTORY.events.jsonl': '{}', path: '{}'}, 'p')
        with self.assertRaisesRegex(ValueError, 'JSON objects'):
            _validate({'PROJECT_HISTORY.events.jsonl': '[]\n'}, 'p')

    def test_symlink_journal_cannot_archive_external_file(self):
        journal = self.root / 'PROJECT_HISTORY.events.jsonl'
        external = self.base / 'external.jsonl'
        journal.rename(external)
        try:
            journal.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest('This host cannot create symlinks')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            capture(self.root, 'p', self.vault)
        self.assertFalse(self.vault.exists())

    def test_concurrent_capture_keeps_single_monotonic_version(self):
        from terminal_vault import _latest
        capture(self.root, 'p', self.vault)
        append_mutation_set(self.root, 'handoff.patch', {'next_step': 'Concurrent'})
        barrier = threading.Barrier(2)
        def simultaneous_latest(recorder, project_id):
            result = _latest(recorder, project_id)
            barrier.wait(timeout=5)
            return result
        def call():
            try:
                return capture(self.root, 'p', self.vault)['status']
            except ValueError:
                return 'conflict'
        with patch('terminal_vault._latest', side_effect=simultaneous_latest):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: call(), range(2)))
        self.assertCountEqual(results, ['captured', 'conflict'])
        self.assertEqual(verify(self.root, 'p', self.vault)['version'], 2)
        restored = self.base / 'concurrent-restored'
        recover('p', self.vault, restored)
        self.assertEqual(replay_journal_set(self.root), replay_journal_set(restored))

    def test_runner_refuses_corrupt_witness_before_launch(self):
        from terminal_runner import run_command
        from terminal_control import submit_contract
        submit_contract(self.root, 'p', {'task_id':'t','title':'Check','purpose':'Before launch',
            'deliverables':['receipt'],'acceptance':['exit0'],'constraints':[], 'stop_conditions':['failure']})
        capture(self.root, 'p', self.vault)
        self.vault.write_bytes(b'not sqlite')
        with patch('terminal_runner.subprocess.Popen') as popen:
            with self.assertRaises(ValueError):
                run_command(self.root, 'p', 't', [sys.executable, '-c', 'pass'],
                            self.root.resolve(), vault=self.vault)
            popen.assert_not_called()

    def test_deleted_witness_is_not_recreated_by_runner(self):
        from terminal_runner import run_command
        from terminal_control import submit_contract
        submit_contract(self.root, 'p', {'task_id':'t','title':'Check','purpose':'Existing witness',
            'deliverables':['receipt'],'acceptance':['exit0'],'constraints':[], 'stop_conditions':['failure']})
        capture(self.root, 'p', self.vault)
        self.vault.unlink()
        with patch('terminal_runner.subprocess.Popen') as popen:
            with self.assertRaises(FileNotFoundError):
                run_command(self.root, 'p', 't', [sys.executable, '-c', 'pass'],
                            self.root.resolve(), vault=self.vault)
            popen.assert_not_called()
        self.assertFalse(self.vault.exists())

    def test_failed_sqlite_connection_setup_closes_raw_handle(self):
        capture(self.root, 'p', self.vault)
        self.vault.write_bytes(b'not sqlite')
        real_connect = sqlite3.connect
        opened = []
        def keep_reference(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            opened.append(connection)
            return connection
        with patch('terminal_vault.sqlite3.connect', side_effect=keep_reference):
            with self.assertRaisesRegex(ValueError, 'Vault storage'):
                verify(self.root, 'p', self.vault)
        self.assertTrue(opened)
        # Keep Python objects alive to rule out accidental GC closing the leak.
        for connection in opened:
            with self.assertRaisesRegex(sqlite3.ProgrammingError, 'closed'):
                connection.execute('SELECT 1')
        moved = self.vault.with_name('closed-corrupt.sqlite')
        self.vault.rename(moved)
        moved.unlink()


if __name__ == '__main__':
    unittest.main()
