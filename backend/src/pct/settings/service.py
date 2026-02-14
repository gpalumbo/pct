"""YAML-based CRUD service for project configuration and global registries."""

from __future__ import annotations

from pathlib import Path

import yaml

from pct import config
from pct.agent.models import AgentConfig
from pct.config_models import (
    LoRARegistryEntry,
    ModelRegistryEntry,
    ProjectConfig,
    WorkflowStageConfig,
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_registries_dir() -> Path:
    if config.settings.registries_dir:
        return Path(config.settings.registries_dir)
    return Path.home() / ".pct" / "registries"


def _get_project_config_path() -> Path:
    if config.settings.project_root:
        root = Path(config.settings.project_root)
    else:
        root = Path.cwd()
    return root / ".pct" / "pct.yaml"


# ---------------------------------------------------------------------------
# Generic YAML I/O
# ---------------------------------------------------------------------------


def _load_yaml_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


def _save_yaml_list(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def _load_yaml_dict(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None


def _save_yaml_dict(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Model Registry CRUD (~/.pct/registries/models.yaml)
# ---------------------------------------------------------------------------


def _models_path() -> Path:
    return _get_registries_dir() / "models.yaml"


def list_models() -> list[ModelRegistryEntry]:
    return [ModelRegistryEntry(**m) for m in _load_yaml_list(_models_path())]


def get_model(model_id: str) -> ModelRegistryEntry | None:
    for m in _load_yaml_list(_models_path()):
        if m.get("id") == model_id:
            return ModelRegistryEntry(**m)
    return None


def create_model(entry: ModelRegistryEntry) -> ModelRegistryEntry:
    items = _load_yaml_list(_models_path())
    items.append(entry.model_dump(mode="json", exclude_none=True))
    _save_yaml_list(_models_path(), items)
    return entry


def update_model(model_id: str, entry: ModelRegistryEntry) -> ModelRegistryEntry | None:
    items = _load_yaml_list(_models_path())
    for i, m in enumerate(items):
        if m.get("id") == model_id:
            items[i] = entry.model_dump(mode="json", exclude_none=True)
            _save_yaml_list(_models_path(), items)
            return entry
    return None


def delete_model(model_id: str) -> bool:
    items = _load_yaml_list(_models_path())
    new_items = [m for m in items if m.get("id") != model_id]
    if len(new_items) == len(items):
        return False
    _save_yaml_list(_models_path(), new_items)
    return True


# ---------------------------------------------------------------------------
# LoRA Registry CRUD (~/.pct/registries/loras.yaml)
# ---------------------------------------------------------------------------


def _loras_path() -> Path:
    return _get_registries_dir() / "loras.yaml"


def list_loras() -> list[LoRARegistryEntry]:
    return [LoRARegistryEntry(**l) for l in _load_yaml_list(_loras_path())]


def get_lora(lora_id: str) -> LoRARegistryEntry | None:
    for l in _load_yaml_list(_loras_path()):
        if l.get("id") == lora_id:
            return LoRARegistryEntry(**l)
    return None


def create_lora(entry: LoRARegistryEntry) -> LoRARegistryEntry:
    items = _load_yaml_list(_loras_path())
    items.append(entry.model_dump(mode="json", exclude_none=True))
    _save_yaml_list(_loras_path(), items)
    return entry


def update_lora(lora_id: str, entry: LoRARegistryEntry) -> LoRARegistryEntry | None:
    items = _load_yaml_list(_loras_path())
    for i, l in enumerate(items):
        if l.get("id") == lora_id:
            items[i] = entry.model_dump(mode="json", exclude_none=True)
            _save_yaml_list(_loras_path(), items)
            return entry
    return None


def delete_lora(lora_id: str) -> bool:
    items = _load_yaml_list(_loras_path())
    new_items = [l for l in items if l.get("id") != lora_id]
    if len(new_items) == len(items):
        return False
    _save_yaml_list(_loras_path(), new_items)
    return True


# ---------------------------------------------------------------------------
# Project Config (.pct/pct.yaml)
# ---------------------------------------------------------------------------


def get_project_config() -> ProjectConfig | None:
    try:
        path = _get_project_config_path()
    except FileNotFoundError:
        return None
    data = _load_yaml_dict(path)
    if data is None:
        return None
    return ProjectConfig(**data)


def save_project_config(cfg: ProjectConfig) -> ProjectConfig:
    path = _get_project_config_path()
    _save_yaml_dict(path, cfg.model_dump(mode="json"))
    return cfg


# ---------------------------------------------------------------------------
# Agent CRUD (sub-resource of project config)
# ---------------------------------------------------------------------------


def list_agents() -> list[AgentConfig]:
    cfg = get_project_config()
    if cfg is None:
        return []
    return cfg.agents


def get_agent(agent_id: str) -> AgentConfig | None:
    for a in list_agents():
        if a.id == agent_id:
            return a
    return None


def create_agent(agent: AgentConfig) -> AgentConfig:
    cfg = get_project_config()
    if cfg is None:
        cfg = ProjectConfig()
    cfg.agents.append(agent)
    save_project_config(cfg)
    return agent


def update_agent(agent_id: str, agent: AgentConfig) -> AgentConfig | None:
    cfg = get_project_config()
    if cfg is None:
        return None
    for i, a in enumerate(cfg.agents):
        if a.id == agent_id:
            cfg.agents[i] = agent
            save_project_config(cfg)
            return agent
    return None


def delete_agent(agent_id: str) -> bool:
    cfg = get_project_config()
    if cfg is None:
        return False
    new_agents = [a for a in cfg.agents if a.id != agent_id]
    if len(new_agents) == len(cfg.agents):
        return False
    cfg.agents = new_agents
    save_project_config(cfg)
    return True


# ---------------------------------------------------------------------------
# Workflow Stages (sub-resource of project config)
# ---------------------------------------------------------------------------


def get_workflow_stages() -> list[WorkflowStageConfig]:
    cfg = get_project_config()
    if cfg is None:
        return []
    return cfg.workflow_stages


def save_workflow_stages(stages: list[WorkflowStageConfig]) -> list[WorkflowStageConfig]:
    cfg = get_project_config()
    if cfg is None:
        cfg = ProjectConfig()
    cfg.workflow_stages = stages
    save_project_config(cfg)
    return stages
