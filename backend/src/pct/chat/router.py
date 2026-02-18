"""Chat API routes — session CRUD and SSE streaming endpoint."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AssembledContext
from pct.agent.tools import ToolRegistry, create_global_registry
from pct.auth.dependencies import get_current_user
from pct.chat import service
from pct.chat.models import (
    ChatSession,
    PlanningMessage,
    SendMessageRequest,
    UpdateMessageRequest,
)
from pct.chat.provider_factory import get_default_planning_agent_id, resolve_provider
from pct.config import settings
from pct.settings import service as settings_service

logger = logging.getLogger(__name__)

router = APIRouter()

_tool_registry: ToolRegistry | None = None


def _get_tool_registry() -> ToolRegistry:
    """Lazily create the global tool registry (singleton per process)."""
    global _tool_registry
    if _tool_registry is None:
        from pathlib import Path

        project_root = Path(settings.project_root) if settings.project_root else Path.cwd()
        project_cfg = settings_service.get_project_config()
        project_id = project_cfg.project_id if project_cfg else ""
        _tool_registry = create_global_registry(project_root, project_id)
    return _tool_registry


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=list[ChatSession])
async def list_sessions(_user: dict = Depends(get_current_user)):
    return service.list_sessions()


class CreateSessionRequest(BaseModel):
    title: str = "Planning"
    session_id: str | None = None


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: CreateSessionRequest | None = None,
    _user: dict = Depends(get_current_user),
):
    req = req or CreateSessionRequest()
    return service.create_session(title=req.title, session_id=req.session_id)


@router.get("/sessions/default", response_model=ChatSession)
async def get_default_session(_user: dict = Depends(get_current_user)):
    return service.get_or_create_default_session()


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(session_id: str, _user: dict = Depends(get_current_user)):
    s = service.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


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


@router.delete(
    "/sessions/{session_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message(
    session_id: str,
    message_id: str,
    _user: dict = Depends(get_current_user),
):
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not service.delete_message(session_id, message_id):
        raise HTTPException(status_code=404, detail="Message not found")


@router.delete(
    "/sessions/{session_id}/messages/{message_id}/truncate",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def truncate_from_message(
    session_id: str,
    message_id: str,
    _user: dict = Depends(get_current_user),
):
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not service.truncate_from_message(session_id, message_id):
        raise HTTPException(status_code=404, detail="Message not found")


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

        # Run the chat turn in background and persist immediately on
        # completion so the message is saved even if the SSE client
        # disconnects before the generator finishes.
        async def run_chat():
            try:
                provider, agent_cfg = resolve_provider(agent_id)
                system_prompt = agent_cfg.prompt_template
                if req.artifact_path:
                    system_prompt = (
                        f"You are working on a kanban task. Write your final results "
                        f"to the artifact file at: {req.artifact_path}\n"
                        f'Use the file tool with action "write" to save your output there.\n\n'
                        + system_prompt
                    )
                result = await execute_chat_turn(
                    provider=provider,
                    context=context,
                    system_prompt=system_prompt,
                    on_token=on_token,
                    tool_registry=_get_tool_registry(),
                )
                full_content = "".join(collected_tokens) or result.output
                assistant_msg = PlanningMessage(
                    role="assistant",
                    content=full_content,
                    tokens=result.tokens_output or None,
                    agent_id=agent_id,
                )
                service.append_message(session_id, assistant_msg)
                return assistant_msg
            except Exception:
                logger.exception("Chat turn failed")
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

        # Message already persisted by run_chat(); send done event if
        # the client is still connected.
        try:
            assistant_msg = await task
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
