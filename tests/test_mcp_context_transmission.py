"""Synthetic source fixtures, real journal/import and separate stdio MCP process."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evidence_import import import_sessions
from project_history_mcp import HistoryReader
from runtime_journal import append_mutation_batch
from terminal_context import read_layer


class Fixture:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project_id = 'synthetic-transmission'
        self.document = {'sessions': [
            {'session_id': 'original', 'messages': [
                {'id': 'a', 'role': 'user', 'text': 'Хранить историю в SQLite.'}]},
            {'session_id': 'continuation', 'parent_session_id': 'original', 'messages': [
                {'id': 'b', 'role': 'user', 'text': 'Отменяю прежнее решение: использовать JSONL.'}]}]}
        import_sessions(self.root, self.project_id, self.document, ['original', 'continuation'])
        state, _ = HistoryReader(self.root, self.project_id).read()
        messages = {e['session_id']: e for e in state['events']}
        self.constraints = ['Не менять смысл источников', 'Never infer lineage from topic'] + ['Rule ' + str(i) for i in range(8)]
        # Explicit curated classification; no inference from message recency.
        self.decisions = [
            {'event_id': 'decision-original', 'event_type': 'decision',
             'summary': 'Исходное решение', 'text': self.document['sessions'][0]['messages'][0]['text'],
             'source_ids': messages['original']['source_ids'], 'evidence_status': 'reported'},
            {'event_id': 'decision-replacement', 'event_type': 'decision',
             'summary': 'Явная отмена', 'text': self.document['sessions'][1]['messages'][0]['text'],
             'source_ids': messages['continuation']['source_ids'], 'evidence_status': 'reported',
             'supersedes': 'decision-original'}]
        append_mutation_batch(self.root, [('project.patch', {'constraints': self.constraints})] +
                              [('event.add', e) for e in self.decisions])

    def mutate(self):
        append_mutation_batch(self.root, [('project.patch', {'description': 'Concurrent update'})])


class ConsistencyTests(Fixture, unittest.TestCase):
    def test_guard_preserves_legacy_shape_and_receipt(self):
        legacy = read_layer(self.root, self.project_id, 'L2', 0, 1)
        pinned = read_layer(self.root, self.project_id, 'L2', 0, 1,
                            expected_journal_tip=legacy['journal_tip'])
        self.assertEqual(legacy, pinned)
        receipt = pinned.pop('retrieval_receipt')
        digest = hashlib.sha256(json.dumps(pinned, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(receipt['payload_sha256'], digest)
        self.assertEqual(pinned['constraints'], self.constraints)
        self.mutate()
        for level in ('L0', 'L1', 'L2'):
            changed = read_layer(self.root, self.project_id, level, 1, 1,
                                 expected_journal_tip=legacy['journal_tip'])
            self.assertEqual(changed['status'], 'STATE_CHANGED')
            self.assertNotIn('items', changed)
            self.assertNotIn('sources', changed)
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            read_layer(self.root, 'other', expected_journal_tip=legacy['journal_tip'])

    def test_bad_tokens_and_bounds_fail(self):
        for token in ('', 'x'*64, 1, True, 'a'*63, 'A'*64):
            with self.subTest(token=token), self.assertRaises(ValueError):
                read_layer(self.root, self.project_id, expected_journal_tip=token)
        for offset, limit in ((-1,1),(0,0),(True,1),(0,101)):
            with self.assertRaises(ValueError):
                read_layer(self.root, self.project_id, 'L2', offset, limit)

    def test_response_uses_same_state_as_tip_even_if_writer_runs_after_read(self):
        state, tip = HistoryReader(self.root, self.project_id).read()
        def read_then_write(reader):
            self.mutate()
            return state, tip
        with patch.object(HistoryReader, 'read', read_then_write):
            page = read_layer(self.root, self.project_id, 'L2', expected_journal_tip=tip)
        self.assertEqual(page['journal_tip'], tip)
        self.assertEqual(page['items'], state['events'])
        self.assertEqual(read_layer(self.root, self.project_id, expected_journal_tip=tip)['status'], 'STATE_CHANGED')

    def test_vault_argument_is_not_dropped(self):
        state, tip = HistoryReader(self.root, self.project_id).read()
        with patch('terminal_context.HistoryReader') as reader:
            reader.return_value.read.return_value = (state, tip)
            read_layer(self.root, self.project_id, 'L2', 0, 1, 'chosen-vault', expected_journal_tip=tip)
            reader.assert_called_once_with(self.root, self.project_id, vault='chosen-vault')


class ProtocolTransmissionTests(Fixture, unittest.IsolatedAsyncioTestCase):
    async def test_real_process_transmission_and_changed_state(self):
        from mcp import Client, StdioServerParameters
        expected, tip = HistoryReader(self.root, self.project_id).read()
        repeat = import_sessions(self.root, self.project_id, self.document, ['original', 'continuation'])
        self.assertEqual(repeat['messages_added'], 0)
        self.assertEqual(HistoryReader(self.root, self.project_id).read()[1], tip)
        params = StdioServerParameters(command=sys.executable, args=[
            str(Path(__file__).resolve().parents[1] / 'project_history_mcp.py'),
            '--root', str(self.root), '--project-id', self.project_id])
        async with Client(params, read_timeout_seconds=15) as client:
            async def call(**kwargs):
                reply = await client.call_tool('read_context_layer', kwargs)
                self.assertFalse(reply.is_error)
                return reply.structured_content
            l0 = await call()
            self.assertEqual(l0['constraints'], self.constraints)
            self.assertEqual(l0['journal_tip'], tip)
            for level in ('L1', 'L2'):
                events, sources, offset = [], {}, 0
                while True:
                    page = await call(level=level, offset=offset, limit=1, expected_journal_tip=tip)
                    self.assertEqual(page['journal_tip'], tip)
                    self.assertEqual(page['constraints'], self.constraints)
                    receipt = page.pop('retrieval_receipt')
                    self.assertEqual(receipt['payload_sha256'], hashlib.sha256(
                        json.dumps(page, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
                    events.extend(page['items'])
                    sources.update({s['source_id']: s for s in page.get('sources', [])})
                    offset = page['next_offset']
                    if offset is None:
                        break
                self.assertEqual([e['event_id'] for e in events], [e['event_id'] for e in expected['events']])
                if level == 'L2':
                    self.assertEqual(events, expected['events'])
                    refs = {s for e in events for s in e['source_ids']}
                    self.assertEqual(sources, {s['source_id']: s for s in expected['sources'] if s['source_id'] in refs})
                    by_id = {e['event_id']: e for e in events}
                    for decision in self.decisions:
                        for key, value in decision.items():
                            self.assertEqual(by_id[decision['event_id']][key], value)
            self.mutate()  # Parent process writes while child MCP remains open.
            changed = await call(level='L2', offset=1, limit=1, expected_journal_tip=tip)
            self.assertEqual(changed['status'], 'STATE_CHANGED')
            self.assertNotIn('items', changed)
            fresh = await call(level='L2', offset=0, limit=1)
            self.assertNotEqual(fresh['journal_tip'], tip)
            denied = await client.call_tool('read_context_layer', {'project_id': 'other'})
            # SDK may ignore unknown arguments; they must never rebind the configured project.
            self.assertFalse(denied.is_error)
            self.assertEqual(denied.structured_content['project_id'], self.project_id)
            report = {'status': 'PASS', 'fixture': 'synthetic', 'transport': 'real stdio subprocess',
                      'checks': ['ids', 'full L2 payloads', 'constraints', 'sources', 'supersession',
                                 'receipt hashes', 'repeat import', 'state change', 'project scope'],
                      'omissions': ['Original account archives not supplied', 'Continuous ingestion not tested', 'A6 remains open']}
            print(json.dumps({'mcp_transmission_audit': report}, ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
