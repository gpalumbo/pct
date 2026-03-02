"""Chat router — /api/chat endpoints with SSE streaming."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from pct.auth.dependencies import get_current_user, get_settings
from pct.chat.models import MessageUpdate, SendMessage
from pct.chat.service import ChatService
from pct.config import Settings
from pct.models.enums import MessageRole

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    return ChatService(settings.project_root)


@router.get("/sessions")
async def list_sessions(
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    return svc.list_sessions()


@router.post("/sessions")
async def create_session(
    session_id: str,
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    sid = svc.create_session(session_id)
    return {"session_id": sid}


@router.get("/sessions/default")
async def get_default_session(
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    messages = svc.get_or_create_session("planning")
    return {"session_id": "planning", "messages": [m.model_dump(mode="json") for m in messages]}


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    messages = svc.get_messages(session_id)
    return [m.model_dump(mode="json") for m in messages]


@router.post("/sessions/{session_id}/send")
async def send_message(
    session_id: str,
    req: SendMessage,
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    """Send a message and stream response via SSE."""
    # Add user message
    svc.add_message(session_id, MessageRole.user, req.content)

    # For now (UserProvider stub), echo a response
    async def generate():
        response_text = f"Received: {req.content}"
        # Stream tokens
        for word in response_text.split():
            event = {"type": "token", "content": word + " "}
            yield f"data: {json.dumps(event)}\n\n"

        # Add assistant message
        assistant_msg = svc.add_message(session_id, MessageRole.assistant, response_text)

        # Done event
        done_event = {"type": "done", "message_id": assistant_msg.id}
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.put("/sessions/{session_id}/messages/{message_id}")
async def update_message(
    session_id: str,
    message_id: str,
    req: MessageUpdate,
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    msg = svc.update_message(session_id, message_id, req.content, req.role, req.included)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg.model_dump(mode="json")


@router.delete("/sessions/{session_id}/messages/{message_id}")
async def delete_message(
    session_id: str,
    message_id: str,
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    if not svc.delete_message(session_id, message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"deleted": True}


@router.delete("/sessions/{session_id}/messages/{message_id}/truncate")
async def truncate_messages(
    session_id: str,
    message_id: str,
    svc: ChatService = Depends(_chat_service),
    _user: str = Depends(get_current_user),
):
    count = svc.truncate_from(session_id, message_id)
    return {"deleted_count": count}
