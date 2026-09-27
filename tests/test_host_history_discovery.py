import json
import tempfile
import unittest
from pathlib import Path

from host_history_discovery import HostHistoryDiscovery


class HostHistoryDiscoveryTests(unittest.TestCase):
    def test_default_home_detects_bounded_claude_and_codex_roots(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            claude = home / '.claude' / 'projects' / 'demo'
            claude.mkdir(parents=True)
            (claude / 'session.jsonl').write_text(json.dumps({'sessionId': 'claude-1', 'cwd': '/work/demo', 'message': {'role': 'user', 'content': 'fix auth'}}) + '\n', encoding='utf-8')
            codex = home / '.codex' / 'sessions' / '2026' / '09' / '16'
            codex.mkdir(parents=True)
            (codex / 'rollout-1.jsonl').write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 'codex-1', 'cwd': '/work/demo'}}) + '\n', encoding='utf-8')
            result = HostHistoryDiscovery(home=home, env={}).discover()
            by_provider = {x['provider']: x for x in result['sources']}
            self.assertEqual('available', by_provider['claude-code']['status'])
            self.assertEqual('available', by_provider['codex']['status'])
            self.assertEqual('not_configured', by_provider['chatgpt-export']['status'])
            self.assertEqual([str(home / '.claude' / 'projects')], by_provider['claude-code']['roots'])
            self.assertIn(str(home / '.codex' / 'sessions'), by_provider['codex']['roots'])
            self.assertNotIn(str(home), by_provider['codex']['roots'])

    def test_codex_home_override_is_preferred_over_default(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); home = base / 'home'; custom = base / 'custom-codex'
            (home / '.codex' / 'sessions').mkdir(parents=True); (custom / 'sessions').mkdir(parents=True)
            source = next(x for x in HostHistoryDiscovery(home=home, env={'CODEX_HOME': str(custom)}).discover()['sources'] if x['provider'] == 'codex')
            self.assertEqual([str(custom / 'sessions')], source['roots'])

    def test_chatgpt_is_never_auto_discovered_without_explicit_export(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td); (home / 'Downloads').mkdir(); (home / 'Downloads' / 'conversations.json').write_text('[]', encoding='utf-8')
            source = next(x for x in HostHistoryDiscovery(home=home, env={}).discover()['sources'] if x['provider'] == 'chatgpt-export')
            self.assertEqual('not_configured', source['status']); self.assertEqual([], source['roots'])

    def test_explicit_chatgpt_export_is_available_and_searchable(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td); export = home / 'export' / 'conversations.json'; export.parent.mkdir()
            export.write_text(json.dumps([{'id': 'chat-1', 'title': 'Agent project', 'mapping': {'n1': {'message': {'create_time': 1, 'content': {'parts': ['continue agent project']}}}}}]), encoding='utf-8')
            discovery = HostHistoryDiscovery(home=home, env={'CHATGPT_CONVERSATIONS_JSON': str(export)})
            result = discovery.discover(); source = next(x for x in result['sources'] if x['provider'] == 'chatgpt-export')
            self.assertEqual('available', source['status']); self.assertEqual('chat-1', discovery.build_adapter(result).search('conversations', 'agent', limit=5)[0]['session_id'])

    def test_missing_explicit_override_is_reported_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td); missing = home / 'missing-claude'
            source = next(x for x in HostHistoryDiscovery(home=home, env={'CLAUDE_HISTORY_ROOT': str(missing)}).discover()['sources'] if x['provider'] == 'claude-code')
            self.assertEqual('missing', source['status']); self.assertTrue(source['explicit']); self.assertEqual([str(missing)], source['roots'])

    def test_build_adapter_returns_none_when_no_sources_available(self):
        with tempfile.TemporaryDirectory() as td:
            discovery = HostHistoryDiscovery(home=Path(td), env={})
            self.assertIsNone(discovery.build_adapter(discovery.discover()))

    def test_discovery_report_has_no_lineage_claim(self):
        with tempfile.TemporaryDirectory() as td:
            result = HostHistoryDiscovery(home=Path(td), env={}).discover()
            self.assertNotIn('continuation', result); self.assertNotIn('parent_chat_id', result); self.assertEqual('candidate-discovery-only', result['authority'])


if __name__ == '__main__':
    unittest.main()
