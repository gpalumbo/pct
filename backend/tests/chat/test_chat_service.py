"""Tests for chat service."""

from pathlib import Path

from pct.chat.service import ChatService
from pct.models.enums import MessageRole


class TestChatService:
    def test_create_session(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        sid = svc.create_session("test-session")
        assert sid == "test-session"
        assert "test-session" in svc.list_sessions()

    def test_add_and_get_messages(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        svc.add_message("s1", MessageRole.user, "Hello")
        svc.add_message("s1", MessageRole.assistant, "Hi!")
        messages = svc.get_messages("s1")
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi!"

    def test_update_message_content(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        msg = svc.add_message("s1", MessageRole.user, "Original")
        updated = svc.update_message("s1", msg.id, content="Updated")
        assert updated is not None
        assert updated.content == "Updated"
        messages = svc.get_messages("s1")
        assert messages[0].content == "Updated"

    def test_update_message_included(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        msg = svc.add_message("s1", MessageRole.user, "Test")
        updated = svc.update_message("s1", msg.id, included=False)
        assert updated is not None
        assert updated.included is False

    def test_update_nonexistent(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        assert svc.update_message("s1", "nonexistent", content="X") is None

    def test_delete_message(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        svc.add_message("s1", MessageRole.user, "Keep")
        m2 = svc.add_message("s1", MessageRole.user, "Delete")
        assert svc.delete_message("s1", m2.id) is True
        messages = svc.get_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "Keep"

    def test_delete_nonexistent(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        assert svc.delete_message("s1", "nope") is False

    def test_truncate(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        svc.add_message("s1", MessageRole.user, "M1")
        m2 = svc.add_message("s1", MessageRole.assistant, "M2")
        svc.add_message("s1", MessageRole.user, "M3")
        count = svc.truncate_from("s1", m2.id)
        assert count == 2
        messages = svc.get_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "M1"

    def test_truncate_nonexistent(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        svc.create_session("s1")
        assert svc.truncate_from("s1", "nope") == 0

    def test_get_or_create_session(self, tmp_project_root: Path):
        svc = ChatService(tmp_project_root)
        messages = svc.get_or_create_session("new-session")
        assert messages == []
        assert "new-session" in svc.list_sessions()
