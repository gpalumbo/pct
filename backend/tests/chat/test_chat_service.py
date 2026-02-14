"""Tests for the chat persistence service."""

import os

import pytest

from pct.chat.models import PlanningMessage, UpdateMessageRequest
from pct.chat import service


@pytest.fixture(autouse=True)
def _isolate_chat(tmp_path):
    """Isolate project root and registries for each test."""
    os.environ["PCT_PROJECT_ROOT"] = str(tmp_path / "project")
    os.environ["PCT_REGISTRIES_DIR"] = str(tmp_path / "registries")
    (tmp_path / "project" / ".pct").mkdir(parents=True)

    from pct import config
    config.settings = config.Settings()
    yield


class TestSessionCRUD:
    def test_list_sessions_empty(self):
        assert service.list_sessions() == []

    def test_create_session(self):
        session = service.create_session("My Chat")
        assert session.id == "planning-001"
        assert session.title == "My Chat"

    def test_create_multiple_sessions(self):
        s1 = service.create_session("First")
        s2 = service.create_session("Second")
        assert s1.id == "planning-001"
        assert s2.id == "planning-002"

    def test_get_session(self):
        service.create_session("Test")
        session = service.get_session("planning-001")
        assert session is not None
        assert session.title == "Test"

    def test_get_session_not_found(self):
        assert service.get_session("nope") is None

    def test_get_or_create_default_session(self):
        # First call creates
        s1 = service.get_or_create_default_session()
        assert s1.id == "planning-001"
        # Second call returns existing
        s2 = service.get_or_create_default_session()
        assert s2.id == "planning-001"

    def test_list_sessions_returns_all(self):
        service.create_session("A")
        service.create_session("B")
        sessions = service.list_sessions()
        assert len(sessions) == 2


class TestMessages:
    def test_load_messages_empty(self):
        service.create_session("Test")
        msgs = service.load_messages("planning-001")
        assert msgs == []

    def test_append_and_load_messages(self):
        service.create_session("Test")
        msg = PlanningMessage(role="user", content="Hello")
        service.append_message("planning-001", msg)

        msgs = service.load_messages("planning-001")
        assert len(msgs) == 1
        assert msgs[0].content == "Hello"
        assert msgs[0].role == "user"

    def test_append_multiple_messages(self):
        service.create_session("Test")
        service.append_message("planning-001", PlanningMessage(role="user", content="Hi"))
        service.append_message("planning-001", PlanningMessage(role="assistant", content="Hello!"))

        msgs = service.load_messages("planning-001")
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"

    def test_update_message_content(self):
        service.create_session("Test")
        msg = PlanningMessage(role="user", content="Original")
        service.append_message("planning-001", msg)

        updated = service.update_message(
            "planning-001",
            msg.id,
            UpdateMessageRequest(content="Updated"),
        )
        assert updated is not None
        assert updated.content == "Updated"

        msgs = service.load_messages("planning-001")
        assert msgs[0].content == "Updated"

    def test_update_message_included(self):
        service.create_session("Test")
        msg = PlanningMessage(role="user", content="Test")
        service.append_message("planning-001", msg)

        service.update_message(
            "planning-001",
            msg.id,
            UpdateMessageRequest(included=False),
        )

        msgs = service.load_messages("planning-001")
        assert msgs[0].included is False

    def test_update_message_role(self):
        service.create_session("Test")
        msg = PlanningMessage(role="user", content="Test")
        service.append_message("planning-001", msg)

        service.update_message(
            "planning-001",
            msg.id,
            UpdateMessageRequest(role="system"),
        )

        msgs = service.load_messages("planning-001")
        assert msgs[0].role == "system"

    def test_update_message_not_found(self):
        service.create_session("Test")
        result = service.update_message(
            "planning-001",
            "nonexistent",
            UpdateMessageRequest(content="x"),
        )
        assert result is None

    def test_get_included_messages(self):
        service.create_session("Test")
        m1 = PlanningMessage(role="user", content="A")
        m2 = PlanningMessage(role="assistant", content="B")
        service.append_message("planning-001", m1)
        service.append_message("planning-001", m2)

        # Exclude second message
        service.update_message("planning-001", m2.id, UpdateMessageRequest(included=False))

        included = service.get_included_messages("planning-001")
        assert len(included) == 1
        assert included[0].content == "A"

    def test_session_message_count_updated(self):
        service.create_session("Test")
        service.append_message("planning-001", PlanningMessage(role="user", content="A"))
        service.append_message("planning-001", PlanningMessage(role="assistant", content="B"))

        session = service.get_session("planning-001")
        assert session is not None
        assert session.message_count == 2
