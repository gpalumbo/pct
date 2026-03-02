"""Board router — /api/board endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from pct.auth.dependencies import get_current_user, get_settings
from pct.board.dag_validation import CycleError
from pct.board.models import FeatureCreate, FeatureUpdate, TaskCreate, TaskMove, TaskUpdate
from pct.board.service import BoardService
from pct.config import Settings
from pct.storage.task_io import load_task_body

router = APIRouter(prefix="/api/board", tags=["board"])


def _board_service(settings: Settings = Depends(get_settings)) -> BoardService:
    return BoardService(settings.project_root)


@router.get("/")
async def get_board(
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    return svc.get_board_state()


# ── Features ──


@router.post("/features")
async def create_feature(
    req: FeatureCreate,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    feature = svc.create_feature(req)
    return feature.model_dump(mode="json")


@router.get("/features/{feature_id}")
async def get_feature(
    feature_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    feature = svc.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature.model_dump(mode="json")


@router.patch("/features/{feature_id}")
async def update_feature(
    feature_id: str,
    req: FeatureUpdate,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    feature = svc.update_feature(feature_id, req)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature.model_dump(mode="json")


@router.delete("/features/{feature_id}")
async def delete_feature(
    feature_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    if not svc.delete_feature(feature_id):
        raise HTTPException(status_code=404, detail="Feature not found")
    return {"deleted": True}


@router.post("/features/{feature_id}/suspend")
async def suspend_feature(
    feature_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    feature = svc.suspend_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature.model_dump(mode="json")


@router.post("/features/{feature_id}/resume")
async def resume_feature(
    feature_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    feature = svc.resume_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature.model_dump(mode="json")


# ── Tasks ──


@router.get("/features/{feature_id}/tasks")
async def list_tasks(
    feature_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    from pct.storage.task_io import list_tasks as _list_tasks

    tasks = _list_tasks(svc.project_root, feature_id)
    return [t.model_dump(mode="json") for t in tasks]


@router.post("/features/{feature_id}/tasks")
async def create_task(
    feature_id: str,
    req: TaskCreate,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    try:
        task = svc.create_task(feature_id, req)
    except CycleError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return task.model_dump(mode="json")


@router.get("/features/{feature_id}/tasks/{task_id}")
async def get_task(
    feature_id: str,
    task_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    task = svc.get_task(feature_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


@router.put("/features/{feature_id}/tasks/{task_id}")
async def update_task(
    feature_id: str,
    task_id: str,
    req: TaskUpdate,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    try:
        task = svc.update_task(feature_id, task_id, req)
    except CycleError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


@router.delete("/features/{feature_id}/tasks/{task_id}")
async def delete_task_endpoint(
    feature_id: str,
    task_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    if not svc.delete_task_by_id(feature_id, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@router.post("/features/{feature_id}/tasks/{task_id}/move")
async def move_task(
    feature_id: str,
    task_id: str,
    req: TaskMove,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    task = svc.move_task(feature_id, task_id, req)
    if task is None:
        raise HTTPException(status_code=400, detail="Cannot move task (blocked or not found)")
    return task.model_dump(mode="json")



# ── PERT Chart ──


@router.get("/features/{feature_id}/pert")
async def get_feature_pert(
    feature_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    try:
        data = svc.get_feature_pert(feature_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Feature not found") from e
    return data.model_dump(mode="json")


@router.get("/pert")
async def get_project_pert(
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    return svc.get_project_pert().model_dump(mode="json")


# ── Artifacts ──


@router.get("/features/{feature_id}/tasks/{task_id}/artifact")
async def get_artifact(
    feature_id: str,
    task_id: str,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    body = load_task_body(svc.project_root, feature_id, task_id)
    return {"content": body}


@router.put("/features/{feature_id}/tasks/{task_id}/artifact")
async def put_artifact(
    feature_id: str,
    task_id: str,
    body: dict,
    svc: BoardService = Depends(_board_service),
    _user: str = Depends(get_current_user),
):
    from pct.storage.task_io import load_task as _load_task
    from pct.storage.task_io import save_task as _save_task

    task = _load_task(svc.project_root, feature_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    _save_task(svc.project_root, task, body=body.get("content", ""))
    return {"saved": True}
