"""Board request/response models."""

from pydantic import BaseModel

from pct.models.enums import FeatureStage


class FeatureCreate(BaseModel):
    id: str
    title: str
    spec_content: str = ""


class FeatureUpdate(BaseModel):
    title: str | None = None
    stage: FeatureStage | None = None


class TaskCreate(BaseModel):
    id: str
    title: str
    artifact_type_id: str | None = None
    blocked_by: list[str] = []
    cross_refs: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    artifact_type_id: str | None = None
    blocked_by: list[str] | None = None
    cross_refs: list[str] | None = None


class TaskMove(BaseModel):
    target_stage_id: str
    bypass: bool = False


class BoardState(BaseModel):
    features: list[dict]
    workflow_stages: list[dict]
