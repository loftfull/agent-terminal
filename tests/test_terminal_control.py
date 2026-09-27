import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state, replay_journal_set, verify_journal_set
from runtime_journal import append_mutation_set
from terminal_control import submit_contract, record_report, terminal_status, tasks_from_state, render_tasks


class TerminalControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        bootstrap_journal_from_state(empty_state('p','Project',''),self.root/'PROJECT_HISTORY.events.jsonl')
        self.contract={'task_id':'t1','title':'Проверка','purpose':'Purpose','deliverables':['preview'],
                       'acceptance':['real capture'],'constraints':[{'rule':'No deploy','reason':'review first'}],
                       'stop_conditions':['credentials missing'],'max_continuations':2}
    def submit(self):
        return submit_contract(self.root,'p',self.contract)
    def report(self,**kw):
        return record_report(self.root,'p',dict(task_id='t1',status='running',summary='Reported',**kw))
    def test_restart_and_flattened_contract(self):
        self.submit()
        self.report(model_id='model-x',session_id='s1')
        state=terminal_status(self.root,'p')
        self.assertEqual(state['counts']['running'],1)
        self.assertEqual(state['tasks'],list(tasks_from_state(replay_journal_set(self.root)).values()))
        self.assertEqual(state['tasks'][0]['constraints'],self.contract['constraints'])
        self.assertEqual(state['tasks'][0]['model_id'],'model-x')
    def test_event_preserves_report_attribution(self):
        self.submit()
        result=self.report(model_id='model-x',session_id='session-42')
        state=replay_journal_set(self.root)
        event=next(e for e in state['events'] if e['event_id']==result['event_id'])
        self.assertEqual(event['model_id'],'model-x')
        self.assertEqual(event['session_id'],'session-42')
        self.assertEqual(event['author'],'reported executor')
        self.assertEqual(event['evidence_status'],'reported')

    def test_markdown_includes_contract_constraints_and_escaped_reports(self):
        self.submit()
        record_report(self.root,'p',{'task_id':'t1','status':'done','summary':'<script>unsafe</script> ![image](remote)',
            'model_id':'model-x','session_id':'s1'})
        markdown=render_tasks(replay_journal_set(self.root))
        for expected in ('No deploy','review first','credentials missing','real capture','review','Accepted: false'):
            self.assertIn(expected,markdown)
        self.assertNotIn('<script>',markdown)
        self.assertNotIn('![image]',markdown)

    def test_done_is_never_accepted_even_with_observed_message(self):
        self.submit()
        append_mutation_set(self.root,'event.add',{'event_id':'msg','evidence_status':'observed','summary':'claim'})
        out=record_report(self.root,'p',{'task_id':'t1','status':'done','summary':'done',
            'acceptance_results':[{'criterion':'real capture','result':'pass','evidence_event_ids':['msg']}]})
        self.assertEqual(out['task']['status'],'review')
        self.assertFalse(out['task']['accepted'])
        self.assertEqual(out['task']['reported_status'],'done')
    def test_done_without_checks_still_review(self):
        self.submit()
        out=record_report(self.root,'p',{'task_id':'t1','status':'done','summary':'claim'})
        self.assertEqual(out['task']['status'],'review')
        self.assertEqual(terminal_status(self.root,'p')['accepted_count'],0)
    def test_repeat_and_old_retry_do_not_rewind(self):
        self.assertTrue(self.submit()['added'])
        self.assertFalse(self.submit()['added'])
        first=self.report(continuation_count=0)
        self.report(continuation_count=1)
        before=verify_journal_set(self.root)['records']
        self.assertFalse(self.report(continuation_count=0)['added'])
        self.assertEqual(verify_journal_set(self.root)['records'],before)
        self.assertEqual(terminal_status(self.root,'p')['tasks'][0]['continuation_count'],1)
    def test_invalid_inputs_do_not_write(self):
        self.submit()
        base={'task_id':'t1','status':'running','summary':'new'}
        invalid=[dict(base,evidence_event_ids=['missing']),dict(base,continuation_count=3),
                 dict(base,continuation_count=True),dict(base,status='accepted'),dict(base,accepted=True),
                 dict(base,acceptance_results=[{'criterion':'real capture','result':'pass','evidence_event_ids':[]}]),
                 dict(base,status='blocked',blockers=[])]
        before=verify_journal_set(self.root)['records']
        for document in invalid:
            with self.assertRaises(ValueError):
                record_report(self.root,'p',document)
        self.assertEqual(verify_journal_set(self.root)['records'],before)
    def test_decreasing_counter_rejected(self):
        self.submit()
        self.report(continuation_count=2)
        with self.assertRaisesRegex(ValueError,'decrease'):
            self.report(continuation_count=1)
    def test_immutable_contract_and_wrong_project(self):
        self.submit()
        changed=dict(self.contract,title='Changed')
        with self.assertRaisesRegex(ValueError,'immutable'):
            submit_contract(self.root,'p',changed)
        with self.assertRaisesRegex(ValueError,'mismatch'):
            submit_contract(self.root,'other',self.contract)
    def test_redacts_secrets_before_writes(self):
        self.contract['purpose']='https://user:private-password@example.com'
        self.submit()
        for path in self.root.rglob('*'):
            if path.is_file():
                self.assertNotIn('private-password',path.read_text(encoding='utf-8'))
    def test_no_implicit_project_initialization(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,'journal required'):
                submit_contract(root,'p',self.contract)
            self.assertEqual([p for p in Path(root).iterdir() if p.name != '.terminal-control.lock'],[])
    def test_corrupt_journal_fails_closed(self):
        self.submit()
        path=self.root/'PROJECT_HISTORY.events.jsonl'
        path.write_text(path.read_text(encoding='utf-8').replace('Project','Changed'),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'integrity'):
            terminal_status(self.root,'p')
    def test_interrupted_source_append_recovers(self):
        def fail_event(root,op,payload):
            if op=='event.add':
                raise OSError('interrupted')
            return append_mutation_set(root,op,payload)
        with patch('terminal_control.append_mutation_set',side_effect=fail_event):
            with self.assertRaises(OSError):
                self.submit()
        self.assertTrue(self.submit()['added'])
        self.assertEqual(len(replay_journal_set(self.root)['sources']),1)
    def _concurrent_checkpoint_test(self, retry):
        from project_history_journal import ProjectLock as RealLock
        from project_history_hooks import checkpoint
        self.submit()
        root=self.root
        injected=False
        class InjectWriter:
            def __init__(self,path,**kwargs):
                self.path=path
                self.real=RealLock(path,**kwargs)
            def __enter__(self):
                nonlocal injected
                if self.path.name=='.project-history.snapshot.lock' and not injected:
                    injected=True
                    append_mutation_set(root,'event.add',{'event_id':'OTHER-WRITER','summary':'concurrent event'})
                    checkpoint(root)
                return self.real.__enter__()
            def __exit__(self,*args):
                return self.real.__exit__(*args)
        target='terminal_control.ProjectLock' if retry else 'project_history_hooks.ProjectLock'
        with patch(target,InjectWriter):
            self.submit() if retry else checkpoint(root)
        self.assertTrue(injected)
        self.assertEqual(json.loads((root/'PROJECT_MEMORY.json').read_text(encoding='utf-8')),replay_journal_set(root))

    def test_retry_cannot_overwrite_newer_completed_checkpoint(self):
        self._concurrent_checkpoint_test(True)

    def test_checkpoint_cannot_overwrite_newer_completed_checkpoint(self):
        self._concurrent_checkpoint_test(False)

    def test_checkpoint_repaired_on_repeat(self):
        self.submit()
        (self.root/'PROJECT_MEMORY.json').write_text('{}',encoding='utf-8')
        self.submit()
        self.assertEqual(json.loads((self.root/'PROJECT_MEMORY.json').read_text(encoding='utf-8')),replay_journal_set(self.root))

if __name__=='__main__':
    unittest.main()
