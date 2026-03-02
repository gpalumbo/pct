"""Settings router — /api/config endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from pct.auth.dependencies import get_current_user, get_settings
from pct.config import Settings
from pct.models.core import Project
from pct.settings.service import browse_files, get_project_config, get_project_status, initialize_project, update_project_config
from pct.settings.templates import create_project_from_template, discover_models
from pct.storage.registry_io import save_model_registry

router = APIRouter(prefix="/api/config", tags=["config"])


class InitProjectRequest(BaseModel):
    name: str
    project_type: str = "coding"


@router.get("/project/status")
async def project_status(settings: Settings = Depends(get_settings)):
    return get_project_status(settings.project_root)


@router.get("/project")
async def get_project(
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    config = get_project_config(settings.project_root)
    if config is None:
        return {"initialized": False}
    return {**config.model_dump(mode="json"), "initialized": True}


@router.post("/project/initialize")
async def init_project_endpoint(
    req: InitProjectRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    existing = get_project_config(settings.project_root)
    if existing is not None:
        raise HTTPException(status_code=400, detail="Project already initialized")
    models = discover_models(settings.project_root, settings.global_config_dir)
    if models:
        save_model_registry(settings.global_config_dir, models)
    project = create_project_from_template(
        project_id=req.name.lower().replace(" ", "-"),
        name=req.name,
        template=req.project_type,
        directory=str(settings.project_root),
        models=models,
    )
    initialized = initialize_project(settings.project_root, project)
    return {**initialized.model_dump(mode="json"), "initialized": True}


@router.put("/project")
async def put_project(
    project: Project,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    existing = get_project_config(settings.project_root)
    if existing is None:
        raise HTTPException(status_code=400, detail="Project not initialized — use POST /project/initialize")
    updated = update_project_config(settings.project_root, project)
    return {**updated.model_dump(mode="json"), "initialized": True}


@router.get("/browse-files")
async def browse(
    path: str = Query(default=""),
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    return browse_files(settings.project_root, path)
