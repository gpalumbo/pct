"""Configuration API routes for model registry, LoRA registry, agents, and workflow."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel as PydanticBaseModel

from pct.auth.dependencies import get_current_user
from pct.agent.models import AgentConfig
from pct.config_models import (
    LoRARegistryEntry,
    ModelRegistryEntry,
    ProjectConfig,
    WorkflowStageConfig,
)
from pct.settings import service

router = APIRouter()


# ---------------------------------------------------------------------------
# File Browser
# ---------------------------------------------------------------------------


class FileEntry(PydanticBaseModel):
    name: str
    path: str
    is_dir: bool


@router.get("/browse-files", response_model=list[FileEntry])
async def browse_files(
    path: str = Query("", description="Directory to list. Empty = home directory."),
    _user: dict = Depends(get_current_user),
):
    """List files and directories at the given path for the file browser."""
    target = Path(path) if path else Path.home()
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    entries: list[FileEntry] = []
    try:
        for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if item.name.startswith("."):
                continue
            entries.append(FileEntry(
                name=item.name,
                path=str(item),
                is_dir=item.is_dir(),
            ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    return entries


# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------


@router.get("/models", response_model=list[ModelRegistryEntry])
async def list_models(_user: dict = Depends(get_current_user)):
    return service.list_models()


@router.post("/models", response_model=ModelRegistryEntry, status_code=status.HTTP_201_CREATED)
async def create_model(entry: ModelRegistryEntry, _user: dict = Depends(get_current_user)):
    if service.get_model(entry.id):
        raise HTTPException(status_code=400, detail=f"Model '{entry.id}' already exists")
    return service.create_model(entry)


@router.get("/models/{model_id}", response_model=ModelRegistryEntry)
async def get_model(model_id: str, _user: dict = Depends(get_current_user)):
    m = service.get_model(model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return m


@router.put("/models/{model_id}", response_model=ModelRegistryEntry)
async def update_model(model_id: str, entry: ModelRegistryEntry, _user: dict = Depends(get_current_user)):
    m = service.update_model(model_id, entry)
    if m is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return m


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: str, _user: dict = Depends(get_current_user)):
    if not service.delete_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")


# ---------------------------------------------------------------------------
# LoRA Registry
# ---------------------------------------------------------------------------


@router.get("/loras", response_model=list[LoRARegistryEntry])
async def list_loras(_user: dict = Depends(get_current_user)):
    return service.list_loras()


@router.post("/loras", response_model=LoRARegistryEntry, status_code=status.HTTP_201_CREATED)
async def create_lora(entry: LoRARegistryEntry, _user: dict = Depends(get_current_user)):
    if service.get_lora(entry.id):
        raise HTTPException(status_code=400, detail=f"LoRA '{entry.id}' already exists")
    return service.create_lora(entry)


@router.get("/loras/{lora_id}", response_model=LoRARegistryEntry)
async def get_lora(lora_id: str, _user: dict = Depends(get_current_user)):
    l = service.get_lora(lora_id)
    if l is None:
        raise HTTPException(status_code=404, detail="LoRA not found")
    return l


@router.put("/loras/{lora_id}", response_model=LoRARegistryEntry)
async def update_lora(lora_id: str, entry: LoRARegistryEntry, _user: dict = Depends(get_current_user)):
    l = service.update_lora(lora_id, entry)
    if l is None:
        raise HTTPException(status_code=404, detail="LoRA not found")
    return l


@router.delete("/loras/{lora_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lora(lora_id: str, _user: dict = Depends(get_current_user)):
    if not service.delete_lora(lora_id):
        raise HTTPException(status_code=404, detail="LoRA not found")


# ---------------------------------------------------------------------------
# Project Config
# ---------------------------------------------------------------------------


class ProjectStatus(PydanticBaseModel):
    initialized: bool
    project_directory: str


@router.get("/project/status", response_model=ProjectStatus)
async def get_project_status(_user: dict = Depends(get_current_user)):
    from pct import config
    cfg = service.get_project_config()
    root = config.settings.project_root
    if cfg is None:
        return ProjectStatus(initialized=False, project_directory=root)
    initialized = bool(cfg.project_name and cfg.project_type)
    return ProjectStatus(initialized=initialized, project_directory=root)


@router.get("/project", response_model=ProjectConfig | None)
async def get_project_config(_user: dict = Depends(get_current_user)):
    return service.get_project_config()


@router.put("/project", response_model=ProjectConfig)
async def save_project_config(cfg: ProjectConfig, _user: dict = Depends(get_current_user)):
    return service.save_project_config(cfg)


# ---------------------------------------------------------------------------
# Agents (sub-resource of project config)
# ---------------------------------------------------------------------------


@router.get("/agents", response_model=list[AgentConfig])
async def list_agents(_user: dict = Depends(get_current_user)):
    return service.list_agents()


@router.post("/agents", response_model=AgentConfig, status_code=status.HTTP_201_CREATED)
async def create_agent(agent: AgentConfig, _user: dict = Depends(get_current_user)):
    if service.get_agent(agent.id):
        raise HTTPException(status_code=400, detail=f"Agent '{agent.id}' already exists")
    return service.create_agent(agent)


@router.get("/agents/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str, _user: dict = Depends(get_current_user)):
    a = service.get_agent(agent_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return a


@router.put("/agents/{agent_id}", response_model=AgentConfig)
async def update_agent(agent_id: str, agent: AgentConfig, _user: dict = Depends(get_current_user)):
    a = service.update_agent(agent_id, agent)
    if a is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return a


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, _user: dict = Depends(get_current_user)):
    if not service.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")


# ---------------------------------------------------------------------------
# Workflow Stages
# ---------------------------------------------------------------------------


@router.get("/workflow-stages", response_model=list[WorkflowStageConfig])
async def get_workflow_stages(_user: dict = Depends(get_current_user)):
    return service.get_workflow_stages()


@router.put("/workflow-stages", response_model=list[WorkflowStageConfig])
async def save_workflow_stages(
    stages: list[WorkflowStageConfig], _user: dict = Depends(get_current_user)
):
    return service.save_workflow_stages(stages)
