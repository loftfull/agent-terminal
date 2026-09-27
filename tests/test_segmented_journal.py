import json
import tempfile
import unittest
from pathlib import Path

from project_history_journal import (
    append_mutation,
    journal_paths,
    replay_journal_set,
    verify_journal_set,
)


class SegmentedJournalTests(unittest.TestCase):
    def test_segment_chain_replays_as_one_history(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / 'PROJECT_HISTORY.events.jsonl'
            append_mutation(base, 'project.patch', {'project_id': 'p', 'name': 'P', 'goal': 'g'}, timestamp='2026-09-16T00:00:00+00:00')
            append_mutation(base, 'source.add', {'source_id': 'S1', 'name': 'one', 'locator': 'x'}, timestamp='2026-09-16T00:00:01+00:00')

            base_records = [json.loads(x) for x in base.read_text(encoding='utf-8').splitlines() if x.strip()]
            prev_hash = base_records[-1]['hash']

            seg_dir = root / 'PROJECT_HISTORY.segments'
            seg_dir.mkdir()
            seg = seg_dir / '0002.jsonl'
            record_without_hash = {
                'schema': 'project-history-journal/v0.5',
                'journal_id': 'J-000003',
                'timestamp': '2026-09-16T00:00:02+00:00',
                'op': 'source.add',
                'payload': {'source_id': 'S2', 'name': 'two', 'locator': 'y'},
                'prev_hash': prev_hash,
            }
            from project_history_journal import _record_hash
            record = dict(record_without_hash)
            record['hash'] = _record_hash(record_without_hash)
            seg.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')

            self.assertEqual([p.name for p in journal_paths(root)], ['PROJECT_HISTORY.events.jsonl', '0002.jsonl'])
            verification = verify_journal_set(root)
            self.assertTrue(verification['ok'], verification)
            self.assertEqual(verification['records'], 3)
            state = replay_journal_set(root)
            self.assertEqual([s['source_id'] for s in state['sources']], ['S1', 'S2'])

    def test_segment_chain_detects_broken_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / 'PROJECT_HISTORY.events.jsonl'
            append_mutation(base, 'project.patch', {'project_id': 'p', 'name': 'P', 'goal': 'g'}, timestamp='2026-09-16T00:00:00+00:00')
            seg_dir = root / 'PROJECT_HISTORY.segments'
            seg_dir.mkdir()
            seg = seg_dir / '0002.jsonl'
            bad = {
                'schema': 'project-history-journal/v0.5',
                'journal_id': 'J-000002',
                'timestamp': '2026-09-16T00:00:01+00:00',
                'op': 'source.add',
                'payload': {'source_id': 'S2', 'name': 'two', 'locator': 'y'},
                'prev_hash': 'wrong',
                'hash': 'wrong',
            }
            seg.write_text(json.dumps(bad) + '\n', encoding='utf-8')
            verification = verify_journal_set(root)
            self.assertFalse(verification['ok'])
            codes = {x['code'] for x in verification['issues']}
            self.assertIn('PREV_HASH_MISMATCH', codes)
            self.assertIn('HASH_MISMATCH', codes)


if __name__ == '__main__':
    unittest.main()
