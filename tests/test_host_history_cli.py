import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HostHistoryCliTests(unittest.TestCase):
    def setUp(self):
        # These tests exercise temporary fixtures, never the invoking host's history.
        self.fixture_env = {k: v for k, v in os.environ.items() if k not in
                            {'CODEX_HOME', 'CLAUDE_HISTORY_ROOT', 'CHATGPT_CONVERSATIONS_JSON'}}

    def test_discover_history_cli_reports_bounded_sources(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / '.codex' / 'sessions').mkdir(parents=True)
            proc = subprocess.run([sys.executable, str(ROOT / 'host_history_cli.py'), 'discover', '--home', str(home)], cwd=ROOT, text=True, capture_output=True, env=self.fixture_env)
            self.assertEqual(0, proc.returncode, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload['bounded'])
            self.assertEqual('candidate-discovery-only', payload['authority'])
            self.assertEqual('available', next(x for x in payload['sources'] if x['provider'] == 'codex')['status'])

    def test_history_search_cli_uses_discovered_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            session_dir = home / '.claude' / 'projects' / 'demo'
            session_dir.mkdir(parents=True)
            (session_dir / 'session.jsonl').write_text(json.dumps({'sessionId':'claude-cli-1','cwd':'/repo/demo','message':{'role':'user','content':'repair payment flow'}}) + '\n', encoding='utf-8')
            proc = subprocess.run([sys.executable, str(ROOT / 'host_history_cli.py'), 'search', 'payment', '--home', str(home), '--scope', 'conversations'], cwd=ROOT, text=True, capture_output=True, env=self.fixture_env)
            self.assertEqual(0, proc.returncode, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(1, payload['count'])
            self.assertEqual('claude-cli-1', payload['results'][0]['session_id'])
            self.assertEqual('candidate-discovery-only', payload['authority'])

    def test_history_search_cli_fails_cleanly_when_no_source_available(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run([sys.executable, str(ROOT / 'host_history_cli.py'), 'search', 'anything', '--home', td], cwd=ROOT, text=True, capture_output=True, env=self.fixture_env)
            self.assertEqual(2, proc.returncode)
            self.assertEqual('NO_HISTORY_SOURCE', json.loads(proc.stdout)['error'])

    def test_history_search_cli_ranks_candidates_when_current_context_is_supplied(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            same = home / '.claude' / 'projects' / 'same'
            other = home / '.claude' / 'projects' / 'other'
            same.mkdir(parents=True)
            other.mkdir(parents=True)
            (same / 'a.jsonl').write_text(json.dumps({'sessionId':'same-path','cwd':'/repo/demo','message':{'role':'user','content':'payment investigation'}}) + '\n', encoding='utf-8')
            (other / 'b.jsonl').write_text(json.dumps({'sessionId':'topic-only','cwd':'/repo/other','message':{'role':'user','content':'payment investigation'}}) + '\n', encoding='utf-8')
            current = home / 'current.json'
            current.write_text(json.dumps({'chat_id':'current','title':'payment work','text':'payment investigation','paths':['/repo/demo']}), encoding='utf-8')
            proc = subprocess.run([sys.executable, str(ROOT / 'host_history_cli.py'), 'search', 'payment', '--home', str(home), '--scope', 'conversations', '--current-json', str(current)], cwd=ROOT, text=True, capture_output=True, env=self.fixture_env)
            self.assertEqual(0, proc.returncode, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual('candidate-ranking-only', payload['ranking_authority'])
            self.assertEqual('same-path', payload['results'][0]['session_id'])
            self.assertEqual('exact_path', payload['results'][0]['rank_reason'])
            self.assertNotIn('classification', payload['results'][0])


if __name__ == '__main__':
    unittest.main()
