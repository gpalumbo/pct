"""Tests for chat I/O — JSONL format."""

from pathlib import Path

from pct.models.chat import ChatMessage
from pct.models.enums import MessageRole
from pct.storage.chat_io import append_message, list_sessions, load_messages, new_session


class TestChatIO:
    def test_new_session_creates_file(self, tmp_project_root: Path):
        path = new_session(tmp_project_root, "planning")
        assert path.exists()
        assert path.read_text() == ""

    def test_append_and_load(self, tmp_project_root: Path):
        new_session(tmp_project_root, "test-session")
        msg1 = ChatMessage(id="m1", role=MessageRole.user, content="Hello")
        msg2 = ChatMessage(id="m2", role=MessageRole.assistant, content="Hi!")
        append_message(tmp_project_root, "test-session", msg1)
        append_message(tmp_project_root, "test-session", msg2)

        messages = load_messages(tmp_project_root, "test-session")
        assert len(messages) == 2
        assert messages[0].id == "m1"
        assert messages[0].role == MessageRole.user
        assert messages[1].id == "m2"
        assert messages[1].content == "Hi!"

    def test_load_nonexistent(self, tmp_project_root: Path):
        assert load_messages(tmp_project_root, "nonexistent") == []

    def test_list_sessions(self, tmp_project_root: Path):
        new_session(tmp_project_root, "session-a")
        new_session(tmp_project_root, "session-b")
        sessions = list_sessions(tmp_project_root)
        assert "session-a" in sessions
        assert "session-b" in sessions

    def test_list_sessions_empty(self, tmp_path: Path):
        assert list_sessions(tmp_path) == []

    def test_append_without_new_session(self, tmp_project_root: Path):
        """append_message should create the file if needed."""
        msg = ChatMessage(id="m1", role=MessageRole.system, content="System prompt")
        append_message(tmp_project_root, "auto-created", msg)
        messages = load_messages(tmp_project_root, "auto-created")
        assert len(messages) == 1
