import json
import unittest
from pathlib import Path

from project_history_auditor import audit_state
from project_history_journal import replay_journal_set, verify_journal_set

ROOT = Path(__file__).resolve().parents[1]


class RepositorySmokeTests(unittest.TestCase):
    def test_root_journal_replays_exact_snapshot(self):
        self.assertTrue(verify_journal_set(ROOT)["ok"])
        rebuilt = replay_journal_set(ROOT)
        snapshot = json.loads((ROOT / "PROJECT_MEMORY.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot, rebuilt)
        self.assertEqual([], [x for x in audit_state(rebuilt) if x.get("severity") == "error"])

    def test_current_chat_bundle_replays_exact_snapshot(self):
        root = ROOT / "chat" / "current"
        self.assertTrue(verify_journal_set(root)["ok"])
        rebuilt = replay_journal_set(root)
        snapshot = json.loads((root / "PROJECT_MEMORY.json").read_text(encoding="utf-8"))
        self.assertEqual(snapshot, rebuilt)
        chats = {item["chat_id"]: item for item in rebuilt["chats"]}
        self.assertEqual("chat-agent-origin", chats["chat-current-project-history-agent"]["parent_chat_id"])
        self.assertEqual("continuation", chats["chat-current-project-history-agent"]["classification"])


if __name__ == "__main__":
    unittest.main()
