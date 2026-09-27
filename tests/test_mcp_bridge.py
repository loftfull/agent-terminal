import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from project_history_agent import empty_state, render_markdown
from project_history_journal import bootstrap_journal_from_state, redact_secrets
from project_history_mcp import HistoryReader


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        state = empty_state('test-project', 'History test', 'Preserve evidence')
        state['project']['constraints'] = ['Не выбирать только по числу звёзд', 'Keep original design']
        state['sources'] = [{'source_id': 'S1', 'locator': 'fixture:message-1'}]
        state['events'] = [{'event_id': 'E1', 'summary': 'INSTA implementation requested',
                            'event_type': 'request', 'source_ids': ['S1'], 'evidence_status': 'requested'}]
        bootstrap_journal_from_state(state, self.root / 'PROJECT_HISTORY.events.jsonl')
        self.reader = HistoryReader(self.root, 'test-project')

    def test_handoff_preserves_all_constraints_and_provenance(self):
        context = self.reader.context()
        self.assertEqual(2, len(context['critical_constraints']))
        for c in context['critical_constraints']:
            self.assertIn(c['text'], context['markdown'])
        result = self.reader.search('INSTA')
        self.assertEqual('requested', result['items'][0]['event']['evidence_status'])
        self.assertEqual('fixture:message-1', result['items'][0]['sources'][0]['locator'])
        self.assertEqual('E1', self.reader.event('E1')['event']['event_id'])

    def test_same_folder_wrong_project_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            HistoryReader(self.root, 'different-project').context()

    def test_tamper_is_rejected(self):
        journal = self.root / 'PROJECT_HISTORY.events.jsonl'
        journal.write_text(journal.read_text(encoding="utf-8").replace('Keep original design', 'Ignore original design'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, 'integrity failure'):
            self.reader.context()

    def test_reads_leave_journal_and_files_unchanged(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.reader.context(); self.reader.search('INSTA'); self.reader.event('E1')
        after = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_query_bounds_and_missing_event(self):
        for args in [('',0,20),('x',-1,20),('x',0,101),('x'*257,0,20)]:
            with self.assertRaises(ValueError): self.reader.search(*args)
        with self.assertRaises(ValueError): self.reader.event('../../outside')

    def test_duplicate_summaries_keep_distinct_evidence_ids(self):
        state, tip = self.reader.read()
        state['events'].append(dict(state['events'][0], event_id='E2', source_ids=['S2']))
        with patch.object(self.reader, 'read', return_value=(state, tip)):
            index = self.reader.context()['event_index']
        self.assertEqual(['E1','E2'], [e['event_id'] for e in index])
        self.assertEqual([['S1'],['S2']], [e['source_ids'] for e in index])

    def test_retry_changed_journal_tip(self):
        with patch('project_history_mcp.verify_journal_set', side_effect=[
            {'ok':True,'last_hash':x} for x in ['a','b','b','b']]):
            self.assertEqual('b', self.reader.context()['journal_tip'])
        with patch('project_history_mcp.verify_journal_set', side_effect=[
            {'ok':True,'last_hash':x} for x in ['a','b','c','d']]):
            with self.assertRaisesRegex(ValueError, 'changed during read'):
                self.reader.context()

    def test_secret_redaction_is_idempotent(self):
        raw = 'notes: https://alice:sample-password@example.invalid/p?token=sample-private-value&view=ok API_KEY="sample key with spaces"'
        clean = redact_secrets(raw)
        self.assertNotIn('sample', clean)
        self.assertIn('view=ok', clean)
        self.assertEqual(clean, redact_secrets(clean))


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_secret_redaction_over_stdio_all_tools(self):
        from mcp import Client, StdioServerParameters
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            state = empty_state('secret-fixture', 'Fixture', 'Privacy test')
            raw = 'notes: https://alice:sample-password@example.invalid/p?token=sample-private-value API_KEY=sample-key Authorization: Bearer sample-bearer-token'
            state['project']['constraints'] = [raw]
            state['sources'] = [{'source_id':'S1', 'locator':raw}]
            state['events'] = [{'event_id':'E1','summary':raw,'source_ids':['S1'],'evidence_status':'reported'}]
            # Simulate legacy journals which predate the strengthened scrubber.
            with patch('project_history_journal.redact_secrets', side_effect=lambda x:x):
                bootstrap_journal_from_state(state, Path(tmp)/'PROJECT_HISTORY.events.jsonl')
            params = StdioServerParameters(command=sys.executable, args=[str(root/'project_history_mcp.py'),'--root',tmp,'--project-id','secret-fixture'])
            async with Client(params, read_timeout_seconds=15) as client:
                for tool,args in [('get_project_context',{}),('search_evidence',{'query':'notes'}),('get_event',{'event_id':'E1'})]:
                    reply = await client.call_tool(tool,args)
                    self.assertFalse(reply.is_error)
                    serialized = json.dumps(reply.structured_content)
                    self.assertNotIn('sample-',serialized)
                    self.assertIn('REDACTED',serialized)

    async def test_real_stdio_client_retrieves_existing_FIX_journal(self):
        from mcp import Client, StdioServerParameters
        root = Path(__file__).resolve().parents[1]
        params = StdioServerParameters(command=sys.executable, args=[str(root/'project_history_mcp.py'), '--root', str(root), '--project-id', 'project-history-agent'])
        async with Client(params, read_timeout_seconds=15) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools.tools}
            self.assertEqual({'get_project_context','search_evidence','get_event','read_context_layer'}, names)
            reply = await client.call_tool('get_project_context', {})
            self.assertFalse(reply.is_error)
            data = reply.structured_content
            self.assertEqual('project-history-agent',data['project']['project_id'])
            self.assertTrue(data['critical_constraints'])
            self.assertIn('CRITICAL_CONSTRAINTS',data['markdown'])
            result = await client.call_tool('search_evidence',{'query':'v0.7','limit':1})
            self.assertFalse(result.is_error)
            self.assertEqual(1,len(result.structured_content['items']))
