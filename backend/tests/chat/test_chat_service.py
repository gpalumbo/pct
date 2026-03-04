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

    def test_update_session_context(self):
        service.create_session("S1", session_id="s1")
        service.update_session_context("s1", "feat-1", "task-1", "draft")
        session = service.get_session("s1")
        assert session is not None
        assert session.feature_id == "feat-1"
        assert session.task_id == "task-1"
        assert session.stage_id == "draft"


class TestTaskStageStorage:
    """Tests for per-stage task chat storage."""

    def test_append_and_load(self):
        msg1 = PlanningMessage(role="user", content="Hello stage")
        msg2 = PlanningMessage(role="assistant", content="Hi from stage")
        service.append_task_stage_message("feat-1", "task-1", "draft", msg1)
        service.append_task_stage_message("feat-1", "task-1", "draft", msg2)
        messages = service.load_task_stage_messages("feat-1", "task-1", "draft")
        assert len(messages) == 2
        assert messages[0].content == "Hello stage"
        assert messages[1].content == "Hi from stage"

    def test_load_empty(self):
        messages = service.load_task_stage_messages("feat-x", "task-x", "draft")
        assert messages == []

    def test_stage_isolation(self):
        """Messages in one stage don't appear in another."""
        service.append_task_stage_message(
            "feat-1", "task-1", "draft",
            PlanningMessage(role="user", content="Draft msg"),
        )
        service.append_task_stage_message(
            "feat-1", "task-1", "review",
            PlanningMessage(role="user", content="Review msg"),
        )
        draft = service.load_task_stage_messages("feat-1", "task-1", "draft")
        review = service.load_task_stage_messages("feat-1", "task-1", "review")
        assert len(draft) == 1
        assert draft[0].content == "Draft msg"
        assert len(review) == 1
        assert review[0].content == "Review msg"

    def test_correct_directory_structure(self, tmp_project_root: Path):
        service.append_task_stage_message(
            "feat-1", "task-1", "draft",
            PlanningMessage(role="user", content="Check path"),
        )
        expected = (
            tmp_project_root / ".pct" / "chat_history" / "tasks"
            / "feat-1" / "task-1" / "draft.jsonl"
        )
        assert expected.exists()

    def test_get_included(self):
        service.append_task_stage_message(
            "feat-1", "task-1", "draft",
            PlanningMessage(role="user", content="Included"),
        )
        service.append_task_stage_message(
            "feat-1", "task-1", "draft",
            PlanningMessage(role="user", content="Excluded", included=False),
        )
        included = service.get_included_task_stage_messages("feat-1", "task-1", "draft")
        assert len(included) == 1
        assert included[0].content == "Included"

    def test_update_message(self):
        msg = PlanningMessage(role="user", content="Original")
        service.append_task_stage_message("feat-1", "task-1", "draft", msg)
        updated = service.update_task_stage_message(
            "feat-1", "task-1", "draft", msg.id,
            UpdateMessageRequest(content="Updated"),
        )
        assert updated is not None
        assert updated.content == "Updated"
        messages = service.load_task_stage_messages("feat-1", "task-1", "draft")
        assert messages[0].content == "Updated"

    def test_update_nonexistent(self):
        result = service.update_task_stage_message(
            "feat-1", "task-1", "draft", "nope",
            UpdateMessageRequest(content="X"),
        )
        assert result is None

    def test_delete_message(self):
        m1 = PlanningMessage(role="user", content="Keep")
        m2 = PlanningMessage(role="user", content="Delete")
        service.append_task_stage_message("feat-1", "task-1", "draft", m1)
        service.append_task_stage_message("feat-1", "task-1", "draft", m2)
        assert service.delete_task_stage_message("feat-1", "task-1", "draft", m2.id)
        messages = service.load_task_stage_messages("feat-1", "task-1", "draft")
        assert len(messages) == 1
        assert messages[0].content == "Keep"

    def test_delete_nonexistent(self):
        assert not service.delete_task_stage_message("feat-1", "task-1", "draft", "nope")

    def test_truncate(self):
        m1 = PlanningMessage(role="user", content="M1")
        m2 = PlanningMessage(role="assistant", content="M2")
        m3 = PlanningMessage(role="user", content="M3")
        service.append_task_stage_message("feat-1", "task-1", "draft", m1)
        service.append_task_stage_message("feat-1", "task-1", "draft", m2)
        service.append_task_stage_message("feat-1", "task-1", "draft", m3)
        assert service.truncate_task_stage_from_message("feat-1", "task-1", "draft", m2.id)
        messages = service.load_task_stage_messages("feat-1", "task-1", "draft")
        assert len(messages) == 1
        assert messages[0].content == "M1"

    def test_truncate_nonexistent(self):
        assert not service.truncate_task_stage_from_message(
            "feat-1", "task-1", "draft", "nope"
        )
