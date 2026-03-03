"""Tests for chat service (module-level functions)."""

from pathlib import Path

import pytest

from pct.chat import service
from pct.chat.models import PlanningMessage, UpdateMessageRequest
from pct.config import Settings, set_settings


@pytest.fixture(autouse=True)
def _use_tmp_project_root(tmp_project_root: Path):
    """Point config.settings.project_root at the tmp dir for all tests."""
    set_settings(Settings(project_root=tmp_project_root))
    yield
    set_settings(Settings())


class TestChatService:
    def test_create_session(self):
        session = service.create_session("Test Session", session_id="test-session")
        assert session.id == "test-session"
        sessions = service.list_sessions()
        assert any(s.id == "test-session" for s in sessions)

    def test_add_and_get_messages(self):
        service.create_session("S1", session_id="s1")
        service.append_message("s1", PlanningMessage(role="user", content="Hello"))
        service.append_message("s1", PlanningMessage(role="assistant", content="Hi!"))
        messages = service.load_messages("s1")
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi!"

    def test_update_message_content(self):
        service.create_session("S1", session_id="s1")
        msg = PlanningMessage(role="user", content="Original")
        service.append_message("s1", msg)
        updated = service.update_message(
            "s1", msg.id, UpdateMessageRequest(content="Updated")
        )
        assert updated is not None
        assert updated.content == "Updated"
        messages = service.load_messages("s1")
        assert messages[0].content == "Updated"

    def test_update_message_included(self):
        service.create_session("S1", session_id="s1")
        msg = PlanningMessage(role="user", content="Test")
        service.append_message("s1", msg)
        updated = service.update_message(
            "s1", msg.id, UpdateMessageRequest(included=False)
        )
        assert updated is not None
        assert updated.included is False

    def test_update_nonexistent(self):
        service.create_session("S1", session_id="s1")
        assert (
            service.update_message(
                "s1", "nonexistent", UpdateMessageRequest(content="X")
            )
            is None
        )

    def test_delete_message(self):
        service.create_session("S1", session_id="s1")
        service.append_message("s1", PlanningMessage(role="user", content="Keep"))
        m2 = PlanningMessage(role="user", content="Delete")
        service.append_message("s1", m2)
        assert service.delete_message("s1", m2.id) is True
        messages = service.load_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "Keep"

    def test_delete_nonexistent(self):
        service.create_session("S1", session_id="s1")
        assert service.delete_message("s1", "nope") is False

    def test_truncate(self):
        service.create_session("S1", session_id="s1")
        service.append_message("s1", PlanningMessage(role="user", content="M1"))
        m2 = PlanningMessage(role="assistant", content="M2")
        service.append_message("s1", m2)
        service.append_message("s1", PlanningMessage(role="user", content="M3"))
        result = service.truncate_from_message("s1", m2.id)
        assert result is True
        messages = service.load_messages("s1")
        assert len(messages) == 1
        assert messages[0].content == "M1"

    def test_truncate_nonexistent(self):
        service.create_session("S1", session_id="s1")
        assert service.truncate_from_message("s1", "nope") is False

    def test_get_or_create_session(self):
        session = service.get_or_create_session("new-session")
        assert session.id == "new-session"
        sessions = service.list_sessions()
        assert any(s.id == "new-session" for s in sessions)

    def test_get_included_messages(self):
        service.create_session("S1", session_id="s1")
        msg = PlanningMessage(role="user", content="Included")
        service.append_message("s1", msg)
        excluded = PlanningMessage(role="user", content="Excluded", included=False)
        service.append_message("s1", excluded)
        included = service.get_included_messages("s1")
        assert len(included) == 1
        assert included[0].content == "Included"
