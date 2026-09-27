import tempfile
import unittest
from pathlib import Path

from evidence_import import import_sessions
from project_history_agent import evidence_date_key
from project_history_journal import replay_journal_set


class EvidenceDateTests(unittest.TestCase):
    def test_mixed_dates_import_replay_and_repeat(self):
        dates=[123.5,None,'2026-09-23','invalid','2026-09-23T12:00:00+03:00',0]
        doc={'sessions':[{'session_id':'s','messages':[
            {'id':str(i),'role':'assistant','text':'reported only','create_time':d}
            for i,d in enumerate(dates)]}]}
        with tempfile.TemporaryDirectory() as tmp:
            result=import_sessions(tmp,'p',doc,['s'])
            self.assertEqual(6,result['messages_added'])
            self.assertEqual(dates,[e['occurred_at'] for e in replay_journal_set(tmp)['events']])
            self.assertIn('- 0 ·', (Path(tmp)/'PROJECT_MEMORY.md').read_text(encoding="utf-8"))
            self.assertEqual(0,import_sessions(tmp,'p',doc,['s'])['messages_added'])

    def test_timezone_instants_sort_equally_without_mutating_input(self):
        self.assertEqual(evidence_date_key('2026-09-23T12:00:00+03:00'),
                         evidence_date_key('2026-09-23T09:00:00Z'))
        self.assertGreater(evidence_date_key(None),evidence_date_key(123.5))
