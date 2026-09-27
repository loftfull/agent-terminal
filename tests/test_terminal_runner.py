import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state, replay_journal_set, verify_journal_set
from terminal_control import submit_contract, terminal_status, record_report
from runtime_journal import append_mutation_set
from terminal_runner import run_command, restore_runs, runs_from_state, _record, _runner_lock


class TerminalRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        bootstrap_journal_from_state(empty_state('p', 'Project', ''), self.root / 'PROJECT_HISTORY.events.jsonl')
        submit_contract(self.root, 'p', {'task_id': 't', 'title': 'Run', 'purpose': 'Observed execution',
            'deliverables': ['stdout'], 'acceptance': ['human review'], 'constraints': [],
            'stop_conditions': ['timeout'], 'max_continuations': 2})

    def run_code(self, code, **kwargs):
        return run_command(self.root, 'p', 't', [sys.executable, '-c', code], self.root, **kwargs)

    def test_real_success_preserves_metadata_and_never_accepts(self):
        out = self.run_code("print('hello'); import sys; print('error stream',file=sys.stderr)", model_id='explicit-model',session_id='s')
        self.assertEqual(out['status'], 'succeeded')
        self.assertEqual(out['exit_code'], 0)
        self.assertEqual(out['stdout']['text'], 'hello\n' if os.name != 'nt' else 'hello\r\n')
        self.assertIn('error stream', out['stderr']['text'])
        self.assertEqual(out['model_id'], 'explicit-model')
        self.assertFalse(out['accepted'])
        self.assertIsNotNone(out['started_at'])
        self.assertIsNotNone(out['ended_at'])
        self.assertEqual(terminal_status(self.root,'p')['accepted_count'], 0)
        self.assertEqual(len(runs_from_state(replay_journal_set(self.root))), 1)
        self.assertTrue(verify_journal_set(self.root)['ok'])
        state = replay_journal_set(self.root)
        saved = next(e for e in state['events'] if e['event_id'] == out['event_id'])
        self.assertEqual(saved['runner_payload']['status'], 'succeeded')
        self.assertEqual(saved['runner_payload']['stdout'], out['stdout'])
        sources = {s['source_id']: s for s in state['sources']}
        self.assertTrue(saved['source_ids'])
        self.assertEqual(sources[saved['source_ids'][0]]['input'], saved['runner_payload'])
        # The receipt is immediately usable as referenced evidence in task control.
        record_report(self.root, 'p', {'task_id': 't', 'status': 'review', 'summary': 'Process observed',
            'evidence_event_ids': [out['event_id']]})

    def test_missing_completion_mutation_cannot_return_success_receipt(self):
        def omit_completion(root, op, payload, **kwargs):
            if op == 'event.add' and payload.get('runner_payload', {}).get('status') == 'succeeded':
                return {}
            return append_mutation_set(root, op, payload, **kwargs)
        with patch('terminal_runner.append_mutation_set', side_effect=omit_completion):
            with self.assertRaisesRegex(RuntimeError, 'persistence verification'):
                self.run_code('print(42)')

    def test_nonzero_and_launch_error_are_truthful(self):
        out = self.run_code('raise SystemExit(7)')
        self.assertEqual((out['status'], out['exit_code']), ('failed', 7))
        out = run_command(self.root,'p','t',[str(self.root/'missing-executable')],self.root,continuation_count=1)
        self.assertEqual(out['status'],'launch_error')
        self.assertIsNone(out['exit_code'])

    def test_timeout_terminates_process_tree(self):
        marker = self.root / 'child survived.txt'
        child = 'import time; from pathlib import Path; time.sleep(1.5); Path('+repr(str(marker))+').write_text("bad")'
        parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); time.sleep(30)'
        started = time.monotonic()
        out = self.run_code(parent, timeout=0.4)
        self.assertEqual(out['status'], 'timed_out')
        self.assertLess(time.monotonic()-started, 3)
        time.sleep(1.5)
        self.assertFalse(marker.exists(), 'timed-out child executed after supervisor returned')

    def test_leader_exit_does_not_leave_descendant_running(self):
        marker = self.root / 'orphan survived.txt'
        child = 'import time; from pathlib import Path; time.sleep(1.0); Path('+repr(str(marker))+').write_text("bad")'
        parent = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c",'+repr(child)+'])'
        out = self.run_code(parent,timeout=0.3)
        self.assertEqual(out['status'],'timed_out')
        time.sleep(1)
        self.assertFalse(marker.exists())

    def test_output_bound_drain_no_deadlock_and_secret_redaction(self):
        out = self.run_code("import sys; print('password=hidden-value'); print('x'*200000); print('z'*200000,file=sys.stderr)",max_output_bytes=256)
        self.assertEqual(out['status'],'succeeded')
        self.assertIn('[REDACTED]',out['stdout']['text'])
        for stream in ('stdout','stderr'):
            self.assertLessEqual(len(out[stream]['text'].encode()),256)
            self.assertTrue(out[stream]['truncated'])
            self.assertGreater(out[stream]['bytes_seen'],100000)
        # Invocation source itself is also redacted.
        for path in self.root.rglob('*.json*'):
            self.assertNotIn('hidden-value',path.read_text(encoding='utf-8'))

    def test_argv_spaces_metacharacters_and_no_shell(self):
        script = self.root / 'script with spaces.py'
        script.write_text('import sys; print(sys.argv[1])',encoding='utf-8')
        literal = 'a b; $(touch NO); & echo nope'
        with patch('terminal_runner.subprocess.Popen', wraps=subprocess.Popen) as popen:
            out = run_command(self.root,'p','t',[sys.executable,str(script),literal],self.root)
        self.assertIn(literal,out['stdout']['text'])
        self.assertFalse((self.root/'NO').exists())
        self.assertIs(popen.call_args.kwargs['shell'],False)

    def test_flag_value_secrets_are_not_persisted(self):
        script = self.root/'silent.py'
        script.write_text('pass',encoding='utf-8')
        out = run_command(self.root,'p','t',[sys.executable,str(script),'--api-key','sensitivevalue'],self.root)
        self.assertEqual(out['argv'][-1],'[REDACTED]')
        for path in self.root.rglob('*.json*'):
            self.assertNotIn('sensitivevalue',path.read_text(encoding='utf-8'))

    def test_retry_is_explicit_and_bounded(self):
        self.run_code('pass')
        with self.assertRaisesRegex(ValueError,'continuation'):
            self.run_code('pass')
        self.run_code('pass',continuation_count=1)
        self.run_code('pass',continuation_count=2)
        with self.assertRaisesRegex(ValueError,'continuation'):
            self.run_code('pass',continuation_count=3)
        self.assertEqual(len(runs_from_state(replay_journal_set(self.root))),3)

    def test_kernel_lock_prevents_concurrent_runs_without_age_steal(self):
        with _runner_lock(self.root):
            os.utime(self.root/'.terminal-runner.lock',(0,0))
            with self.assertRaises(TimeoutError):
                self.run_code('pass')
            with self.assertRaises(TimeoutError):
                restore_runs(self.root,'p')
        self.assertEqual(self.run_code('pass')['status'],'succeeded')

    def test_crashed_run_restores_interrupted_never_assumes_child_exit(self):
        _record(self.root, {'run_id':'crash','task_id':'t','project_id':'p','status':'running',
            'started_at':'2026-09-24T00:00:00+00:00','model_id':'unknown','session_id':'unknown',
            'continuation_count':0,'process_id':1234,'accepted':False})
        before = runs_from_state(replay_journal_set(self.root))
        self.assertEqual(before[0]['status'],'running')
        restored = restore_runs(self.root,'p')
        self.assertEqual(restored[0]['status'],'interrupted')
        self.assertEqual(restored[0]['child_process_state'],'unknown')
        self.assertEqual(restore_runs(self.root,'p'),[])
        with self.assertRaises(ValueError):
            self.run_code('pass')
        self.assertEqual(self.run_code('pass',continuation_count=1)['status'],'succeeded')

    def test_invalid_inputs_cannot_launch(self):
        invalid = [{'argv':'echo unsafe'}, {'timeout':0}, {'timeout':float('nan')}, {'timeout':True},
            {'cwd':'.'}, {'max_output_bytes':False}, {'continuation_count':True}, {'task_id':'missing'},
            {'project_id':'other'}]
        with patch('terminal_runner.subprocess.Popen') as popen:
            for fields in invalid:
                request = dict(root=self.root,project_id='p',task_id='t',argv=[sys.executable,'-c','pass'],cwd=self.root)
                request.update(fields)
                with self.assertRaises(ValueError, msg=str(fields)):
                    run_command(**request)
            popen.assert_not_called()

    def test_cli_utf8_receipt_under_legacy_stdout_codepage(self):
        cwd = self.root / 'Папка проекта'
        cwd.mkdir()
        request = self.root / 'unicode-request.json'
        # Explicit UTF-8 bytes from the child keep this check focused on receipt encoding.
        request.write_text(json.dumps(dict(root=str(self.root), project_id='p', task_id='t',
            argv=[sys.executable, '-c', "import sys; sys.stdout.buffer.write('Привет\\n'.encode('utf-8'))"],
            cwd=str(cwd)), ensure_ascii=False), encoding='utf-8')
        env = dict(os.environ, PYTHONIOENCODING='cp1252')
        process = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1]/'terminal_runner.py'),
            '--request', str(request)], capture_output=True, text=True, encoding='utf-8', env=env, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        receipt = json.loads(process.stdout)
        self.assertEqual(receipt['cwd'], str(cwd.resolve()))
        self.assertEqual(receipt['stdout']['text'], 'Привет\n')

    def test_cli_json_real_process(self):
        request = self.root/'request.json'
        request.write_text(json.dumps(dict(root=str(self.root),project_id='p',task_id='t',
            argv=[sys.executable,'-c',"print('real cli')"],cwd=str(self.root))),encoding='utf-8')
        process = subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'terminal_runner.py'),
            '--request',str(request)],capture_output=True,text=True,encoding='utf-8',timeout=15)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(json.loads(process.stdout)['status'],'succeeded')


if __name__ == '__main__':
    unittest.main()
