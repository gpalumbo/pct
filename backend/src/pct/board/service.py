"""YAML / frontmatter CRUD service for Features, Tasks, and the Kanban board."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import frontmatter
import yaml

from pct import config
from pct.board.models import (
    BacklogFeature,
    BoardResponse,
    CreateFeatureRequest,
    CreateTaskRequest,
    Feature,
    FeatureMetadata,
    FeatureStage,
    MoveTaskRequest,
    ReassignTaskRequest,
    Task,
    UpdateFeatureMetadataRequest,
    UpdateTaskRequest,
)
from pct.config_models import WorkflowStageConfig


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    if config.settings.project_root:
        return Path(config.settings.project_root)
    return Path.cwd()


def _active_features_dir() -> Path:
    return _project_root() / ".pct" / "active-features"


def _backlog_dir() -> Path:
    return _project_root() / ".pct" / "feature_backlog"


# ---------------------------------------------------------------------------
# Generic YAML I/O
# ---------------------------------------------------------------------------


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
# Feature spec I/O
# ---------------------------------------------------------------------------


def _feature_dir(feature_id: str) -> Path:
    return _active_features_dir() / feature_id


def _load_feature_spec(feature_id: str) -> str:
    path = _feature_dir(feature_id) / "feature_spec.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _save_feature_spec(feature_id: str, spec: str) -> None:
    path = _feature_dir(feature_id) / "feature_spec.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec, encoding="utf-8")


# ---------------------------------------------------------------------------
# Feature metadata I/O
# ---------------------------------------------------------------------------


def _load_feature_metadata(feature_id: str) -> FeatureMetadata:
    path = _feature_dir(feature_id) / "metadata.yaml"
    data = _load_yaml_dict(path)
    if data is None:
        return FeatureMetadata()
    return FeatureMetadata(**data)


def _save_feature_metadata(feature_id: str, meta: FeatureMetadata) -> None:
    path = _feature_dir(feature_id) / "metadata.yaml"
    _save_yaml_dict(path, meta.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Task I/O  (YAML frontmatter + markdown body)
# ---------------------------------------------------------------------------


def _tasks_dir(feature_id: str) -> Path:
    return _feature_dir(feature_id) / "tasks"


def _find_task_file(feature_id: str, task_id: str) -> Path | None:
    """Find a task file by ID prefix match (e.g. '001' matches '001-my-task.md')."""
    tasks = _tasks_dir(feature_id)
    if not tasks.exists():
        return None
    for p in tasks.iterdir():
        if p.is_file() and p.name.startswith(task_id + "-"):
            return p
    return None


def _load_task(feature_id: str, path: Path) -> Task:
    """Load a task from its frontmatter-markdown file."""
    post = frontmatter.load(str(path))
    meta = dict(post.metadata)
    meta["body"] = post.content
    meta["feature"] = feature_id
    return Task(**meta)


def _save_task(feature_id: str, task: Task) -> None:
    """Save a task as a YAML-frontmatter + markdown file."""
    tasks = _tasks_dir(feature_id)
    tasks.mkdir(parents=True, exist_ok=True)

    # Remove old file if it exists (title/slug may have changed)
    old = _find_task_file(feature_id, task.id)
    if old is not None:
        old.unlink()

    filename = f"{task.id}-{task.slug}.md"
    path = tasks / filename

    # Build frontmatter dict (exclude body, feature)
    data = task.model_dump(mode="json", exclude={"body", "feature", "slug"})
    post = frontmatter.Post(task.body, **data)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")


def _list_tasks(feature_id: str) -> list[Task]:
    tasks = _tasks_dir(feature_id)
    if not tasks.exists():
        return []
    result = []
    for p in sorted(tasks.iterdir()):
        if p.is_file() and p.suffix == ".md":
            result.append(_load_task(feature_id, p))
    return result


def _artifact_slug(text: str, max_words: int = 3) -> str:
    """Create a short underscore-delimited slug from text for artifact paths."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) > max_words:
        words = words[:max_words]
    return "_".join(words) if words else "untitled"


def _get_feature_title(feature_id: str) -> str:
    """Get just the feature title without loading all tasks."""
    spec = _load_feature_spec(feature_id)
    if spec:
        first_line = spec.strip().split("\n", 1)[0]
        title = re.sub(r"^#+\s*", "", first_line).strip()
        if title:
            return title
    return feature_id


def _next_task_id(feature_id: str) -> str:
    """Generate the next sequential task ID (e.g. '001', '002', ...)."""
    existing = _list_tasks(feature_id)
    if not existing:
        return "001"
    max_id = max(int(t.id) for t in existing if t.id.isdigit())
    return f"{max_id + 1:03d}"


# ---------------------------------------------------------------------------
# Feature CRUD
# ---------------------------------------------------------------------------


def list_features() -> list[Feature]:
    base = _active_features_dir()
    if not base.exists():
        return []
    features = []
    for d in sorted(base.iterdir()):
        if d.is_dir():
            feature = _load_feature(d.name)
            if feature is not None:
                features.append(feature)
    return features


def _load_feature(feature_id: str) -> Feature | None:
    d = _feature_dir(feature_id)
    if not d.exists():
        return None
    spec = _load_feature_spec(feature_id)
    meta = _load_feature_metadata(feature_id)
    tasks = _list_tasks(feature_id)
    # Derive title from first heading in spec, or use the ID
    title = feature_id
    if spec:
        first_line = spec.strip().split("\n", 1)[0]
        title = re.sub(r"^#+\s*", "", first_line).strip() or feature_id
    return Feature(id=feature_id, title=title, specification=spec, metadata=meta, tasks=tasks)


def get_feature(feature_id: str) -> Feature | None:
    return _load_feature(feature_id)


def create_feature(req: CreateFeatureRequest) -> Feature:
    d = _feature_dir(req.id)
    d.mkdir(parents=True, exist_ok=True)

    _save_feature_spec(req.id, req.specification)
    meta = req.metadata if req.metadata is not None else FeatureMetadata()
    _save_feature_metadata(req.id, meta)

    return Feature(
        id=req.id,
        title=req.title,
        specification=req.specification,
        metadata=meta,
        tasks=[],
    )


def update_feature_metadata(feature_id: str, req: UpdateFeatureMetadataRequest) -> Feature | None:
    feature = get_feature(feature_id)
    if feature is None:
        return None

    update_data = req.model_dump(exclude_none=True)
    if update_data:
        current = feature.metadata.model_dump(mode="json")
        current.update(update_data)
        current["updated"] = datetime.now(UTC).isoformat()
        new_meta = FeatureMetadata(**current)
        _save_feature_metadata(feature_id, new_meta)
        feature.metadata = new_meta

    return feature


def delete_feature(feature_id: str) -> bool:
    import shutil

    d = _feature_dir(feature_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


def suspend_feature(feature_id: str) -> Feature | None:
    return update_feature_metadata(
        feature_id,
        UpdateFeatureMetadataRequest(lifecycle_stage=FeatureStage.SUSPENDED),
    )


def resume_feature(feature_id: str) -> Feature | None:
    return update_feature_metadata(
        feature_id,
        UpdateFeatureMetadataRequest(lifecycle_stage=FeatureStage.ACTIVE),
    )


# ---------------------------------------------------------------------------
# Backlog CRUD
# ---------------------------------------------------------------------------


def list_backlog() -> list[BacklogFeature]:
    base = _backlog_dir()
    if not base.exists():
        return []
    result = []
    for p in sorted(base.iterdir()):
        if p.is_file() and p.suffix == ".md":
            content = p.read_text(encoding="utf-8")
            name = p.stem
            # Derive title from first heading
            title = name
            if content:
                first_line = content.strip().split("\n", 1)[0]
                title = re.sub(r"^#+\s*", "", first_line).strip() or name
            result.append(BacklogFeature(id=name, title=title, specification=content))
    return result


def create_backlog_feature(feature: BacklogFeature) -> BacklogFeature:
    base = _backlog_dir()
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{feature.id}.md"
    path.write_text(feature.specification, encoding="utf-8")
    return feature


def activate_backlog_feature(backlog_id: str) -> Feature | None:
    """Move a feature from backlog to active-features."""
    base = _backlog_dir()
    path = base / f"{backlog_id}.md"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    title = backlog_id
    if content:
        first_line = content.strip().split("\n", 1)[0]
        title = re.sub(r"^#+\s*", "", first_line).strip() or backlog_id

    feature = create_feature(CreateFeatureRequest(
        id=backlog_id,
        title=title,
        specification=content,
        metadata=FeatureMetadata(lifecycle_stage=FeatureStage.PLANNING),
    ))

    path.unlink()
    return feature


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------


def get_task(feature_id: str, task_id: str) -> Task | None:
    path = _find_task_file(feature_id, task_id)
    if path is None:
        return None
    return _load_task(feature_id, path)


def list_tasks(feature_id: str) -> list[Task]:
    return _list_tasks(feature_id)


def create_task(feature_id: str, req: CreateTaskRequest) -> Task | None:
    if not _feature_dir(feature_id).exists():
        return None

    task_id = _next_task_id(feature_id)

    # Auto-generate artifact path from feature title / task title if not provided
    feature_title = _get_feature_title(feature_id)
    feature_slug = _artifact_slug(feature_title)
    task_slug = _artifact_slug(req.title)
    artifact_path = req.artifact_path or f"work/{feature_slug}/{task_slug}.md"

    task = Task(
        id=task_id,
        title=req.title,
        feature=feature_id,
        status=req.status,
        agent=req.agent,
        depends_on=req.depends_on,
        cross_depends_on=req.cross_depends_on,
        tags=req.tags,
        priority=req.priority,
        artifact_path=artifact_path,
        body=req.body,
        artifact_type=req.artifact_type,
    )
    _save_task(feature_id, task)
    return task


def update_task(feature_id: str, task_id: str, req: UpdateTaskRequest) -> Task | None:
    task = get_task(feature_id, task_id)
    if task is None:
        return None

    update_data = req.model_dump(exclude_none=True)
    if update_data:
        current = task.model_dump(mode="json")
        current.update(update_data)
        current["updated"] = datetime.now(UTC).isoformat()
        task = Task(**current)
        _save_task(feature_id, task)

    return task


def delete_task(feature_id: str, task_id: str) -> bool:
    path = _find_task_file(feature_id, task_id)
    if path is None:
        return False
    path.unlink()
    return True


# ---------------------------------------------------------------------------
# Artifact I/O
# ---------------------------------------------------------------------------


def read_artifact(feature_id: str, task_id: str) -> dict:
    """Read a task's artifact file. Returns {path, content, exists}."""
    task = get_task(feature_id, task_id)
    if task is None:
        return {"path": "", "content": "", "exists": False}

    artifact_path = task.artifact_path
    if not artifact_path:
        return {"path": "", "content": "", "exists": False}

    full_path = _project_root() / artifact_path
    if full_path.exists():
        return {
            "path": artifact_path,
            "content": full_path.read_text(encoding="utf-8"),
            "exists": True,
        }
    return {"path": artifact_path, "content": "", "exists": False}


def write_artifact(feature_id: str, task_id: str, content: str) -> dict:
    """Write content to a task's artifact file. Returns {path, content, exists}."""
    task = get_task(feature_id, task_id)
    if task is None:
        return {"path": "", "content": "", "exists": False}

    artifact_path = task.artifact_path
    if not artifact_path:
        return {"path": "", "content": "", "exists": False}

    full_path = _project_root() / artifact_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return {"path": artifact_path, "content": content, "exists": True}


# ---------------------------------------------------------------------------
# Move task (drag-and-drop)
# ---------------------------------------------------------------------------


def _get_enabled_stages() -> list[str]:
    """Return the ordered list of enabled workflow stage names."""
    from pct.settings.service import get_workflow_stages

    stages: list[WorkflowStageConfig] = get_workflow_stages()
    return [s.stage for s in stages if s.enabled]


def move_task(
    feature_id: str,
    task_id: str,
    req: MoveTaskRequest,
) -> Task | None:
    """Move a task to a new stage, optionally requiring skip confirmation."""
    task = get_task(feature_id, task_id)
    if task is None:
        return None

    enabled = _get_enabled_stages()
    if req.new_status not in enabled:
        raise ValueError(f"Stage '{req.new_status}' is not enabled")

    # Check adjacency
    if task.status in enabled and req.new_status in enabled:
        cur_idx = enabled.index(task.status)
        new_idx = enabled.index(req.new_status)
        if abs(new_idx - cur_idx) > 1 and not req.confirm_skip:
            raise ValueError(
                f"Non-adjacent move from '{task.status}' to '{req.new_status}' "
                "requires confirm_skip=true"
            )

    return update_task(feature_id, task_id, UpdateTaskRequest(status=req.new_status))


# ---------------------------------------------------------------------------
# Reassign task across features
# ---------------------------------------------------------------------------


def reassign_task(req: ReassignTaskRequest) -> Task:
    """Move a task from one feature to another.

    Generates a new sequential ID in the destination feature, copies all
    fields (clearing feature-local depends_on), deletes the source task file,
    and returns the new task.
    """
    src_task = get_task(req.src_feature_id, req.task_id)
    if src_task is None:
        raise ValueError(f"Task '{req.task_id}' not found in feature '{req.src_feature_id}'")

    if not _feature_dir(req.dest_feature_id).exists():
        raise ValueError(f"Destination feature '{req.dest_feature_id}' not found")

    new_id = _next_task_id(req.dest_feature_id)

    new_task = Task(
        id=new_id,
        title=src_task.title,
        feature=req.dest_feature_id,
        status=req.new_status,
        agent=src_task.agent,
        branch=src_task.branch,
        depends_on=[],  # cleared — depends_on is feature-local
        cross_depends_on=src_task.cross_depends_on,
        tags=src_task.tags,
        priority=src_task.priority,
        attempt=src_task.attempt,
        artifact_path=src_task.artifact_path,
        body=src_task.body,
    )
    _save_task(req.dest_feature_id, new_task)

    # Delete the source task file
    delete_task(req.src_feature_id, req.task_id)

    return new_task


# ---------------------------------------------------------------------------
# Board assembly
# ---------------------------------------------------------------------------


def _get_stage_labels() -> dict[str, str]:
    """Return a mapping of stage id -> display label."""
    from pct.settings.service import get_workflow_stages

    stages: list[WorkflowStageConfig] = get_workflow_stages()
    return {s.stage: s.label or s.stage for s in stages}


def get_board() -> BoardResponse:
    """Build the composite board response."""
    return BoardResponse(
        features=list_features(),
        backlog=list_backlog(),
        enabled_stages=_get_enabled_stages(),
        stage_labels=_get_stage_labels(),
    )
