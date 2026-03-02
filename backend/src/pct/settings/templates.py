"""Project templates — coding and writing presets."""

from pathlib import Path

from pct.models.agents import Agent, ModelRegistryEntry
from pct.models.core import Project
from pct.models.enums import AgentType, ProviderType
from pct.models.workflow import ArtifactType, WorkflowStage

CODING_STAGES = [
    WorkflowStage(id="refine-spec", label="Refine Spec", sort_order=0),
    WorkflowStage(id="implement", label="Implement", sort_order=1),
    WorkflowStage(id="feature-test", label="Feature Test", sort_order=2),
    WorkflowStage(id="code-review", label="Code Review", sort_order=3),
    WorkflowStage(id="merge", label="Merge", sort_order=4),
    WorkflowStage(id="full-test", label="Full Test Suite", sort_order=5),
    WorkflowStage(id="push", label="Push", sort_order=6),
    WorkflowStage(id="done", label="Done", sort_order=7),
]

WRITING_STAGES = [
    WorkflowStage(
        id="concept", label="Concept", sort_order=0,
        prompt_template=(
            "Help the user brainstorm and develop the core concept."
            " Read {{artifact}} if it exists and suggest expansions."
        ),
    ),
    WorkflowStage(
        id="outline", label="Outline", sort_order=1,
        prompt_template=(
            "Help structure and outline the content."
            " Reference {{cross_refs}} for world consistency."
        ),
    ),
    WorkflowStage(
        id="draft", label="Draft", sort_order=2,
        prompt_template=(
            "Write or expand the draft. Use {{artifact}} as the working document."
            " Reference {{cross_refs}} for world consistency."
        ),
    ),
    WorkflowStage(
        id="revise", label="Revise", sort_order=3,
        prompt_template=(
            "Review {{artifact}} for quality, consistency, and completeness."
            " Cross-check against {{cross_refs}}. Suggest specific improvements."
        ),
    ),
    WorkflowStage(
        id="polish", label="Polish", sort_order=4,
        prompt_template=(
            "Final polish of {{artifact}}. Fix grammar, improve prose,"
            " ensure consistency with {{cross_refs}}."
        ),
    ),
    WorkflowStage(id="done", label="Done", sort_order=5),
]

CODING_ARTIFACT_TYPES = [
    ArtifactType(id="text", label="Text"),
]

WRITING_ARTIFACT_TYPES = [
    ArtifactType(id="timeline", label="Timeline & History"),
    ArtifactType(id="location", label="Location"),
    ArtifactType(id="character", label="Character"),
    ArtifactType(id="faction", label="Faction / Organization"),
    ArtifactType(id="magic-system", label="Magic & Religion"),
    ArtifactType(id="technology", label="Technology"),
    ArtifactType(id="item", label="Item / Artifact"),
    ArtifactType(id="story-arc", label="Story Arc"),
    ArtifactType(id="chapter", label="Chapter"),
    ArtifactType(id="text", label="Text"),
]


def _scan_gguf_dir(directory: Path) -> list[ModelRegistryEntry]:
    """Scan a directory for .gguf files and return ModelRegistryEntry objects."""
    if not directory.is_dir():
        return []
    entries = []
    for gguf_file in sorted(directory.glob("*.gguf")):
        model_id = gguf_file.stem.lower().replace(" ", "-")
        entries.append(ModelRegistryEntry(
            id=model_id,
            name=gguf_file.stem,
            provider_type=ProviderType.local,
            model_identifier=model_id,
            file_path=str(gguf_file),
        ))
    return entries


def discover_models(
    project_root: Path,
    global_config_dir: Path,
) -> list[ModelRegistryEntry]:
    """Discover models from the search path and existing registry.

    Search order (later entries do NOT overwrite earlier ones):
      1. $PCT_PROJECT_ROOT/models/  (scan .gguf)
      2. $PCT_ROOT/models/          (scan .gguf)  — global_config_dir/models/
      3. ~/.pct/registries/models.yaml  (existing registry entries)
    """
    from pct.storage.registry_io import load_model_registry

    seen_ids: set[str] = set()
    models: list[ModelRegistryEntry] = []

    # Scan directories for .gguf files
    for scan_dir in [project_root / "models", global_config_dir / "models"]:
        for entry in _scan_gguf_dir(scan_dir):
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                models.append(entry)

    # Load existing registry entries
    for entry in load_model_registry(global_config_dir):
        if entry.id not in seen_ids:
            seen_ids.add(entry.id)
            models.append(entry)

    return models


def _create_default_agents(models: list[ModelRegistryEntry]) -> list[Agent]:
    """Create a USER agent plus one LLM agent per discovered model."""
    agents: list[Agent] = [
        Agent(
            id="user",
            name="User",
            agent_type=AgentType.user,
            model_id="",
        ),
    ]
    for model in models:
        agent_id = f"agent-{model.id}"
        agents.append(Agent(
            id=agent_id,
            name=model.name,
            agent_type=AgentType.llm,
            model_id=model.id,
        ))
    return agents


def create_project_from_template(
    project_id: str,
    name: str,
    template: str,
    directory: str = "",
    models: list[ModelRegistryEntry] | None = None,
) -> Project:
    """Create a Project with template-appropriate stages, artifact types, and agents."""
    if template == "writing":
        stages = WRITING_STAGES
        artifact_types = WRITING_ARTIFACT_TYPES
    else:
        stages = CODING_STAGES
        artifact_types = CODING_ARTIFACT_TYPES

    agents = _create_default_agents(models or [])

    # Pick first LLM agent as default, fall back to user
    llm_agents = [a for a in agents if a.agent_type == AgentType.llm]
    default_id = llm_agents[0].id if llm_agents else "user"

    return Project(
        id=project_id,
        name=name,
        project_type=template,
        directory=directory,
        workflow_stages=stages,
        artifact_types=artifact_types,
        agents=agents,
        default_agent_id=default_id,
        planning_agent_id=default_id,
    )
