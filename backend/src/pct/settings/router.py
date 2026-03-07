"""Settings router — /api/config endpoints."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from pct.auth.dependencies import get_current_user, get_settings
from pct.config import Settings
from pct.models.agents import LoRARegistryEntry, LoRAVersion, ModelRegistryEntry
from pct.models.core import Project
from pct.models.enums import DownloadStatus, ProviderType
from pct.settings.service import browse_files, get_project_config, get_project_status, initialize_project, update_project_config
from pct.settings.templates import create_project_from_template, discover_models
from pct.storage.registry_io import load_lora_registry, load_model_registry, save_lora_registry, save_model_registry
from loguru import logger

# Matches GGUF split shard pattern: -NNNNN-of-NNNNN.gguf
_GGUF_SHARD_RE = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)

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
    gguf_filename: str | None = None
    download_status: DownloadStatus | None = None


class ModelUpdateRequest(BaseModel):
    name: str | None = None
    provider_type: ProviderType | None = None
    model_identifier: str | None = None
    context_length: int | None = Field(default=None, ge=0)
    api_base_url: str | None = None
    file_path: str | None = None
    gguf_filename: str | None = None
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
    models, imagegen_ids = discover_models(settings.project_root, settings.root, settings.global_config_dir)
    if models:
        save_model_registry(settings.global_config_dir, models)
    project = create_project_from_template(
        project_id=req.name.lower().replace(" ", "-"),
        name=req.name,
        template=req.project_type,
        directory=str(settings.project_root),
        models=models,
        imagegen_ids=imagegen_ids,
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


# ── HuggingFace GGUF variant listing ─────────────────────────────


@router.get("/hf-gguf-files")
async def list_hf_gguf_files(
    repo_id: str = Query(..., description="HuggingFace repo ID, e.g. Qwen/Qwen2.5-3B-Instruct-GGUF"),
    _user: str = Depends(get_current_user),
):
    """List GGUF file variants in a HuggingFace repo, grouping split shards."""
    try:
        from huggingface_hub import list_repo_tree
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="huggingface-hub is not installed. Install with: pip install huggingface-hub",
        )

    try:
        from pct.config import settings as app_settings

        tree = list_repo_tree(repo_id, token=app_settings.hf_token)
        gguf_files = [
            item for item in tree
            if hasattr(item, "rfilename") and item.rfilename.endswith(".gguf")
        ]
    except Exception as e:
        logger.warning("Failed to list repo tree for {}: {}", repo_id, e)
        raise HTTPException(status_code=400, detail=f"Could not fetch repo '{repo_id}': {e}")

    if not gguf_files:
        return []

    # Group split shards into single variant entries
    variants: dict[str, dict] = {}  # key = display_name or filename
    for item in gguf_files:
        fname = item.rfilename
        size = getattr(item, "size", 0) or 0
        shard_match = _GGUF_SHARD_RE.search(fname)

        if shard_match:
            shard_num = int(shard_match.group(1))
            total_shards = int(shard_match.group(2))
            # Build the base display name by stripping the shard suffix
            base = fname[: shard_match.start()]
            if base not in variants:
                variants[base] = {
                    "filename": fname,  # first shard filename (will be updated)
                    "display_name": base,
                    "total_size": 0,
                    "shard_count": total_shards,
                }
            variants[base]["total_size"] += size
            # Always store the first shard as the filename
            if shard_num == 1:
                variants[base]["filename"] = fname
        else:
            variants[fname] = {
                "filename": fname,
                "display_name": fname,
                "total_size": size,
                "shard_count": 1,
            }

    return sorted(variants.values(), key=lambda v: v["display_name"])


# ── Model registry CRUD ──────────────────────────────────────────


@router.get("/models")
async def list_models(
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    import asyncio

    from pct.agent.model_downloader import sync_hf_download_status

    models = await asyncio.to_thread(sync_hf_download_status, settings.global_config_dir)
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


# ── LoRA registry CRUD ───────────────────────────────────────────


class LoRACreateRequest(BaseModel):
    name: str
    base_model_id: str
    description: str = ""
    active_version: int = 1


class LoRAUpdateRequest(BaseModel):
    name: str | None = None
    base_model_id: str | None = None
    description: str | None = None
    active_version: int | None = None


class LoRAVersionCreateRequest(BaseModel):
    file_path: str
    training_job_id: str | None = None


@router.get("/loras")
async def list_loras(
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    loras = load_lora_registry(settings.global_config_dir)
    return [entry.model_dump(mode="json") for entry in loras]


@router.post("/loras", status_code=status.HTTP_201_CREATED)
async def create_lora(
    req: LoRACreateRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    loras = load_lora_registry(settings.global_config_dir)
    entry = LoRARegistryEntry(
        id=str(uuid.uuid4()),
        **req.model_dump(),
    )
    loras.append(entry)
    save_lora_registry(settings.global_config_dir, loras)
    return entry.model_dump(mode="json")


@router.put("/loras/{lora_id}")
async def update_lora(
    lora_id: str,
    req: LoRAUpdateRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    loras = load_lora_registry(settings.global_config_dir)
    target = next((entry for entry in loras if entry.id == lora_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="LoRA not found")
    updates = req.model_dump(exclude_unset=True)
    updated = target.model_copy(update=updates)
    loras = [updated if entry.id == lora_id else entry for entry in loras]
    save_lora_registry(settings.global_config_dir, loras)
    return updated.model_dump(mode="json")


@router.delete("/loras/{lora_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lora(
    lora_id: str,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    loras = load_lora_registry(settings.global_config_dir)
    before = len(loras)
    loras = [entry for entry in loras if entry.id != lora_id]
    if len(loras) == before:
        raise HTTPException(status_code=404, detail="LoRA not found")
    save_lora_registry(settings.global_config_dir, loras)


@router.post("/loras/{lora_id}/versions", status_code=status.HTTP_201_CREATED)
async def add_lora_version(
    lora_id: str,
    req: LoRAVersionCreateRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    loras = load_lora_registry(settings.global_config_dir)
    target = next((entry for entry in loras if entry.id == lora_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="LoRA not found")
    next_version = max((v.version for v in target.versions), default=0) + 1
    new_version = LoRAVersion(
        version=next_version,
        file_path=req.file_path,
        training_job_id=req.training_job_id,
    )
    updated = target.model_copy(update={"versions": [*target.versions, new_version]})
    loras = [updated if entry.id == lora_id else entry for entry in loras]
    save_lora_registry(settings.global_config_dir, loras)
    return updated.model_dump(mode="json")
