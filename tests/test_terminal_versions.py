import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state,replay_journal_set
from runtime_journal import append_mutation_set
from project_history_hooks import checkpoint
from terminal_versions import create,restore,attach_screenshot,screenshot_view,versions,git
from terminal_metrics import metrics
from terminal_control import submit_contract,record_report

class VersionTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.base=Path(self.t.name)
        self.repo=self.base/'code';self.repo.mkdir();self.mem=self.base/'memory';self.mem.mkdir()
        git(self.repo,'init');git(self.repo,'config','user.email','fixture@example.invalid');git(self.repo,'config','user.name','Fixture')
        (self.repo/'app.txt').write_text('version one',encoding='utf-8');git(self.repo,'add','.');git(self.repo,'commit','-m','one')
        bootstrap_journal_from_state(empty_state('p','Test','History'),self.mem/'PROJECT_HISTORY.events.jsonl')
        append_mutation_set(self.mem,'source.add',{'source_id':'S1','locator':'fixture'})
        append_mutation_set(self.mem,'event.add',{'event_id':'E1','event_type':'test','summary':'Synthetic test only','source_ids':['S1'],'evidence_status':'observed'})
        checkpoint(self.mem)
    def tearDown(self):self.t.cleanup()
    def create(self,label='v0.8.1-candidate.1'):
        return create(self.mem,'p',self.repo,label,'Version fixture',['E1'])
    def test_restore_old_code_preserves_current_dirty_work_and_journal(self):
        v=self.create();(self.repo/'app.txt').write_text('version two',encoding='utf-8');git(self.repo,'add','.');git(self.repo,'commit','-m','two');head=git(self.repo,'rev-parse','HEAD')
        (self.repo/'app.txt').write_text('unfinished new work',encoding='utf-8')
        receipt=restore(self.mem,'p',v['version_id'],self.base/'old')
        self.assertEqual((self.base/'old/app.txt').read_text(),'version one')
        self.assertEqual((self.repo/'app.txt').read_text(),'unfinished new work')
        self.assertEqual(git(self.repo,'rev-parse','HEAD'),head)
        self.assertEqual(receipt['memory_root'],str(self.mem.resolve()))
        self.assertTrue(any(e['event_id']=='E1' for e in replay_journal_set(self.mem)['events']))
        self.assertEqual(json.loads((self.base/'old/RESTORE_CONTEXT.json').read_text())['status'],'restored_unexecuted')
    def test_dirty_duplicate_unknown_evidence_and_existing_destination_rejected(self):
        (self.repo/'untracked').write_text('keep')
        with self.assertRaisesRegex(ValueError,'Commit'):self.create()
        (self.repo/'untracked').unlink();v=self.create()
        with self.assertRaisesRegex(ValueError,'already'):self.create()
        with self.assertRaisesRegex(ValueError,'Known'):create(self.mem,'p',self.repo,'v0.8.1-candidate.2','x',['missing'])
        with self.assertRaisesRegex(ValueError,'new'):restore(self.mem,'p',v['version_id'],self.repo)
        self.assertEqual((self.repo/'app.txt').read_text(),'version one')
    def test_nested_restore_and_mutated_ref_rejected(self):
        v=self.create()
        with self.assertRaisesRegex(ValueError,'outside'):restore(self.mem,'p',v['version_id'],self.repo/'nested')
        (self.repo/'app.txt').write_text('two');git(self.repo,'add','.');git(self.repo,'commit','-m','two')
        git(self.repo,'update-ref',v['git_ref'],git(self.repo,'rev-parse','HEAD'))
        with self.assertRaisesRegex(ValueError,'ref changed'):restore(self.mem,'p',v['version_id'],self.base/'old')
    def test_screenshot_missing_tampered_and_reported_provenance(self):
        from PIL import Image
        v=self.create();self.assertEqual(screenshot_view(self.mem,replay_journal_set(self.mem),v)['status'],'NOT_CAPTURED')
        image=self.base/'fixture.png';Image.new('RGB',(10,12),'white').save(image)
        with self.assertRaisesRegex(ValueError,'SHA'):attach_screenshot(self.mem,'p',v['version_id'],image,'synthetic fixture','bad')
        r=attach_screenshot(self.mem,'p',v['version_id'],image,'synthetic fixture, not application screenshot',v['commit_sha'])
        self.assertEqual(r['build_link'],'reported');s=replay_journal_set(self.mem);v=versions(s)[0]
        self.assertTrue(screenshot_view(self.mem,s,v)['data_uri'].startswith('data:image/png;'))
        Path(s['visuals'][0]['uri']).write_bytes(b'changed')
        self.assertEqual(screenshot_view(self.mem,s,v)['status'],'MISSING_OR_CHANGED')
    def test_invalid_version_label_and_project(self):
        with self.assertRaises(ValueError):create(self.mem,'p',self.repo,'../../escape','x',['E1'])
        with self.assertRaises(ValueError):create(self.mem,'wrong',self.repo,'v0.8.1-candidate.1','x',['E1'])
    def test_metrics_reported_pass_never_accepted_or_chat_connected(self):
        submit_contract(self.mem,'p',{'task_id':'t','title':'t','purpose':'p','deliverables':['d'],'acceptance':['a','b'],'constraints':[],'stop_conditions':['s']})
        record_report(self.mem,'p',{'task_id':'t','status':'done','summary':'claimed done','acceptance_results':[{'criterion':'a','result':'pass','evidence_event_ids':['E1']}]})
        m=metrics(replay_journal_set(self.mem));self.assertEqual(m['criteria'],{'total':2,'reported_pass':1,'reported_fail':0,'not_run':1,'accepted':0});self.assertIsNone(m['project_percent']);self.assertEqual(m['chat']['status'],'not_connected')
        self.assertEqual(metrics(empty_state('x','x','x'))['criteria']['total'],0)

    def test_browser_observation_is_historical_and_never_subscription(self):
        s=empty_state('x','x','x');s['sources']=[{'source_id':'S'}]
        self.assertIsNone(metrics(s)['chat']['last_browser_observation'])
        s['events']=[{'event_id':'B1','event_type':'chat_access_observation',
            'evidence_status':'observed','source_ids':['S'],'observed_at':'2026-09-24T09:33:22Z',
            'browser_observation':{'result':'manual_read','sample_messages':28}}]
        m=metrics(s)['chat'];self.assertEqual(m['status'],'not_connected')
        self.assertFalse(m['continuous_ingestion'])
        self.assertEqual(m['last_browser_observation']['evidence_status'],'observed')
        s['events'].append(dict(s['events'][0],event_id='B2',evidence_status='reported'))
        self.assertEqual(metrics(s)['chat']['last_browser_observation']['evidence_status'],'reported')
        s['events'].append(dict(s['events'][0],event_id='B3',source_ids=['missing']))
        self.assertEqual(metrics(s)['chat']['last_browser_observation']['evidence_status'],'unknown')
        s['events'].append(dict(s['events'][0],event_id='B4',browser_observation={'result':'failed'}))
        self.assertEqual(metrics(s)['chat']['last_browser_observation']['result'],'failed')


    def test_restore_receipt_collision_refuses_without_creating_worktree(self):
        (self.repo/'restore_context.json').write_text('original historical file')
        git(self.repo,'add','.');git(self.repo,'commit','-m','reserved name')
        v=self.create()
        with self.assertRaisesRegex(ValueError,'collision'):restore(self.mem,'p',v['version_id'],self.base/'old')
        self.assertFalse((self.base/'old').exists())
        self.assertEqual((self.repo/'restore_context.json').read_text(),'original historical file')
    def test_filters_refused_and_fsmonitor_disabled(self):
        git(self.repo,'config','core.fsmonitor','nonexistent-fsmonitor-command')
        v=self.create()  # status must not attempt this executable
        git(self.repo,'config','filter.probe.smudge','nonexistent-smudge-command')
        with self.assertRaisesRegex(ValueError,'filters'):restore(self.mem,'p',v['version_id'],self.base/'old')
        with self.assertRaisesRegex(ValueError,'filters'):self.create('v0.8.1-candidate.2')
        self.assertFalse((self.base/'old').exists())
    def test_failed_journal_write_cleans_only_own_orphan_ref(self):
        from unittest.mock import patch
        with patch('terminal_versions.append_mutation_set',side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):self.create()
        self.assertEqual(git(self.repo,'for-each-ref','--format=%(refname)','refs/fix-checkpoints'),'')
        self.create()
    def test_special_and_oversized_images_rejected(self):
        from terminal_versions import bounded_image_bytes
        import os
        p=self.base/'oversized';p.write_bytes(b'x'*(5*1024*1024+1))
        with self.assertRaises(ValueError):bounded_image_bytes(p)
        with self.assertRaises(ValueError):bounded_image_bytes(self.repo)
        if hasattr(os,'mkfifo'):
            pipe=self.base/'pipe';os.mkfifo(pipe)
            with self.assertRaises(ValueError):bounded_image_bytes(pipe)

if __name__=='__main__':unittest.main()
