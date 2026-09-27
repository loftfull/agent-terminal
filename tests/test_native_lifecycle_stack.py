import json
import tempfile
import unittest
from pathlib import Path

from history_adapters import InMemoryHistoryAdapter
from host_lifecycle_bridge import handle_lifecycle_event
from native_hook_config import write_hook_templates
from native_hook_runner import run_native_hook
from project_history_agent import empty_state, render_markdown
from project_history_doctor import run_doctor
from project_history_journal import atomic_save_state, bootstrap_journal_from_state, replay_journal_set, verify_journal_set
from runtime_journal import append_mutation_set, begin_runtime_segment, close_runtime_segment


class NativeLifecycleStackTests(unittest.TestCase):
    def _project(self, root: Path):
        state = empty_state('p', 'P', 'g')
        state['handoff']['updated_at'] = None
        bootstrap_journal_from_state(state, root / 'PROJECT_HISTORY.events.jsonl')
        atomic_save_state(root / 'PROJECT_MEMORY.json', state)
        (root / 'PROJECT_MEMORY.md').write_text(render_markdown(state), encoding='utf-8')
        return state

    def test_runtime_segment_preserves_base_and_global_chain(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._project(root)
            base = root / 'PROJECT_HISTORY.events.jsonl'
            before = base.read_bytes()
            begin_runtime_segment(root)
            record = append_mutation_set(root, 'handoff.patch', {'next_step': 'continue'}, timestamp='2026-09-16T00:00:00+00:00')
            self.assertEqual(before, base.read_bytes())
            self.assertEqual(verify_journal_set(root)['records'], int(record['journal_id'].split('-')[1]))
            self.assertEqual('continue', replay_journal_set(root)['handoff']['next_step'])
            close_runtime_segment(root)
            self.assertFalse((root / '.project-history.active-segment').exists())

    def test_precompact_checkpoint_uses_project_journal_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._project(root)
            result = handle_lifecycle_event(root, {
                'event': 'checkpoint',
                'reason': 'pre_compaction',
                'summary': 'checkpoint before compact',
                'session_id': 's1',
            })
            self.assertEqual('checkpoint', result['event'])
            self.assertTrue(verify_journal_set(root)['ok'])
            self.assertTrue(any(x.get('summary') == 'checkpoint before compact' for x in result['state']['events']))

    def test_native_runner_loads_handoff_and_is_fail_open(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._project(root)
            payload = {'hook_event_name': 'SessionStart', 'session_id': 's1', 'cwd': str(root), 'transcript_path': str(root / 't.jsonl')}
            ok = run_native_hook('claude-code', payload, project_root=root, adapter=InMemoryHistoryAdapter([]))
            self.assertIsNone(ok['error'])
            self.assertTrue(ok['hook_response']['continue'])
            self.assertIn('Project History Agent handoff loaded', ok['hook_response']['systemMessage'])
            bad = run_native_hook('unknown-provider', payload, project_root=root)
            self.assertIsNotNone(bad['error'])
            self.assertTrue(bad['hook_response']['continue'])

    def test_templates_are_project_local_and_doctor_does_not_claim_installation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._project(root)
            out = write_hook_templates(root)
            self.assertEqual('template_only', out['authority'])
            self.assertFalse((root / '.claude' / 'settings.json').exists())
            self.assertFalse((root / '.codex' / 'hooks.json').exists())
            report = run_doctor(root, adapter=InMemoryHistoryAdapter([]), probe_screenshot=False)
            self.assertEqual('PASS', report['checks']['hook_templates']['status'])
            self.assertEqual('template_only', report['checks']['hook_templates']['authority'])


if __name__ == '__main__':
    unittest.main()
