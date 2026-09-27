import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import project_history_doctor as doctor
from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state, atomic_save_state
from project_history_hooks import checkpoint
from runtime_journal import append_mutation_set


class DoctorConsistencyTests(unittest.TestCase):
    def seed(self, root):
        bootstrap_journal_from_state(empty_state('p', 'P', 'goal'), root/'PROJECT_HISTORY.events.jsonl')
        checkpoint(root)

    def test_writer_between_replay_and_snapshot_does_not_mix_generations(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            start=threading.Event(); finished=threading.Event(); errors=[]
            def writer():
                try:
                    if not start.wait(3): raise RuntimeError('reader never started')
                    append_mutation_set(root,'project.patch',{'goal':'new goal'})
                    checkpoint(root)
                except Exception as exc: errors.append(exc)
                finally: finished.set()
            thread=threading.Thread(target=writer); thread.start()
            original=doctor.replay_journal_set
            def replay(path):
                state=original(path)
                start.set()
                finished.wait(.15)
                return state
            try:
                with patch.object(doctor,'replay_journal_set',side_effect=replay):
                    report=doctor.run_doctor(root,probe_screenshot=False)
            finally:
                start.set(); thread.join(5)
            self.assertFalse(thread.is_alive()); self.assertEqual(errors,[])
            self.assertEqual(report['checks']['snapshot_replay_match']['status'],'PASS')
            self.assertEqual(json.loads((root/'PROJECT_MEMORY.json').read_text())['project']['goal'],'new goal')

    def test_persistent_stale_snapshot_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            append_mutation_set(root,'project.patch',{'goal':'not checkpointed'})
            before=(root/'PROJECT_MEMORY.json').read_bytes()
            report=doctor.run_doctor(root,probe_screenshot=False)
            self.assertEqual(report['checks']['snapshot_replay_match']['status'],'FAIL')
            self.assertEqual(before,(root/'PROJECT_MEMORY.json').read_bytes())

    def test_checkpoint_gap_retries_without_repairing_data(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            append_mutation_set(root,'project.patch',{'goal':'pending checkpoint'})
            with patch.object(doctor.time,'sleep',side_effect=lambda _: checkpoint(root)) as pause:
                report=doctor.run_doctor(root,probe_screenshot=False)
            self.assertEqual(pause.call_count,1)
            self.assertEqual(report['checks']['snapshot_replay_match']['status'],'PASS')
            self.assertEqual(report['checks']['consistent_read']['attempts'],2)

    def test_corruption_is_not_repaired_or_hidden(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.seed(root)
            path=root/'PROJECT_HISTORY.events.jsonl'
            path.write_text(path.read_text().replace('goal','tampered',1))
            report=doctor.run_doctor(root,probe_screenshot=False)
            self.assertEqual(report['checks']['journal_integrity']['status'],'FAIL')
