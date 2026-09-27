import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import project_history_journal as journal
from project_history_agent import empty_state


class BootstrapTests(unittest.TestCase):
    def test_concurrent_creators_publish_only_one_complete_state(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'PROJECT_HISTORY.events.jsonl'
            barrier = Barrier(2)
            def create(name):
                barrier.wait(timeout=5)
                try:
                    journal.bootstrap_journal_from_state(empty_state(name, name, name), path)
                    return name
                except FileExistsError:
                    return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(create, ['a', 'b']))
            winners = [r for r in results if r is not None]
            self.assertEqual(len(winners), 1)
            self.assertTrue(journal.verify_journal(path)['ok'])
            self.assertEqual(journal.replay_journal(path)['project']['project_id'], winners[0])

    def test_preparation_failure_leaves_no_partial_journal_and_retry_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'PROJECT_HISTORY.events.jsonl'
            state = empty_state('p', 'Проект', 'Цель')
            original = journal._state_mutations
            def interrupted(value):
                for index, mutation in enumerate(original(value)):
                    if index == 2:
                        raise OSError('interrupted preparation')
                    yield mutation
            with patch.object(journal, '_state_mutations', interrupted):
                with self.assertRaises(OSError):
                    journal.bootstrap_journal_from_state(state, path)
            self.assertFalse(path.exists())
            journal.bootstrap_journal_from_state(state, path)
            self.assertEqual(journal.replay_journal(path)['project'], state['project'])

    def test_failed_publication_and_existing_file_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'PROJECT_HISTORY.events.jsonl'
            state = empty_state('p', 'p', 'p')
            with patch.object(journal.os, 'replace', side_effect=OSError('before rename')):
                with self.assertRaises(OSError):
                    journal.bootstrap_journal_from_state(state, path)
            self.assertFalse(path.exists())
            journal.bootstrap_journal_from_state(state, path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                journal.bootstrap_journal_from_state(state, path)
            self.assertEqual(path.read_bytes(), before)

    def test_lost_acknowledgement_leaves_complete_valid_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'PROJECT_HISTORY.events.jsonl'
            state = empty_state('p', 'p', 'p')
            real = journal.atomic_write_text
            def publish_then_fail(p, text):
                real(p, text)
                raise OSError('lost acknowledgement')
            with patch.object(journal, 'atomic_write_text', publish_then_fail):
                with self.assertRaises(OSError):
                    journal.bootstrap_journal_from_state(state, path)
            self.assertTrue(journal.verify_journal(path)['ok'])
            self.assertEqual(journal.replay_journal(path)['project'], state['project'])
