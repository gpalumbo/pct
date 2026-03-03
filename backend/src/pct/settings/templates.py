"""Project templates — coding and writing presets."""

import re
from pathlib import Path

from pct.models.agents import Agent, ModelRegistryEntry
from pct.models.core import Project
from pct.models.enums import AgentType, ProviderType
from pct.models.workflow import ArtifactType, WorkflowStage

# Matches GGUF split shard pattern: -NNNNN-of-NNNNN.gguf
_GGUF_SHARD_RE = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)

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


def _scan_gguf(directory: Path) -> list[ModelRegistryEntry]:
    """Recursively scan for .gguf files.

    For split models (e.g. model-00001-of-00002.gguf), only register the first
    shard — llama.cpp auto-discovers the rest.  The model ID is derived from the
    base name (without the shard suffix).
    """
    if not directory.is_dir():
        return []
    entries = []
    for gguf_file in sorted(directory.glob("**/*.gguf")):
        shard_match = _GGUF_SHARD_RE.search(gguf_file.name)
        if shard_match:
            shard_num = int(shard_match.group(1))
            if shard_num != 1:
                continue  # skip non-first shards
            # Use base name without shard suffix as the model name
            base_name = gguf_file.name[:shard_match.start()]
        else:
            base_name = gguf_file.stem

        model_id = base_name.lower().replace(" ", "-")
        entries.append(ModelRegistryEntry(
            id=model_id,
            name=base_name,
            provider_type=ProviderType.local,
            model_identifier=model_id,
            file_path=str(gguf_file),
        ))
    return entries


def _scan_safetensors(directory: Path) -> list[ModelRegistryEntry]:
    """Scan for safetensor model directories.

    Detects two layouts:
      - Diffusers pipelines: directory containing model_index.json
      - Sharded LLMs: directory containing model.safetensors.index.json

    In both cases the directory itself is registered as file_path (the entry
    point for from_pretrained()).
    """
    if not directory.is_dir():
        return []
    entries = []
    markers = ("model_index.json", "model.safetensors.index.json")
    for marker in markers:
        for marker_file in sorted(directory.glob(f"**/{marker}")):
            model_dir = marker_file.parent
            model_id = model_dir.name.lower().replace(" ", "-")
            if any(e.id == model_id for e in entries):
                continue  # already found via another marker in same dir
            provider = ProviderType.huggingface
            entries.append(ModelRegistryEntry(
                id=model_id,
                name=model_dir.name,
                provider_type=provider,
                model_identifier=model_id,
                file_path=str(model_dir),
            ))
    return entries


def discover_models(
    project_root: Path,
    pct_root: Path,
    global_config_dir: Path,
) -> list[ModelRegistryEntry]:
    """Discover models from the search path and existing registry.

    Search order (later entries do NOT overwrite earlier ones):
      1. $PCT_PROJECT_ROOT/models/  — project-local models
      2. $PCT_ROOT/models/          — PCT deployment directory
      3. ~/.pct/registries/models.yaml  (existing registry entries)

    Scans for:
      - .gguf files (single and split-shard, for llama.cpp)
      - Safetensor directories (diffusers pipelines and sharded LLMs)
    """
    from pct.storage.registry_io import load_model_registry

    seen_ids: set[str] = set()
    models: list[ModelRegistryEntry] = []

    def _add(entry: ModelRegistryEntry) -> None:
        if entry.id not in seen_ids:
            seen_ids.add(entry.id)
            models.append(entry)

    for scan_dir in [project_root / "models", pct_root / "models"]:
        for entry in _scan_gguf(scan_dir):
            _add(entry)
        for entry in _scan_safetensors(scan_dir):
            _add(entry)

    for entry in load_model_registry(global_config_dir):
        _add(entry)

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


# ---------------------------------------------------------------------------
# Initial feature/task definitions per template
# ---------------------------------------------------------------------------

CODING_INITIAL_FEATURES: list[dict] = [
    {
        "id": "f1-project-setup",
        "title": "Project Setup",
        "tasks": [
            {"id": "setup-structure", "title": "Set up project structure and dependencies"},
            {"id": "setup-lint", "title": "Configure linting and formatting"},
            {"id": "setup-ci", "title": "Add CI/CD pipeline"},
            {"id": "setup-readme", "title": "Write initial README"},
        ],
    },
]

WRITING_INITIAL_FEATURES: list[dict] = [
    {
        "id": "f0-timeline",
        "title": "Timeline & History",
        "tasks": [
            {"id": "chronology", "title": "Establish world chronology", "artifact_type_id": "timeline"},
        ],
    },
    {
        "id": "f1-locations",
        "title": "Locations",
        "tasks": [
            {"id": "regions", "title": "Define major regions and geography", "artifact_type_id": "location"},
            {"id": "cities", "title": "Detail key cities and landmarks", "artifact_type_id": "location"},
        ],
    },
    {
        "id": "f2-characters",
        "title": "Characters",
        "tasks": [
            {"id": "protagonist", "title": "Create protagonist profile", "artifact_type_id": "character"},
            {"id": "antagonist", "title": "Create antagonist profile", "artifact_type_id": "character"},
        ],
    },
    {
        "id": "f3-factions",
        "title": "Factions & Organizations",
        "tasks": [
            {"id": "factions-overview", "title": "Outline major factions and power structures", "artifact_type_id": "faction"},
            {"id": "faction-relations", "title": "Define faction relationships and conflicts", "artifact_type_id": "faction"},
        ],
    },
    {
        "id": "f4-magic-religion",
        "title": "Magic & Religion",
        "tasks": [
            {"id": "magic-rules", "title": "Define magic system rules and limitations", "artifact_type_id": "magic-system"},
            {"id": "religion", "title": "Outline religious traditions and beliefs", "artifact_type_id": "magic-system"},
        ],
    },
    {
        "id": "f5-technology",
        "title": "Technology",
        "tasks": [
            {"id": "tech-level", "title": "Define technology level and key inventions", "artifact_type_id": "technology"},
        ],
    },
    {
        "id": "f6-items",
        "title": "Items & Artifacts",
        "tasks": [
            {"id": "items-catalog", "title": "Catalog significant items and their origins", "artifact_type_id": "item"},
        ],
    },
]


def get_initial_features(template: str) -> list[dict]:
    """Return the initial feature/task definitions for a project template."""
    if template == "writing":
        return WRITING_INITIAL_FEATURES
    return CODING_INITIAL_FEATURES


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
