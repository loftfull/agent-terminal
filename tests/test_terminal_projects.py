import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project_history_agent import empty_state
from project_history_journal import bootstrap_journal_from_state
from terminal_projects import (update_registry, read_registry, probe_entry, launch_plan,
                               powershell_command, normalized_path)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.memory = self.root / 'Память проекта'
        self.memory.mkdir()
        self.checkout = self.root / "Код O'Brien"
        self.checkout.mkdir()
        self.registry = self.root / 'проекты.json'
        self.entry = dict(project_id='example', memory_root=str(self.memory), checkout_root=str(self.checkout), label='Проект пример')
        bootstrap_journal_from_state(empty_state('example', 'Example', 'Explicit registry'), self.memory / 'PROJECT_HISTORY.events.jsonl')

    def test_roundtrip_cyrillic_spaces_and_remove(self):
        update_registry(self.registry, add=self.entry)
        expected = dict(self.entry, memory_root=str(self.memory.resolve()),
                        checkout_root=str(self.checkout.resolve()))
        self.assertEqual(expected, read_registry(self.registry)[0])
        self.assertEqual('verified-memory', probe_entry(self.entry)['status'])
        update_registry(self.registry, remove='example')
        self.assertEqual([], read_registry(self.registry))
        self.assertTrue(self.memory.exists())

    def test_duplicate_and_nested_memory_root_rejected(self):
        update_registry(self.registry, add=self.entry)
        original = self.registry.read_bytes()
        for entry in (self.entry, dict(self.entry, project_id='other'), dict(self.entry, project_id='other', memory_root=str(self.memory / 'nested'))):
            with self.assertRaises(ValueError):
                update_registry(self.registry, add=entry)
        self.assertEqual(original, self.registry.read_bytes())

    def test_wrong_project_and_missing_roots_are_not_connected(self):
        self.assertEqual('invalid-memory-or-project-mismatch', probe_entry(dict(self.entry, project_id='wrong'))['status'])
        self.assertEqual('missing-memory-root', probe_entry(dict(self.entry, memory_root=str(self.root / 'missing')))['status'])
        self.assertEqual('verified-memory-missing-checkout', probe_entry(dict(self.entry, checkout_root=str(self.root / 'missing')))['status'])

    def test_tampered_journal_refused(self):
        p = self.memory / 'PROJECT_HISTORY.events.jsonl'
        p.write_text(p.read_text(encoding='utf-8').replace('Explicit registry', 'Altered registry'), encoding='utf-8')
        self.assertEqual('invalid-memory-or-project-mismatch', probe_entry(self.entry)['status'])

    def test_atomic_failure_keeps_original_registry(self):
        update_registry(self.registry, add=self.entry)
        before = self.registry.read_bytes()
        with patch('project_history_journal.os.replace', side_effect=OSError('simulated')):
            with self.assertRaises(OSError):
                update_registry(self.registry, remove='example')
        self.assertEqual(before, self.registry.read_bytes())
        from project_history_journal import ProjectLock
        with ProjectLock(self.registry.with_name(self.registry.name + '.lock'), timeout=.1):
            pass  # Failure released the OS lock; the inode intentionally remains.

    def test_secrets_rejected_not_silently_redacted(self):
        with self.assertRaises(ValueError):
            update_registry(self.registry, add=dict(self.entry, label='token=secret-value'))
        self.assertFalse(self.registry.exists())

    def test_launch_plan_preserves_argv_and_quotes_powershell(self):
        plan = launch_plan(self.entry, sys.executable, Path(__file__).resolve().parents[1])
        self.assertFalse(plan['executed'])
        self.assertIn(str(self.checkout.resolve()), plan['commands']['watch'])
        self.assertIn("O''Brien", plan['powershell']['watch'])
        self.assertEqual("& 'hello' '$(touch evil); x'", powershell_command(['hello', '$(touch evil); x']))

    def test_overlap_warns_and_omits_watcher(self):
        entry = dict(self.entry, checkout_root=str(self.memory))
        plan = launch_plan(entry, sys.executable, Path(__file__).resolve().parents[1])
        self.assertNotIn('watch', plan['commands'])
        self.assertTrue(plan['warnings'])

    def test_missing_checkout_omits_watcher(self):
        plan = launch_plan(dict(self.entry, checkout_root=str(self.root / 'absent')), sys.executable, Path(__file__).resolve().parents[1])
        self.assertNotIn('watch', plan['commands'])
        self.assertTrue(plan['warnings'])

    def test_plan_wrong_project_rejected(self):
        with self.assertRaises(ValueError):
            launch_plan(dict(self.entry, project_id='wrong'), sys.executable, Path(__file__).resolve().parents[1])

    def test_read_and_probe_do_not_write(self):
        update_registry(self.registry, add=self.entry)
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        probe_entry(read_registry(self.registry)[0])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_normalizes_nonexistent_relative_path(self):
        self.assertEqual(str((Path.cwd() / 'not-yet' / 'папка').resolve()), normalized_path('not-yet/папка'))

    def test_stored_relative_paths_rejected(self):
        entry = dict(self.entry, memory_root='relative-memory')
        self.registry.write_text(json.dumps({'schema': 'terminal-project-registry/v1', 'projects': [entry]}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'normalized absolute'):
            read_registry(self.registry)

    def test_interpreter_path_is_not_resolved_away_from_virtualenv(self):
        interpreter = self.root / 'venv-python'
        try:
            interpreter.symlink_to(sys.executable)
        except OSError:
            self.skipTest('Symlink creation unavailable on this host')
        plan = launch_plan(self.entry, str(interpreter), Path(__file__).resolve().parents[1])
        self.assertEqual(str(interpreter), plan['commands']['mcp'][0])

    def test_cli_utf8_output_with_legacy_stdout_encoding(self):
        update_registry(self.registry, add=self.entry)
        script = Path(__file__).resolve().parents[1] / 'terminal_projects.py'
        result = subprocess.run([sys.executable, str(script), '--registry', str(self.registry), 'list'],
                                env={**os.environ, 'PYTHONIOENCODING': 'cp1252'},
                                capture_output=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr.decode('utf-8'))
        payload = json.loads(result.stdout.decode('utf-8'))
        self.assertEqual('Проект пример', payload['projects'][0]['label'])
        self.assertEqual('verified-memory', payload['projects'][0]['status'])

    def test_registry_schema_and_unknown_removal(self):
        with self.assertRaises(ValueError):
            update_registry(self.registry, remove='unknown')
        self.registry.write_text(json.dumps({'schema': 'wrong', 'projects': []}), encoding='utf-8')
        with self.assertRaises(ValueError):
            read_registry(self.registry)


if __name__ == '__main__':
    unittest.main()
