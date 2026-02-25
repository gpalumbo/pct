"""Pydantic models for project configuration, model registry, and LoRA registry."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator

from pct.agent.models import AgentConfig, AgentType, ProviderType  # noqa: F401


class ModelRegistryEntry(BaseModel):
    """A model available in the global registry."""

    id: str
    provider_type: ProviderType
    model_id: str
    context_length: int
    model_path: str | None = None
    api_base: str | None = None
    download_status: str | None = None  # pending | downloading | ready | error

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


class ArtifactTypeConfig(BaseModel):
    """Configuration for an artifact type with LLM prompt hint."""

    id: str
    label: str
    template_hint: str = ""


class TemplateVariable(BaseModel):
    """A user-defined template variable for stage prompt expansion."""

    key: str          # e.g. "project_style"  (used as {{project_style}} in prompts)
    description: str = ""
    value: str = ""   # static text substituted at prompt-expansion time


class WorkflowStageConfig(BaseModel):
    """Configuration for a single workflow stage."""

    stage: str
    label: str = ""
    enabled: bool = True
    agent: str | None = None
    prompt_template: str = ""


class ConcurrencyConfig(BaseModel):
    """Concurrency limits for agent execution."""

    remote_api_limit: int = 2
    local_gpu_limit: int = 1


class ProjectConfig(BaseModel):
    """Top-level project configuration stored in pct.yaml at the project root."""

    project_id: str = ""
    project_name: str = ""
    project_type: str = ""
    project_directory: str = ""
    agents: list[AgentConfig] = []
    workflow_stages: list[WorkflowStageConfig] = []
    template_variables: list[TemplateVariable] = []
    artifact_types: list[ArtifactTypeConfig] = []
    planning_agent: str = ""
    default_agent: str = ""
    auto_advance: bool = True
    concurrency: ConcurrencyConfig = ConcurrencyConfig()
