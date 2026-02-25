"""API routes for the Kanban board: features, tasks, backlog, and composite board."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pct.auth.dependencies import get_current_user
from pct.board import service
from pct.board.artifact_types import WRITING_ARTIFACT_TYPES
from pct.board.models import (
    BacklogFeature,
    BoardResponse,
    CreateFeatureRequest,
    CreateTaskRequest,
    Feature,
    MoveTaskRequest,
    ReassignTaskRequest,
    Task,
    UpdateFeatureMetadataRequest,
    UpdateTaskRequest,
)

logger = logging.getLogger(__name__)


class ArtifactWriteRequest(BaseModel):
    content: str

router = APIRouter()


# ---------------------------------------------------------------------------
# Composite board
# ---------------------------------------------------------------------------


@router.get("/", response_model=BoardResponse)
async def get_board(_user: dict = Depends(get_current_user)):
    """Return the full board state in a single request."""
    return service.get_board()


@router.get("/artifact-types")
async def get_artifact_types(_user: dict = Depends(get_current_user)):
    """Return available artifact types as {key: label} map."""
    return {k: v["label"] for k, v in WRITING_ARTIFACT_TYPES.items()}


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


@router.get("/features", response_model=list[Feature])
async def list_features(_user: dict = Depends(get_current_user)):
    return service.list_features()


@router.post("/features", response_model=Feature, status_code=status.HTTP_201_CREATED)
async def create_feature(req: CreateFeatureRequest, _user: dict = Depends(get_current_user)):
    if service.get_feature(req.id):
        raise HTTPException(status_code=400, detail=f"Feature '{req.id}' already exists")
    return service.create_feature(req)


@router.get("/features/{feature_id}", response_model=Feature)
async def get_feature(feature_id: str, _user: dict = Depends(get_current_user)):
    f = service.get_feature(feature_id)
    if f is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return f


@router.patch("/features/{feature_id}", response_model=Feature)
async def update_feature_metadata(
    feature_id: str,
    req: UpdateFeatureMetadataRequest,
    _user: dict = Depends(get_current_user),
):
    f = service.update_feature_metadata(feature_id, req)
    if f is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return f


@router.delete("/features/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature(feature_id: str, _user: dict = Depends(get_current_user)):
    if not service.delete_feature(feature_id):
        raise HTTPException(status_code=404, detail="Feature not found")


@router.post("/features/{feature_id}/suspend", response_model=Feature)
async def suspend_feature(feature_id: str, _user: dict = Depends(get_current_user)):
    f = service.suspend_feature(feature_id)
    if f is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return f


@router.post("/features/{feature_id}/resume", response_model=Feature)
async def resume_feature(feature_id: str, _user: dict = Depends(get_current_user)):
    f = service.resume_feature(feature_id)
    if f is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return f


# ---------------------------------------------------------------------------
# Backlog
# ---------------------------------------------------------------------------


@router.get("/backlog", response_model=list[BacklogFeature])
async def list_backlog(_user: dict = Depends(get_current_user)):
    return service.list_backlog()


@router.post("/backlog/{backlog_id}/activate", response_model=Feature)
async def activate_backlog_feature(backlog_id: str, _user: dict = Depends(get_current_user)):
    f = service.activate_backlog_feature(backlog_id)
    if f is None:
        raise HTTPException(status_code=404, detail="Backlog feature not found")
    return f


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@router.get("/features/{feature_id}/tasks", response_model=list[Task])
async def list_tasks(feature_id: str, _user: dict = Depends(get_current_user)):
    if service.get_feature(feature_id) is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return service.list_tasks(feature_id)


@router.post(
    "/features/{feature_id}/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    feature_id: str,
    req: CreateTaskRequest,
    _user: dict = Depends(get_current_user),
):
    task = service.create_task(feature_id, req)
    if task is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return task


@router.get("/features/{feature_id}/tasks/{task_id}", response_model=Task)
async def get_task(
    feature_id: str, task_id: str, _user: dict = Depends(get_current_user)
):
    t = service.get_task(feature_id, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.put("/features/{feature_id}/tasks/{task_id}", response_model=Task)
async def update_task(
    feature_id: str,
    task_id: str,
    req: UpdateTaskRequest,
    _user: dict = Depends(get_current_user),
):
    t = service.update_task(feature_id, task_id, req)
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.post("/features/{feature_id}/tasks/{task_id}/move", response_model=Task)
async def move_task(
    feature_id: str,
    task_id: str,
    req: MoveTaskRequest,
    _user: dict = Depends(get_current_user),
):
    try:
        t = service.move_task(feature_id, task_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.delete(
    "/features/{feature_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    feature_id: str, task_id: str, _user: dict = Depends(get_current_user)
):
    if not service.delete_task(feature_id, task_id):
        raise HTTPException(status_code=404, detail="Task not found")


# ---------------------------------------------------------------------------
# Task reassignment (cross-feature drag)
# ---------------------------------------------------------------------------


@router.post("/tasks/reassign", response_model=Task)
async def reassign_task(req: ReassignTaskRequest, _user: dict = Depends(get_current_user)):
    try:
        return service.reassign_task(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


@router.get("/features/{feature_id}/tasks/{task_id}/artifact")
async def get_artifact(
    feature_id: str, task_id: str, _user: dict = Depends(get_current_user)
):
    task = service.get_task(feature_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.read_artifact(feature_id, task_id)


@router.put("/features/{feature_id}/tasks/{task_id}/artifact")
async def put_artifact(
    feature_id: str,
    task_id: str,
    req: ArtifactWriteRequest,
    _user: dict = Depends(get_current_user),
):
    task = service.get_task(feature_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.write_artifact(feature_id, task_id, req.content)


# ---------------------------------------------------------------------------
# Analysis endpoints (Gap Analysis & Continuity Check)
# ---------------------------------------------------------------------------


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


async def _run_analysis_stream(feature_id: str, build_prompt_fn):
    """Shared SSE streaming logic for analysis endpoints."""
    from pct.agent.chat_loop import execute_chat_turn
    from pct.agent.models import AssembledContext
    from pct.agent.tools import ToolRegistry
    from pct.chat.provider_factory import get_default_planning_agent_id, resolve_provider

    feature = service.get_feature(feature_id)
    if feature is None:
        async def not_found():
            yield _sse({"error": "Feature not found"})
        return StreamingResponse(not_found(), media_type="text/event-stream")

    agent_id = get_default_planning_agent_id()
    if agent_id is None:
        async def no_agent():
            yield _sse({"error": "No agent configured. Add an agent in Settings."})
        return StreamingResponse(no_agent(), media_type="text/event-stream")

    context: AssembledContext = build_prompt_fn(feature_id)

    async def event_stream():
        collected_tokens: list[str] = []
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_token(token: str) -> None:
            collected_tokens.append(token)
            await token_queue.put(token)

        async def run_analysis():
            try:
                provider, agent_cfg = resolve_provider(agent_id)
                result = await execute_chat_turn(
                    provider=provider,
                    context=context,
                    system_prompt=agent_cfg.prompt_template,
                    on_token=on_token,
                    tool_registry=ToolRegistry(),
                )
                return "".join(collected_tokens) or result.output
            except Exception:
                logger.exception("Analysis failed")
                raise
            finally:
                await token_queue.put(None)

        task = asyncio.create_task(run_analysis())

        while True:
            token = await token_queue.get()
            if token is None:
                break
            yield _sse({"token": token})

        try:
            full_content = await task
            yield _sse({"done": True, "content": full_content})
        except Exception as e:
            yield _sse({"error": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/features/{feature_id}/gap-analysis")
async def run_gap_analysis(
    feature_id: str, _user: dict = Depends(get_current_user)
):
    from pct.board.analysis import build_gap_analysis_prompt
    return await _run_analysis_stream(feature_id, build_gap_analysis_prompt)


@router.post("/features/{feature_id}/continuity-check")
async def run_continuity_check(
    feature_id: str, _user: dict = Depends(get_current_user)
):
    from pct.board.analysis import build_continuity_check_prompt
    return await _run_analysis_stream(feature_id, build_continuity_check_prompt)
