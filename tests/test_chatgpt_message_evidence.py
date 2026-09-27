import json
import tempfile
import unittest
from pathlib import Path

from history_adapters import ChatGPTExportHistoryAdapter


class ChatGPTMessageEvidenceTests(unittest.TestCase):
    def parse(self, mapping, **extra):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'conversations.json'
            path.write_text(json.dumps([{'id': 'chat1', 'mapping': mapping, **extra}]))
            return ChatGPTExportHistoryAdapter(path).inspect('chat1')

    def node(self, ident, parent, text, role='assistant', **extra):
        return {'parent': parent, 'children': [], 'message': {'id': ident,
                'author': {'role': role}, 'content': {'parts': [text]}, **extra}}

    def test_alternatives_preserved_not_flattened_as_sequence(self):
        mapping = {'root': self.node('m0', None, 'request', 'user'),
                   'old': self.node('m1', 'root', 'rejected'),
                   'new': self.node('m2', 'root', 'accepted')}
        mapping['root']['children'] = ['old', 'new']
        result = self.parse(mapping, current_node='new')
        self.assertEqual(result['active_node_ids'], ['root', 'new'])
        self.assertEqual(result['text'], 'request\naccepted')
        self.assertEqual([x['on_active_path'] for x in result['messages']], [True, False, True])
        self.assertEqual(result['messages'][1]['parent'], 'root')
        self.assertNotIn('parent_chat_id', result)

    def test_metadata_and_timestamps_preserved(self):
        meta = {'model_slug': 'model-a', 'default_model_slug': 'model-b', 'nested': {'automation_id': 'a1'}}
        result = self.parse({'a': self.node('message-a', None, 'text', metadata=meta, create_time='broken'),
                             'b': self.node('message-b', 'a', 'next')}, current_node='b')
        self.assertEqual(result['messages'][0]['metadata'], meta)
        self.assertEqual(result['messages'][0]['create_time'], 'broken')
        self.assertIsNone(result['messages'][1]['create_time'])
        self.assertEqual(result['messages'][0]['id'], 'message-a')

    def test_missing_current_node_means_unknown_not_active(self):
        result = self.parse({'a': self.node('m', None, 'text')})
        self.assertIsNone(result['messages'][0]['on_active_path'])
        self.assertFalse(result['coverage']['active_path_known'])
        self.assertEqual(result['coverage']['text_scope'], 'all_alternatives_unordered')
        self.assertTrue(result['coverage']['warnings'])

    def test_cycle_and_dangling_paths_terminate_with_unknown(self):
        for mapping in ({'a': self.node('m', 'a', 'text')},
                        {'a': self.node('m', 'missing', 'text')},
                        {'a': {'message': {'id': 'm'}}}):
            with self.subTest(mapping=mapping):
                result = self.parse(mapping, current_node='a')
                self.assertFalse(result['coverage']['active_path_known'])
                self.assertEqual(result['active_node_ids'], [])
                self.assertIsNone(result['messages'][0]['on_active_path'])

    def test_graph_order_overrides_timestamps_and_mapping_order(self):
        result = self.parse({'b': self.node('m2', 'a', 'second', create_time=-10),
                             'a': self.node('m1', None, 'first', create_time=20)}, current_node='b')
        self.assertEqual(result['text'], 'first\nsecond')
        self.assertEqual(result['active_node_ids'], ['a', 'b'])

    def test_malformed_node_and_dangling_children_covered(self):
        node = self.node('m', None, 'text')
        node['children'] = ['absent']
        result = self.parse({'a': node, 'bad': 3}, current_node='a')
        self.assertIn('dangling_children:a', result['coverage']['warnings'])
        self.assertIn('malformed_node:bad', result['coverage']['warnings'])

    def test_search_finds_alternative_without_changing_active_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'conversations.json'
            path.write_text(json.dumps([{'id': 'chat1', 'current_node': 'a', 'mapping': {
                'a': self.node('m1', None, 'active'),
                'b': self.node('m2', None, 'alternative needle')}}]))
            hits = ChatGPTExportHistoryAdapter(path).search('conversations', 'needle')
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['text'], 'active')

    def test_nontext_evidence_and_malformed_metadata_retained(self):
        node = self.node('m', None, 'text', metadata=['unexpected'])
        node['message']['content']['parts'].append({'asset_pointer': 'asset-123'})
        result = self.parse({'a': node}, current_node='a')
        message = result['messages'][0]
        self.assertEqual(message['metadata'], {})
        self.assertEqual(message['raw_metadata'], ['unexpected'])
        self.assertEqual(message['content'], node['message']['content'])
        self.assertEqual(message['author'], {'role': 'assistant'})
        self.assertIn('malformed_metadata:a', result['coverage']['warnings'])

    def test_adapter_import_replay_preserves_extra_raw_fields(self):
        from evidence_import import import_sessions
        from project_history_journal import replay_journal_set
        node = self.node('m1', 'root', 'hello', update_time=123, recipient='all',
                         status='finished_successfully', metadata={'model_slug': 'model-x'})
        node['weight'] = 3
        root = {'id': 'root', 'parent': None, 'children': ['a'], 'message': None,
                'custom_root_metadata': {'origin': 'export'}}
        session = self.parse({'root': root, 'a': node}, current_node='a',
                             update_time=456, custom_session_field={'flag': True})
        with tempfile.TemporaryDirectory() as folder:
            import_sessions(folder, 'project-test', {'sessions': [session]}, ['chat1'])
            state = replay_journal_set(Path(folder))
        source = next(x for x in state['sources'] if x.get('kind') == 'normalized_message')
        self.assertEqual(source['message']['raw_message'], node['message'])
        self.assertEqual(source['message']['node_metadata']['weight'], 3)
        metadata = source['session_metadata']
        self.assertEqual(metadata['raw_session']['update_time'], 456)
        self.assertEqual(metadata['raw_session']['custom_session_field'], {'flag': True})
        self.assertEqual(metadata['node_index']['root']['custom_root_metadata'], {'origin': 'export'})
        self.assertIn('external bytes not fetched', metadata['coverage']['attachments'])


if __name__ == '__main__':
    unittest.main()
