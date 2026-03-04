"""Chat API routes — session CRUD and SSE streaming endpoint."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AssembledContext, ContextMessage, ContextResource
from pct.board import service as board_service
from pct.models.enums import ResourceKind
from pct.agent.tools import ToolRegistry, create_global_registry
from pct.auth.dependencies import get_current_user
from pct.chat import service
from pct.chat.context_builder import rag_search_context, resolve_task_context
from pct.chat.models import (
    ChatSession,
    PlanningMessage,
    SendMessageRequest,
    UpdateMessageRequest,
)
from pct.agent.model_downloader import ensure_model_ready
from pct.chat.provider_factory import (
    get_default_planning_agent_id,
    resolve_model_entry_for_agent,
    resolve_provider,
)
from pct.config import settings
from loguru import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])

_tool_registry: ToolRegistry | None = None


def _get_tool_registry() -> ToolRegistry:
    """Lazily create the global tool registry (singleton per process)."""
    global _tool_registry
    if _tool_registry is None:
        project_root = Path(settings.project_root) if settings.project_root else Path.cwd()
        _tool_registry = create_global_registry(project_root)
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
    session = service.get_or_create_session(session_id)
    if session.feature_id and session.task_id and session.stage_id:
        return service.load_task_stage_messages(
            session.feature_id, session.task_id, session.stage_id
        )
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
    if session.feature_id and session.task_id and session.stage_id:
        msg = service.update_task_stage_message(
            session.feature_id, session.task_id, session.stage_id,
            message_id, updates,
        )
    else:
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
    if session.feature_id and session.task_id and session.stage_id:
        ok = service.delete_task_stage_message(
            session.feature_id, session.task_id, session.stage_id, message_id,
        )
    else:
        ok = service.delete_message(session_id, message_id)
    if not ok:
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
    if session.feature_id and session.task_id and session.stage_id:
        ok = service.truncate_task_stage_from_message(
            session.feature_id, session.task_id, session.stage_id, message_id,
        )
    else:
        ok = service.truncate_from_message(session_id, message_id)
    if not ok:
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
    # Resolve task context fields from the request body
    feature_id = req.feature_id
    task_id = req.task_id
    stage_id: str | None = None
    is_task_chat = bool(feature_id and task_id)
    logger.debug(
        "send_message: session_id={}, feature_id={}, task_id={}, is_task_chat={}",
        session_id, feature_id, task_id, is_task_chat,
    )

    # Look up current stage from the task
    if is_task_chat:
        try:
            task_obj = board_service.get_task(feature_id, task_id)
            if task_obj:
                stage_id = getattr(task_obj, "current_stage_id", None) or getattr(
                    task_obj, "status", None
                )
        except Exception:
            pass

    # Ensure session exists — store feature/task/stage metadata on it
    session = service.get_or_create_session(session_id)
    if is_task_chat and (
        session.feature_id != feature_id
        or session.task_id != task_id
        or session.stage_id != stage_id
    ):
        service.update_session_context(session_id, feature_id, task_id, stage_id)

    # 1. Persist user message
    user_msg = PlanningMessage(role="user", content=req.content)
    if is_task_chat and stage_id:
        service.append_task_stage_message(feature_id, task_id, stage_id, user_msg)
    else:
        service.append_message(session_id, user_msg)

    # 2. Resolve agent
    agent_id = req.agent_id or session.agent_id or get_default_planning_agent_id()
    if agent_id is None:
        async def no_agent_stream():
            yield _sse({"error": "No agent configured. Add an agent in Settings."})

        return StreamingResponse(no_agent_stream(), media_type="text/event-stream")

    # 3. Load history into AssembledContext as ContextMessage objects
    if is_task_chat and stage_id:
        included = service.get_included_task_stage_messages(
            feature_id, task_id, stage_id
        )
    else:
        included = service.get_included_messages(session_id)

    context = AssembledContext()
    for m in included:
        # Skip system and tool_call roles (backwards compat with old JSONL)
        if m.role in ("system", "tool_call"):
            continue
        if m.role in ("user", "assistant"):
            context.messages.append(
                ContextMessage(role=m.role, content=m.content)
            )
        elif m.role == "tool_result":
            context.messages.append(
                ContextMessage(
                    role="tool_result",
                    content=m.content,
                    tool_call_id=m.tool_call_id,
                    tool_name=m.tool_name,
                )
            )

    # 3a. Resolve cross-reference and RAG context for task sessions
    cross_ref_text, artifact_type_prompt, stage_prompt = resolve_task_context(
        feature_id, task_id
    )
    logger.debug(
        "resolve_task_context result: cross_ref={!r}, artifact_type={!r}, stage={!r}",
        bool(cross_ref_text), artifact_type_prompt, stage_prompt,
    )
    rag_text = rag_search_context(req.content)

    # Attach resources to context
    if cross_ref_text:
        context.resources.append(
            ContextResource(kind=ResourceKind.cross_ref, content=cross_ref_text)
        )
    if rag_text:
        context.resources.append(
            ContextResource(kind=ResourceKind.rag, content=rag_text)
        )

    pre_turn_count = len(context.messages)

    # 4. Stream response
    async def event_stream():
        collected_tokens: list[str] = []
        event_queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_token(token: str) -> None:
            collected_tokens.append(token)
            await event_queue.put({"token": token})

        async def on_status(msg: str) -> None:
            await event_queue.put({"status": msg})

        async def on_tool_call(call_id: str, name: str, arguments: str) -> None:
            await event_queue.put({
                "tool_call": {"id": call_id, "name": name, "arguments": arguments},
            })

        async def on_tool_result(call_id: str, name: str, output: str) -> None:
            await event_queue.put({
                "tool_result": {
                    "id": call_id,
                    "name": name,
                    "output": output[:2000],
                },
            })

        async def on_flush_bubble() -> None:
            """Commit current streaming content as a finalized bubble."""
            content = "".join(collected_tokens)
            if content:
                await event_queue.put({"flush_bubble": content})

        async def run_chat():
            try:
                # Auto-download HuggingFace models if needed
                model_entry = resolve_model_entry_for_agent(agent_id)
                if model_entry is not None:
                    await ensure_model_ready(model_entry, on_status)

                provider, agent_cfg = resolve_provider(agent_id)

                # Set prompts on context
                context.agent_prompt = agent_cfg.prompt_template or ""
                if stage_prompt:
                    context.stage_prompt = stage_prompt
                if artifact_type_prompt:
                    context.project_prompt = artifact_type_prompt

                # Emit system prompt so frontend can display it
                sys_prompt = context.build_system_prompt()
                if sys_prompt:
                    await event_queue.put({"system_prompt": sys_prompt})

                result = await execute_chat_turn(
                    provider=provider,
                    context=context,
                    on_token=on_token,
                    tool_registry=_get_tool_registry(),
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                    on_flush_bubble=on_flush_bubble,
                )

                # Append final assistant response to context
                full_content = "".join(collected_tokens) or result.output
                context.append_assistant(full_content)

                # Persist new messages from the turn
                if is_task_chat and stage_id:
                    _append = lambda msg: service.append_task_stage_message(
                        feature_id, task_id, stage_id, msg
                    )
                else:
                    _append = lambda msg: service.append_message(session_id, msg)
                _persist_turn_messages(_append, context, pre_turn_count, agent_id, result)

                assistant_msg = PlanningMessage(
                    role="assistant",
                    content=full_content,
                    tokens=result.tokens_output or None,
                    agent_id=agent_id,
                )
                return assistant_msg
            except Exception:
                logger.exception("Chat turn failed")
                raise
            finally:
                await event_queue.put(None)

        task = asyncio.create_task(run_chat())

        # Stream events as they arrive
        while True:
            item = await event_queue.get()
            if item is None:
                break
            yield _sse(item)

        try:
            assistant_msg = await task
            yield _sse(
                {
                    "done": True,
                    "message": json.loads(assistant_msg.model_dump_json()),
                }
            )
        except ValueError as e:
            yield _sse({"error": str(e)})
        except Exception as e:
            logger.exception("Unexpected error in chat stream")
            yield _sse({"error": f"An unexpected error occurred: {e}"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _persist_turn_messages(
    append_fn,
    context: AssembledContext,
    pre_turn_count: int,
    agent_id: str,
    result,
) -> None:
    """Persist tool_result and assistant messages added during the turn.

    Iterates ``context.messages[pre_turn_count:]``, skipping ``user`` (already
    persisted before the turn).  No system prompt or tool_call persistence.
    """
    for msg in context.messages[pre_turn_count:]:
        if msg.role == "user":
            continue
        if msg.role == "tool_result":
            append_fn(
                PlanningMessage(
                    role="tool_result",
                    content=msg.content[:10000],
                    included=True,
                    tool_call_id=msg.tool_call_id,
                    tool_name=msg.tool_name,
                ),
            )
        elif msg.role == "assistant":
            append_fn(
                PlanningMessage(
                    role="assistant",
                    content=msg.content,
                    tokens=result.tokens_output or None,
                    agent_id=agent_id,
                ),
            )


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"
