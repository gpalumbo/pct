"""Settings router — /api/config endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from pct.auth.dependencies import get_current_user, get_settings
from pct.config import Settings
from pct.models.agents import ModelRegistryEntry
from pct.models.core import Project
from pct.models.enums import DownloadStatus, ProviderType
from pct.settings.service import browse_files, get_project_config, get_project_status, initialize_project, update_project_config
from pct.settings.templates import create_project_from_template, discover_models
from pct.storage.registry_io import load_model_registry, save_model_registry

router = APIRouter(prefix="/api/config", tags=["config"])


class InitProjectRequest(BaseModel):
    name: str
    project_type: str = "coding"


class ModelCreateRequest(BaseModel):
    name: str
    provider_type: ProviderType
    model_identifier: str
    context_length: int = Field(default=0, ge=0)
    api_base_url: str | None = None
    file_path: str | None = None
    download_status: DownloadStatus | None = None


class ModelUpdateRequest(BaseModel):
    name: str | None = None
    provider_type: ProviderType | None = None
    model_identifier: str | None = None
    context_length: int | None = Field(default=None, ge=0)
    api_base_url: str | None = None
    file_path: str | None = None
    download_status: DownloadStatus | None = None


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
    models = discover_models(settings.project_root, settings.root, settings.global_config_dir)
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


# ── Model registry CRUD ──────────────────────────────────────────


@router.get("/models")
async def list_models(
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    models = load_model_registry(settings.global_config_dir)
    return [m.model_dump(mode="json") for m in models]


@router.post("/models", status_code=status.HTTP_201_CREATED)
async def create_model(
    req: ModelCreateRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    models = load_model_registry(settings.global_config_dir)
    entry = ModelRegistryEntry(
        id=str(uuid.uuid4()),
        **req.model_dump(),
    )
    models.append(entry)
    save_model_registry(settings.global_config_dir, models)
    return entry.model_dump(mode="json")


@router.put("/models/{model_id}")
async def update_model(
    model_id: str,
    req: ModelUpdateRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    models = load_model_registry(settings.global_config_dir)
    target = next((m for m in models if m.id == model_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Model not found")
    updates = req.model_dump(exclude_unset=True)
    updated = target.model_copy(update=updates)
    models = [updated if m.id == model_id else m for m in models]
    save_model_registry(settings.global_config_dir, models)
    return updated.model_dump(mode="json")


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: str,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    models = load_model_registry(settings.global_config_dir)
    before = len(models)
    models = [m for m in models if m.id != model_id]
    if len(models) == before:
        raise HTTPException(status_code=404, detail="Model not found")
    save_model_registry(settings.global_config_dir, models)
