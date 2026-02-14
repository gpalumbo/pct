"""Chat API routes — session CRUD and SSE streaming endpoint."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from pct.auth.dependencies import get_current_user
from pct.agent.models import AssembledContext
from pct.agent.chat_loop import execute_chat_turn
from pct.chat import service
from pct.chat.models import (
    ChatSession,
    PlanningMessage,
    SendMessageRequest,
    UpdateMessageRequest,
)
from pct.chat.provider_factory import resolve_provider, get_default_planning_agent_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=list[ChatSession])
async def list_sessions(_user: dict = Depends(get_current_user)):
    return service.list_sessions()


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_session(
    title: str = "Planning",
    _user: dict = Depends(get_current_user),
):
    return service.create_session(title)


@router.get("/sessions/default", response_model=ChatSession)
async def get_default_session(_user: dict = Depends(get_current_user)):
    return service.get_or_create_default_session()


@router.get("/sessions/{session_id}/messages", response_model=list[PlanningMessage])
async def get_messages(session_id: str, _user: dict = Depends(get_current_user)):
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return service.load_messages(session_id)


@router.put("/sessions/{session_id}/messages/{message_id}", response_model=PlanningMessage)
async def update_message(
    session_id: str,
    message_id: str,
    updates: UpdateMessageRequest,
    _user: dict = Depends(get_current_user),
):
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    msg = service.update_message(session_id, message_id, updates)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


# ---------------------------------------------------------------------------
# Streaming chat endpoint (SSE)
# ---------------------------------------------------------------------------


@router.post("/sessions/{session_id}/send")
async def send_message(
    session_id: str,
    req: SendMessageRequest,
    _user: dict = Depends(get_current_user),
):
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Persist user message
    user_msg = PlanningMessage(role="user", content=req.content)
    service.append_message(session_id, user_msg)

    # 2. Resolve agent
    agent_id = req.agent_id or session.agent_id or get_default_planning_agent_id()
    if agent_id is None:
        # No agent configured — return error via SSE
        async def no_agent_stream():
            yield _sse({"error": "No agent configured. Add an agent in Settings."})

        return StreamingResponse(no_agent_stream(), media_type="text/event-stream")

    # 3. Build context from included messages
    included = service.get_included_messages(session_id)
    conversation_text = "\n\n".join(
        f"[{m.role}]: {m.content}" for m in included
    )
    context = AssembledContext(base=conversation_text)

    # 4. Stream response
    async def event_stream():
        collected_tokens: list[str] = []
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_token(token: str) -> None:
            collected_tokens.append(token)
            await token_queue.put(token)

        # Run the chat turn in background
        async def run_chat():
            try:
                provider = resolve_provider(agent_id)
                result = await execute_chat_turn(
                    provider=provider,
                    context=context,
                    on_token=on_token,
                )
                return result
            except Exception as e:
                logger.exception("Chat turn failed")
                await token_queue.put(None)
                raise
            finally:
                await token_queue.put(None)

        task = asyncio.create_task(run_chat())

        # Stream tokens as they arrive
        while True:
            token = await token_queue.get()
            if token is None:
                break
            yield _sse({"token": token})

        # Get result and persist assistant message
        try:
            result = await task
            full_content = "".join(collected_tokens) or result.output
            assistant_msg = PlanningMessage(
                role="assistant",
                content=full_content,
                tokens=result.tokens_output or None,
                agent_id=agent_id,
            )
            service.append_message(session_id, assistant_msg)
            yield _sse({
                "done": True,
                "message": json.loads(assistant_msg.model_dump_json()),
            })
        except Exception as e:
            yield _sse({"error": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"
