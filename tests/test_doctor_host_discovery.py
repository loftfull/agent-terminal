import json
import tempfile
import unittest
from pathlib import Path

from host_history_discovery import HostHistoryDiscovery
from project_history_agent import empty_state, render_markdown
from project_history_journal import bootstrap_journal_from_state, atomic_save_state
from project_history_doctor import run_doctor


class DoctorHostDiscoveryTests(unittest.TestCase):
    def _project(self, root: Path):
        state = empty_state('p', 'P', 'g'); state['handoff']['updated_at'] = None
        bootstrap_journal_from_state(state, root / 'PROJECT_HISTORY.events.jsonl')
        atomic_save_state(root / 'PROJECT_MEMORY.json', state)
        (root / 'PROJECT_MEMORY.md').write_text(render_markdown(state), encoding='utf-8')

    def test_doctor_auto_wires_available_discovery_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); project = base / 'project'; project.mkdir(); self._project(project)
            claude = base / 'home' / '.claude' / 'projects' / 'demo'; claude.mkdir(parents=True)
            (claude / 's.jsonl').write_text(json.dumps({'sessionId':'c1','message':{'role':'user','content':'hello'}}) + '\n', encoding='utf-8')
            report = run_doctor(project, history_discovery=HostHistoryDiscovery(home=base / 'home', env={}), probe_screenshot=False)
            self.assertEqual('PASS', report['checks']['history_adapter']['status'])
            self.assertEqual('PASS', report['checks']['history_sources']['status'])
            self.assertIn('claude-code', report['checks']['history_sources']['available'])

    def test_doctor_reports_warn_when_no_host_history_available(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); project = base / 'project'; project.mkdir(); self._project(project)
            report = run_doctor(project, history_discovery=HostHistoryDiscovery(home=base / 'home', env={}), probe_screenshot=False)
            self.assertEqual('WARN', report['checks']['history_sources']['status'])
            self.assertEqual('WARN', report['checks']['history_adapter']['status'])
            self.assertNotEqual('FAIL', report['overall'])


if __name__ == '__main__':
    unittest.main()
