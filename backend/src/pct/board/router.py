"""API routes for the Kanban board: features, tasks, backlog, and composite board."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from pct.auth.dependencies import get_current_user
from pct.board import service
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
