import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from history_adapters import (
    ChatGPTExportHistoryAdapter,
    ClaudeCodeHistoryAdapter,
    CodexHistoryAdapter,
)


class HostNativeAdapterTests(unittest.TestCase):
    def test_claude_code_jsonl_normalizes_session_text_paths_and_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / "-Users-vladimir-projects-FIX"
            project_dir.mkdir()
            session = project_dir / "abc123.jsonl"
            rows = [
                {"type": "user", "uuid": "m1", "parentUuid": None, "sessionId": "abc123", "timestamp": "2026-09-16T06:00:00Z", "cwd": "/Users/vladimir/projects/FIX", "message": {"role": "user", "content": "continue Project History Agent from chat agent"}},
                {"type": "assistant", "uuid": "m2", "parentUuid": "m1", "sessionId": "abc123", "timestamp": "2026-09-16T06:00:05Z", "cwd": "/Users/vladimir/projects/FIX", "message": {"role": "assistant", "content": [{"type": "text", "text": "Updating the project memory."}, {"type": "tool_use", "name": "Read", "input": {"file_path": "/Users/vladimir/projects/FIX/PROJECT_MEMORY.md"}}]}},
            ]
            session.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
            adapter = ClaudeCodeHistoryAdapter(root)
            item = adapter.inspect("abc123")
            self.assertEqual("claude-code", item["provider"])
            self.assertIn("/Users/vladimir/projects/FIX", item["paths"])
            self.assertIn("/Users/vladimir/projects/FIX/PROJECT_MEMORY.md", item["files"])
            self.assertIn("continue Project History Agent", item["text"])
            self.assertEqual("abc123", adapter.search("conversations", "Project History Agent")[0]["session_id"])

    def test_codex_rollout_normalizes_session_repo_and_cwd(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rollout = root / "rollout-2026-09-16T06-10-00-xyz789.jsonl"
            rows = [
                {"timestamp": "2026-09-16T06:10:00Z", "type": "session_meta", "payload": {"id": "xyz789", "cwd": "C:\\Users\\Vladimir\\Projects\\FIX", "git": {"repository_url": "https://github.com/loftfull/FIX.git", "branch": "project-history-agent-v0.6", "commit_hash": "abcde12345"}}},
                {"timestamp": "2026-09-16T06:10:03Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "continue v0.6 host adapters"}]}},
                {"timestamp": "2026-09-16T06:10:04Z", "type": "response_item", "payload": {"type": "function_call", "name": "read_file", "arguments": json.dumps({"path": "history_adapters.py"})}},
            ]
            rollout.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
            adapter = CodexHistoryAdapter(root)
            item = adapter.inspect("xyz789")
            self.assertEqual("codex", item["provider"])
            self.assertIn("https://github.com/loftfull/FIX.git", item["repositories"])
            self.assertIn("C:\\Users\\Vladimir\\Projects\\FIX", item["paths"])
            self.assertIn("history_adapters.py", item["files"])

    def test_chatgpt_export_normalizes_conversation_without_inventing_parent_chat(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "conversations.json"
            export = [{"id": "conv-agent", "conversation_id": "conv-agent", "title": "агент", "create_time": 1789530000.0, "current_node": "n2", "mapping": {"n1": {"id": "n1", "parent": None, "children": ["n2"], "message": {"id": "msg1", "author": {"role": "user"}, "create_time": 1789530000.0, "content": {"content_type": "text", "parts": ["создай автономного агента истории проекта"]}}}, "n2": {"id": "n2", "parent": "n1", "children": [], "message": {"id": "msg2", "author": {"role": "assistant"}, "create_time": 1789530002.0, "content": {"content_type": "text", "parts": ["Создан протокол проекта"]}}}}}]
            path.write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
            adapter = ChatGPTExportHistoryAdapter(path)
            item = adapter.inspect("conv-agent")
            self.assertEqual("chatgpt-export", item["provider"])
            self.assertEqual("conv-agent", item["chat_id"])
            self.assertIn("автономного агента истории проекта", item["text"])
            self.assertNotIn("parent_session_id", item)

    def test_chatgpt_export_rejects_non_list_root(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "conversations.json"
            path.write_text(json.dumps({"not": "an export list"}), encoding="utf-8")
            adapter = ChatGPTExportHistoryAdapter(path)
            with self.assertRaises(ValueError):
                adapter.search("sessions", "")


if __name__ == "__main__":
    unittest.main()
