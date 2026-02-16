"""Domain models for the Kanban board: Features, Tasks, and API request/response types."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FeatureStage(str, Enum):
    """Lifecycle stages for a feature."""

    BACKLOG = "backlog"
    PLANNING = "planning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INTEGRATION_TEST = "integration-test"
    COMPLETE = "complete"


class SerializationMode(str, Enum):
    """Whether tasks within a feature run in parallel or serially."""

    PARALLEL = "parallel"
    SERIAL = "serial"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------


class FeatureMetadata(BaseModel):
    """Metadata stored alongside a feature specification."""

    lifecycle_stage: FeatureStage = FeatureStage.PLANNING
    serialization_mode: SerializationMode = SerializationMode.PARALLEL
    worktree_path: str | None = None
    branch: str | None = None
    commits: list[str] = Field(default_factory=list)
    feature_dependencies: list[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Task(BaseModel):
    """A task (card) on the Kanban board."""

    id: str
    title: str
    feature: str
    status: str = "refine-spec"
    agent: str | None = None
    branch: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    cross_depends_on: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    priority: int = 0
    attempt: int = 0
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    body: str = ""

    @property
    def slug(self) -> str:
        """Generate a filesystem-safe slug from the title."""
        s = self.title.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "-", s)
        return s.strip("-")


class Feature(BaseModel):
    """An active feature with its metadata and tasks."""

    id: str
    title: str
    specification: str = ""
    metadata: FeatureMetadata = Field(default_factory=FeatureMetadata)
    tasks: list[Task] = Field(default_factory=list)


class BacklogFeature(BaseModel):
    """A feature in the backlog (not yet activated)."""

    id: str
    title: str
    specification: str = ""


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateFeatureRequest(BaseModel):
    """Request body for creating a new active feature."""

    id: str
    title: str
    specification: str = ""
    metadata: FeatureMetadata | None = None


class UpdateFeatureMetadataRequest(BaseModel):
    """Request body for updating feature metadata (PATCH semantics)."""

    lifecycle_stage: FeatureStage | None = None
    serialization_mode: SerializationMode | None = None
    worktree_path: str | None = None
    branch: str | None = None
    commits: list[str] | None = None
    feature_dependencies: list[str] | None = None


class CreateTaskRequest(BaseModel):
    """Request body for creating a new task."""

    title: str
    status: str = "refine-spec"
    agent: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    cross_depends_on: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    priority: int = 0
    body: str = ""


class UpdateTaskRequest(BaseModel):
    """Request body for updating a task (full replacement of provided fields)."""

    title: str | None = None
    status: str | None = None
    agent: str | None = None
    branch: str | None = None
    depends_on: list[str] | None = None
    cross_depends_on: list[str] | None = None
    tags: list[str] | None = None
    priority: int | None = None
    attempt: int | None = None
    body: str | None = None


class MoveTaskRequest(BaseModel):
    """Request body for moving a task to a new workflow stage."""

    new_status: str
    confirm_skip: bool = False


class BoardResponse(BaseModel):
    """Composite response containing the full board state."""

    features: list[Feature] = Field(default_factory=list)
    backlog: list[BacklogFeature] = Field(default_factory=list)
    enabled_stages: list[str] = Field(default_factory=list)
