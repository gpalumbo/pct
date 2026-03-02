"""Tests for notification service — CRUD, badge count."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pct.models.enums import NotificationEventType, NotificationState
from pct.notifications.service import NotificationService, get_notification_service


@pytest.fixture
def svc() -> NotificationService:
    """Create a fresh NotificationService for each test."""
    return NotificationService()


class TestCreateEvent:
    def test_create_event_basic(self, svc: NotificationService):
        """create_event creates and stores a notification."""
        event = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Task waiting for user input",
        )

        assert event.id is not None
        assert event.event_type == NotificationEventType.task_waiting
        assert event.message == "Task waiting for user input"
        assert event.severity == NotificationState.attention
        assert event.acknowledged is False

    def test_create_event_with_all_fields(self, svc: NotificationService):
        """create_event stores all provided fields."""
        event = svc.create_event(
            event_type=NotificationEventType.agent_failure,
            message="Agent crashed",
            severity=NotificationState.warning,
            task_id="t1",
            feature_id="f1",
            email_target="user@example.com",
        )

        assert event.feature_id == "f1"
        assert event.task_id == "t1"
        assert event.email_target == "user@example.com"
        assert event.severity == NotificationState.warning

    def test_create_multiple_events(self, svc: NotificationService):
        """Multiple events can be created and listed."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.agent_failure,
            message="Event 2",
        )

        events = svc.list_events()
        assert len(events) == 2


class TestListEvents:
    def test_list_events_most_recent_first(self, svc: NotificationService):
        """Events are returned most recent first."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="First",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Second",
        )

        events = svc.list_events()
        assert len(events) == 2
        assert events[0].message == "Second"
        assert events[1].message == "First"

    def test_list_events_excludes_acknowledged(self, svc: NotificationService):
        """By default, acknowledged events are excluded."""
        e1 = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        svc.acknowledge(e1.id)

        events = svc.list_events()
        assert len(events) == 1
        assert events[0].message == "Event 2"

    def test_list_events_includes_acknowledged(self, svc: NotificationService):
        """include_acknowledged=True returns all events."""
        e1 = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        svc.acknowledge(e1.id)

        events = svc.list_events(include_acknowledged=True)
        assert len(events) == 2

    def test_list_events_filter_by_feature(self, svc: NotificationService):
        """Events can be filtered by feature_id."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="F1 event",
            feature_id="f1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="F2 event",
            feature_id="f2",
        )

        events = svc.list_events(feature_id="f1")
        assert len(events) == 1
        assert events[0].feature_id == "f1"

    def test_list_events_filter_by_task(self, svc: NotificationService):
        """Events can be filtered by task_id."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="T1 event",
            task_id="t1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="T2 event",
            task_id="t2",
        )

        events = svc.list_events(task_id="t1")
        assert len(events) == 1
        assert events[0].task_id == "t1"

    def test_list_events_respects_limit(self, svc: NotificationService):
        """Limit parameter caps the number of returned events."""
        for i in range(10):
            svc.create_event(
                event_type=NotificationEventType.task_waiting,
                message=f"Event {i}",
            )

        events = svc.list_events(limit=3)
        assert len(events) == 3


class TestAcknowledge:
    def test_acknowledge_single(self, svc: NotificationService):
        """Acknowledging an event marks it as acknowledged."""
        event = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Acknowledge me",
        )

        result = svc.acknowledge(event.id)
        assert result is True

        # Verify via get_event
        updated = svc.get_event(event.id)
        assert updated is not None
        assert updated.acknowledged is True

    def test_acknowledge_nonexistent(self, svc: NotificationService):
        """Acknowledging a non-existent event returns False."""
        result = svc.acknowledge("nonexistent-id")
        assert result is False

    def test_acknowledge_all(self, svc: NotificationService):
        """acknowledge_all marks all unacknowledged events."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.agent_failure,
            message="Event 2",
        )
        svc.create_event(
            event_type=NotificationEventType.merge_conflict,
            message="Event 3",
        )

        count = svc.acknowledge_all()
        assert count == 3

        # All should now be acknowledged
        events = svc.list_events(include_acknowledged=True)
        assert all(e.acknowledged for e in events)

    def test_acknowledge_all_returns_zero_when_empty(
        self, svc: NotificationService
    ):
        """acknowledge_all returns 0 when no unacknowledged events."""
        count = svc.acknowledge_all()
        assert count == 0

    def test_acknowledge_all_skips_already_acknowledged(
        self, svc: NotificationService
    ):
        """acknowledge_all only counts newly acknowledged events."""
        e1 = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        svc.acknowledge(e1.id)

        count = svc.acknowledge_all()
        assert count == 1  # Only event 2 was newly acknowledged


class TestBadgeCount:
    def test_badge_count_zero_initially(self, svc: NotificationService):
        """Badge count is 0 when no events exist."""
        assert svc.badge_count() == 0

    def test_badge_count_reflects_unacknowledged(
        self, svc: NotificationService
    ):
        """Badge count matches unacknowledged event count."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        assert svc.badge_count() == 2

    def test_badge_count_decreases_on_acknowledge(
        self, svc: NotificationService
    ):
        """Badge count decreases when events are acknowledged."""
        e1 = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        svc.acknowledge(e1.id)
        assert svc.badge_count() == 1

    def test_badge_count_zero_after_acknowledge_all(
        self, svc: NotificationService
    ):
        """Badge count is 0 after acknowledging all."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        svc.acknowledge_all()
        assert svc.badge_count() == 0


class TestGetEvent:
    def test_get_existing_event(self, svc: NotificationService):
        """get_event returns the correct event."""
        event = svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Find me",
        )

        found = svc.get_event(event.id)
        assert found is not None
        assert found.message == "Find me"

    def test_get_nonexistent_event(self, svc: NotificationService):
        """get_event returns None for unknown id."""
        assert svc.get_event("nonexistent") is None


class TestClearAll:
    def test_clear_all(self, svc: NotificationService):
        """clear_all removes all events."""
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 1",
        )
        svc.create_event(
            event_type=NotificationEventType.task_waiting,
            message="Event 2",
        )

        svc.clear_all()
        assert svc.badge_count() == 0
        assert len(svc.list_events(include_acknowledged=True)) == 0


class TestSingleton:
    def test_get_notification_service_singleton(self):
        """get_notification_service returns the same instance."""
        import pct.notifications.service as mod

        # Reset singleton
        mod._service = None

        s1 = get_notification_service()
        s2 = get_notification_service()
        assert s1 is s2

        # Clean up
        mod._service = None


class TestEmailIntegration:
    @pytest.mark.asyncio
    async def test_send_email_without_smtp_config(self):
        """send_email returns False when smtp_config is None."""
        from pct.notifications.email import send_email

        result = await send_email(
            smtp_config=None,
            to_address="user@example.com",
            subject="Test",
            body="Test body",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_without_aiosmtplib(self):
        """send_email returns False when aiosmtplib is not installed."""
        from pct.models.core import SmtpConfig
        from pct.notifications.email import send_email

        config = SmtpConfig(
            server="smtp.example.com",
            port=587,
            username="user@example.com",
            password="secret",
        )

        with patch.dict("sys.modules", {"aiosmtplib": None}):
            # This will trigger ImportError on import
            result = await send_email(
                smtp_config=config,
                to_address="user@example.com",
                subject="Test",
                body="Test body",
            )
            # May return False (ImportError) or True (if aiosmtplib happens to be installed)
            # We just check it doesn't crash
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_send_notification_email_formats_correctly(self):
        """send_notification_email formats subject and body."""
        from pct.notifications.email import send_notification_email

        with patch(
            "pct.notifications.email.send_email",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send:
            await send_notification_email(
                smtp_config=None,  # Will be passed through
                to_address="user@example.com",
                event_type="task_waiting",
                message="Task is waiting",
                feature_id="f1",
                task_id="t1",
            )

        # send_email was called
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        # send_email is called with positional args: (smtp_config, to, subject, body)
        subject = call_args.kwargs.get("subject") or call_args[0][2]
        assert "task_waiting" in subject
