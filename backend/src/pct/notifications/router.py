"""Router — /api/notifications endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pct.auth.dependencies import get_current_user
from pct.notifications.service import get_notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    include_acknowledged: bool = False,
    feature_id: str | None = None,
    task_id: str | None = None,
    limit: int = 100,
    _user: str = Depends(get_current_user),
):
    """List notification events.

    By default returns only unacknowledged events, most recent first.
    """
    svc = get_notification_service()
    events = svc.list_events(
        include_acknowledged=include_acknowledged,
        feature_id=feature_id,
        task_id=task_id,
        limit=limit,
    )
    return {
        "events": [e.model_dump(mode="json") for e in events],
        "badge_count": svc.badge_count(),
    }


@router.get("/badge")
async def badge_count(
    _user: str = Depends(get_current_user),
):
    """Get the unacknowledged notification count for the UI badge."""
    svc = get_notification_service()
    return {"badge_count": svc.badge_count()}


@router.post("/{event_id}/acknowledge")
async def acknowledge_notification(
    event_id: str,
    _user: str = Depends(get_current_user),
):
    """Acknowledge a single notification event."""
    svc = get_notification_service()
    if not svc.acknowledge(event_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"acknowledged": True}


@router.post("/acknowledge-all")
async def acknowledge_all_notifications(
    _user: str = Depends(get_current_user),
):
    """Acknowledge all unacknowledged notification events."""
    svc = get_notification_service()
    count = svc.acknowledge_all()
    return {"acknowledged_count": count}
