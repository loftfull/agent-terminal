import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state,replay_journal_set,journal_paths,atomic_write_text
from runtime_journal import append_mutation_batch,append_mutation_set

class AtomicBatchTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
  bootstrap_journal_from_state(empty_state('p','p','p'),self.root/'PROJECT_HISTORY.events.jsonl')
  self.batch=[('event.add',{'event_id':'E','source_ids':['S'],'evidence_status':'reported','summary':'fixture'}),('source.add',{'source_id':'S','locator':'fixture'})]
 def tearDown(self):self.t.cleanup()
 def test_dangling_rejected_and_forward_ref_batch_accepted(self):
  before=[p.read_bytes() for p in journal_paths(self.root)]
  with self.assertRaises(ValueError):append_mutation_set(self.root,*self.batch[0])
  self.assertEqual(before,[p.read_bytes() for p in journal_paths(self.root)])
  append_mutation_batch(self.root,self.batch)
  self.assertEqual(len(replay_journal_set(self.root)['events']),1)
 def test_failure_before_rename_has_no_partial_batch(self):
  before=[p.read_bytes() for p in journal_paths(self.root)]
  with patch('project_history_journal.os.replace',side_effect=OSError('failure before rename')):
   with self.assertRaises(OSError):append_mutation_batch(self.root,self.batch)
  self.assertEqual(before,[p.read_bytes() for p in journal_paths(self.root)])
  append_mutation_batch(self.root,self.batch)
  self.assertEqual(len(replay_journal_set(self.root)['sources']),1)
 def test_failure_after_publication_is_complete_and_reconciliable(self):
  def publish_then_fail(path,text):
   atomic_write_text(path,text)
   if str(path).endswith('.jsonl'):raise OSError('lost acknowledgement')
  with patch('runtime_journal.atomic_write_text',side_effect=publish_then_fail):
   with self.assertRaises(OSError):append_mutation_batch(self.root,self.batch)
  state=replay_journal_set(self.root)
  self.assertEqual((len(state['sources']),len(state['events'])),(1,1))

 def test_numeric_segment_rollover_and_batch_reuses_segment(self):
  from runtime_journal import close_runtime_segment
  from project_history_journal import verify_journal_set
  append_mutation_batch(self.root,self.batch)
  segment=journal_paths(self.root)[-1]
  close_runtime_segment(self.root)
  segment.rename(segment.with_name('9999-runtime.jsonl'))
  append_mutation_set(self.root,'handoff.patch',{'next_step':'next'})
  self.assertTrue(verify_journal_set(self.root)['ok'])
  count=len(journal_paths(self.root))
  append_mutation_set(self.root,'handoff.patch',{'next_step':'later'})
  self.assertEqual(len(journal_paths(self.root)),count)
