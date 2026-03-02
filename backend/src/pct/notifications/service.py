"""Notification service — create, list, acknowledge events.

Uses an in-memory store for now (list of NotificationEvent). In a future
iteration this could be backed by a YAML file or database.
"""

from __future__ import annotations

import logging
import uuid

from pct.models.enums import NotificationEventType, NotificationState
from pct.models.notifications import NotificationEvent

logger = logging.getLogger(__name__)


class NotificationService:
    """In-memory notification service.

    Manages creation, listing, acknowledgement, and badge counting
    of notification events.
    """

    def __init__(self) -> None:
        self._events: list[NotificationEvent] = []

    def create_event(
        self,
        event_type: NotificationEventType,
        message: str,
        severity: NotificationState = NotificationState.attention,
        task_id: str | None = None,
        feature_id: str | None = None,
        email_target: str | None = None,
    ) -> NotificationEvent:
        """Create a new notification event.

        Args:
            event_type: The kind of notification.
            message: Human-readable message.
            severity: Visual severity level.
            task_id: Optional associated task id.
            feature_id: Optional associated feature id.
            email_target: Optional email address for email delivery.

        Returns:
            The created NotificationEvent.
        """
        event = NotificationEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            message=message,
            severity=severity,
            task_id=task_id,
            feature_id=feature_id,
            email_target=email_target,
        )
        self._events.append(event)
        logger.info(
            "Created notification: type=%s message=%s",
            event_type.value,
            message[:80],
        )
        return event

    def list_events(
        self,
        include_acknowledged: bool = False,
        feature_id: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[NotificationEvent]:
        """List notification events, most recent first.

        Args:
            include_acknowledged: If False, only return unacknowledged events.
            feature_id: Filter by feature id.
            task_id: Filter by task id.
            limit: Maximum number of events to return.
        """
        results = list(self._events)

        if not include_acknowledged:
            results = [e for e in results if not e.acknowledged]

        if feature_id is not None:
            results = [e for e in results if e.feature_id == feature_id]

        if task_id is not None:
            results = [e for e in results if e.task_id == task_id]

        # Most recent first
        results.sort(key=lambda e: e.created_at, reverse=True)

        return results[:limit]

    def acknowledge(self, event_id: str) -> bool:
        """Acknowledge a single notification event.

        Returns True if the event was found and acknowledged.
        """
        for event in self._events:
            if event.id == event_id:
                event.acknowledged = True
                logger.debug("Acknowledged notification %s", event_id)
                return True
        return False

    def acknowledge_all(self) -> int:
        """Acknowledge all unacknowledged events.

        Returns the count of newly acknowledged events.
        """
        count = 0
        for event in self._events:
            if not event.acknowledged:
                event.acknowledged = True
                count += 1
        if count:
            logger.info("Acknowledged %d notifications", count)
        return count

    def badge_count(self) -> int:
        """Return the count of unacknowledged notifications.

        This powers the notification badge in the UI header.
        """
        return sum(1 for e in self._events if not e.acknowledged)

    def get_event(self, event_id: str) -> NotificationEvent | None:
        """Get a single event by id."""
        for event in self._events:
            if event.id == event_id:
                return event
        return None

    def clear_all(self) -> None:
        """Clear all events. Primarily for testing."""
        self._events.clear()


# Module-level singleton
_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get or create the singleton NotificationService."""
    global _service
    if _service is None:
        _service = NotificationService()
    return _service
