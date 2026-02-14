"""Pydantic models for project configuration, model registry, and LoRA registry."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator

from pct.agent.models import AgentConfig, AgentType, ProviderType  # noqa: F401


class TaskStatus(str, Enum):
    """Workflow stages a task passes through."""

    REFINE_SPEC = "refine-spec"
    IMPLEMENT = "implement"
    FEATURE_TEST = "feature-test"
    CODE_REVIEW = "code-review"
    USER_APPROVAL = "user-approval"
    MERGE = "merge"
    FULL_TEST = "full-test"
    REFACTOR_CHECK = "refactor-check"
    PUSH = "push"
    DONE = "done"


class ModelRegistryEntry(BaseModel):
    """A model available in the global registry."""

    id: str
    provider_type: ProviderType
    model_id: str
    context_length: int
    model_path: str | None = None
    api_base: str | None = None

    @model_validator(mode="after")
    def require_model_path_for_local(self) -> ModelRegistryEntry:
        if self.provider_type == ProviderType.LOCAL_LLM and not self.model_path:
            raise ValueError("model_path is required for local models")
        return self


class LoRARegistryEntry(BaseModel):
    """A LoRA adapter in the global registry."""

    id: str
    base_model: str
    path: str
    description: str = ""
    created: datetime | None = None


class WorkflowStageConfig(BaseModel):
    """Configuration for a single workflow stage."""

    stage: TaskStatus
    enabled: bool = True
    agent: str | None = None


class ConcurrencyConfig(BaseModel):
    """Concurrency limits for agent execution."""

    remote_api_limit: int = 2
    local_gpu_limit: int = 1


class ContextConfig(BaseModel):
    """Context assembly settings."""

    token_budget: int = 8000
    context_manager_model: str = ""


class ProjectConfig(BaseModel):
    """Top-level project configuration stored in .pct/pct.yaml."""

    project_id: str = ""
    project_name: str = ""
    project_type: str = ""
    agents: list[AgentConfig] = []
    workflow_stages: list[WorkflowStageConfig] = []
    planning_agent: str = ""
    default_agent: str = ""
    auto_advance: bool = True
    concurrency: ConcurrencyConfig = ConcurrencyConfig()
    context: ContextConfig = ContextConfig()
