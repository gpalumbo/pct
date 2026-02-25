"""YAML-based CRUD service for project configuration and global registries."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from pct import config
from pct.agent.models import AgentConfig, AgentType, ProviderType
from pct.config_models import (
    LoRARegistryEntry,
    ModelRegistryEntry,
    ProjectConfig,
    WorkflowStageConfig,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_registries_dir() -> Path:
    if config.settings.registries_dir:
        return Path(config.settings.registries_dir)
    return Path.home() / ".pct" / "registries"


def _get_project_root() -> Path:
    if config.settings.project_root:
        return Path(config.settings.project_root)
    return Path.cwd()


def _get_project_config_path() -> Path:
    return _get_project_root() / "pct.yaml"


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
# Project Config (pct.yaml at project root)
# ---------------------------------------------------------------------------


def get_project_config() -> ProjectConfig | None:
    try:
        path = _get_project_config_path()
    except FileNotFoundError:
        return None
    data = _load_yaml_dict(path)
    if data is None:
        return None
    cfg = ProjectConfig(**data)
    cfg.project_directory = config.settings.project_root
    return cfg


def save_project_config(cfg: ProjectConfig) -> ProjectConfig:
    # Derive project_id from directory name if empty
    if not cfg.project_id:
        cfg.project_id = _get_project_root().name

    # Auto-apply template if this is initial setup (no stages yet)
    if not cfg.workflow_stages and cfg.project_type:
        from pct.settings.templates import get_template

        tpl = get_template(cfg.project_type)
        if tpl:
            cfg.workflow_stages = [
                WorkflowStageConfig(**s) for s in tpl["stages"]
            ]
            _apply_initial_feature(tpl)
        _apply_default_agents(cfg)
        _create_work_index()
        _index_existing_work(cfg)

    path = _get_project_config_path()
    data = cfg.model_dump(mode="json")
    data.pop("project_directory", None)
    _save_yaml_dict(path, data)
    cfg.project_directory = config.settings.project_root
    return cfg


def _apply_initial_feature(tpl: dict) -> None:
    """Create the initial feature(s) and tasks from a project template.

    Supports both singular ``initial_feature`` (backward-compat) and plural
    ``initial_features`` list for templates that create multiple features.
    """
    from pct.board.service import create_feature, create_task
    from pct.board.models import CreateFeatureRequest, CreateTaskRequest

    first_stage = tpl["stages"][0]["stage"] if tpl["stages"] else "todo"

    # Collect feature templates — plural key takes precedence
    feat_templates: list[dict] = list(tpl.get("initial_features", []))
    singular = tpl.get("initial_feature")
    if singular and not feat_templates:
        feat_templates = [singular]

    for feat_tpl in feat_templates:
        create_feature(CreateFeatureRequest(
            id=feat_tpl["id"],
            title=feat_tpl["title"],
        ))
        for task_tpl in feat_tpl.get("tasks", []):
            create_task(feat_tpl["id"], CreateTaskRequest(
                title=task_tpl["title"],
                status=first_stage,
                artifact_type=task_tpl.get("artifact_type", "text"),
            ))


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


# ---------------------------------------------------------------------------
# Model auto-discovery
# ---------------------------------------------------------------------------


def scan_and_register_models() -> list[ModelRegistryEntry]:
    """Scan model directories for .gguf and .safetensors files, register new ones.

    Supports two layouts:
    - Flat:   models/my-model.gguf  → id = "my-model"
    - Nested: models/qwen2.5-7b/qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf
              → id = "qwen2.5-7b" (parent dir name, registered once)
    """
    search_paths: list[Path] = []

    # Project-local models take precedence
    project_models = _get_project_root() / "models"
    if project_models.is_dir():
        search_paths.append(project_models)

    # PCT_ROOT/models as fallback
    if config.settings.root:
        pct_root_models = Path(config.settings.root) / "models"
        if pct_root_models.is_dir():
            search_paths.append(pct_root_models)

    existing = {m.id for m in list_models()}
    registered: list[ModelRegistryEntry] = []

    for models_dir in search_paths:
        for f in sorted(models_dir.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".gguf", ".safetensors"):
                continue

            # Determine model id: use parent dir name if nested, else file stem
            if f.parent != models_dir:
                model_id = f.parent.name
            else:
                model_id = f.stem

            if model_id in existing:
                continue

            if f.suffix == ".gguf":
                entry = ModelRegistryEntry(
                    id=model_id,
                    provider_type=ProviderType.LOCAL_LLM,
                    model_id=model_id,
                    context_length=4096,
                    model_path=str(f.parent if f.parent != models_dir else f),
                )
            else:
                entry = ModelRegistryEntry(
                    id=model_id,
                    provider_type=ProviderType.LOCAL_LLM,
                    model_id=model_id,
                    context_length=0,
                    model_path=str(f.parent if f.parent != models_dir else f),
                )

            create_model(entry)
            existing.add(model_id)
            registered.append(entry)

    return registered


# ---------------------------------------------------------------------------
# Default agents on project init
# ---------------------------------------------------------------------------


def _apply_default_agents(cfg: ProjectConfig) -> None:
    """Create default agents: user agent + one agent per discovered model."""
    existing_ids = {a.id for a in cfg.agents}

    # Always create a "user" agent
    if "user" not in existing_ids:
        cfg.agents.append(AgentConfig(
            id="user",
            agent_type=AgentType.USER,
            provider_type=ProviderType.USER,
            model="",
        ))
        existing_ids.add("user")

    # Discover and register models first
    scan_and_register_models()

    # Create agents for all registered models
    for model in list_models():
        if model.id in existing_ids:
            continue
        # Determine agent type from model file extension
        agent_type = AgentType.LLM
        if model.model_path and model.model_path.endswith(".safetensors"):
            agent_type = AgentType.IMAGEGEN

        cfg.agents.append(AgentConfig(
            id=model.id,
            agent_type=agent_type,
            provider_type=model.provider_type,
            model=model.model_id,
        ))
        existing_ids.add(model.id)


# ---------------------------------------------------------------------------
# Work index (work/INDEX.md)
# ---------------------------------------------------------------------------


def _create_work_index() -> None:
    """Walk work/ dir, write markdown index with relative links."""
    work_dir = _get_project_root() / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    _write_work_index(work_dir)


def _write_work_index(work_dir: Path) -> None:
    """Generate INDEX.md for the work directory."""
    lines = ["# Work Artifacts Index", ""]
    for item in sorted(work_dir.rglob("*")):
        if item.name == "INDEX.md":
            continue
        if item.is_file():
            rel = item.relative_to(work_dir)
            lines.append(f"- [{rel}]({rel.as_posix()})")
    if len(lines) == 2:
        lines.append("_No artifacts yet._")
    lines.append("")
    (work_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def regenerate_work_index() -> None:
    """Public wrapper to re-generate work/INDEX.md."""
    work_dir = _get_project_root() / "work"
    if work_dir.is_dir():
        _write_work_index(work_dir)


# ---------------------------------------------------------------------------
# RAG indexing helpers
# ---------------------------------------------------------------------------


def _index_existing_work(cfg: ProjectConfig) -> None:
    """Index existing files under work/ into RAG on project init."""
    work_dir = _get_project_root() / "work"
    if not work_dir.is_dir():
        return
    project_id = cfg.project_id
    if not project_id:
        return
    try:
        from pct.rag.indexer import index_directory
        index_directory(project_id, work_dir)
    except ImportError:
        logger.debug("RAG dependencies not available, skipping index")
    except Exception:
        logger.exception("Failed to index existing work")


def reindex_project() -> dict:
    """Re-index work/ directory: regenerate INDEX.md and RAG index."""
    regenerate_work_index()

    cfg = get_project_config()
    if cfg is None:
        return {"indexed": 0, "error": "No project config"}

    work_dir = _get_project_root() / "work"
    if not work_dir.is_dir():
        return {"indexed": 0}

    try:
        from pct.rag.indexer import reindex_all
        count = reindex_all(cfg.project_id, work_dir)
        return {"indexed": count}
    except ImportError:
        return {"indexed": 0, "error": "RAG dependencies not installed"}
    except Exception as exc:
        logger.exception("Reindex failed")
        return {"indexed": 0, "error": str(exc)}
