import os,sys,time,subprocess,tempfile,unittest
from pathlib import Path
from history_adapters import InMemoryHistoryAdapter
from native_hook_runner import _handoff_context
from project_history_agent import empty_state,render_markdown
from project_history_hooks import session_start
from project_history_journal import ProjectLock,append_mutation,redact_secrets,replay_journal_set
from runtime_journal import append_mutation_set

class AuditRepairs(unittest.TestCase):
 def test_live_lock_age_and_crash(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'lock';ready=Path(d)/'ready'
   code="from project_history_journal import ProjectLock; from pathlib import Path; import sys,time\nwith ProjectLock(sys.argv[1]):\n Path(sys.argv[2]).touch()\n time.sleep(30)"
   child=subprocess.Popen([sys.executable,'-c',code,str(p),str(ready)])
   try:
    deadline=time.monotonic()+5
    while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
    self.assertTrue(ready.exists());os.utime(p,(time.time()-301,)*2)
    with self.assertRaises(TimeoutError):
     with ProjectLock(p,timeout=.03,poll_interval=.01):pass
   finally:child.kill();child.wait()
   with ProjectLock(p,timeout=.2):pass
   self.assertTrue(p.exists())
 def test_invalid_mutation_does_not_change_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);j=p/'PROJECT_HISTORY.events.jsonl'
   append_mutation(j,'project.patch',{'project_id':'p','name':'p'})
   before=j.read_bytes()
   for write in (lambda:append_mutation(j,'source.patch',{'source_id':'missing'}),lambda:append_mutation_set(p,'source.patch',{'source_id':'missing'})):
    with self.assertRaises(ValueError):write()
    self.assertEqual(j.read_bytes(),before);self.assertEqual(replay_journal_set(p)['project']['project_id'],'p')
   self.assertFalse((p/'PROJECT_HISTORY.segments').exists())
 def test_wrong_identity_has_no_writes(self):
  with tempfile.TemporaryDirectory() as d:
   a=InMemoryHistoryAdapter([]);session_start(d,{'chat_id':'a','project_id':'A'},a,project_id='A',name='A',goal='A')
   p=Path(d);before={str(x.relative_to(p)):x.read_bytes() for x in p.rglob('*.jsonl')}
   with self.assertRaises(ValueError):session_start(d,{'chat_id':'b','project_id':'B'},a,project_id='B',name='B',goal='B')
   self.assertEqual(before,{str(x.relative_to(p)):x.read_bytes() for x in p.rglob('*.jsonl')})
 def test_cookie_headers_redacted_before_append(self):
  with tempfile.TemporaryDirectory() as d:
   j=Path(d)/'PROJECT_HISTORY.events.jsonl'
   text='Cookie: session=synthetic-secret; other=also-secret\r\nSet-Cookie: auth=third-secret\nordinary text'
   append_mutation(j,'project.patch',{'project_id':'p','goal':text})
   for secret in ('synthetic-secret','also-secret','third-secret'):self.assertNotIn(secret,j.read_text())
   self.assertIn('ordinary text',redact_secrets(text))
 def test_long_constraints_survive(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);s=empty_state('p','p','ordinary goal\n## 1. User-supplied heading');s['project']['constraints']=['A'*4000,'CRITICAL_LAST_CONSTRAINT']
   (p/'PROJECT_MEMORY.md').write_text(render_markdown(s),encoding='utf-8')
   self.assertIn('CRITICAL_LAST_CONSTRAINT',_handoff_context(p))
