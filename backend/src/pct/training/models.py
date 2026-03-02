"""Training request/response models."""

from __future__ import annotations

from pydantic import BaseModel

from pct.models.enums import (
    AnnotationCategory,
    CurationStatus,
    FlagType,
    LoRASaveTarget,
    TrainingMethod,
)


class FlagCreate(BaseModel):
    model_config = {"extra": "forbid"}

    session_ref: str
    message_index: int
    flag_type: FlagType  # positive or negative
    annotation_category: AnnotationCategory | None = None
    note: str = ""


class FlagUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    annotation_category: AnnotationCategory | None = None
    note: str | None = None
    curation_status: CurationStatus | None = None
    edited_response: str | None = None


class DatasetCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    description: str = ""


class DatasetUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    description: str | None = None
    entry_ids: list[str] | None = None  # flag IDs to include


class JobCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    base_model_id: str
    training_method: TrainingMethod
    dataset_ids: list[str]
    target_lora_name: str
    save_target: LoRASaveTarget = LoRASaveTarget.project_local
    lora_rank: int = 16
    lora_alpha: int = 32
    learning_rate: float = 2e-4
    epochs: int = 3
    batch_size: int = 4


class PromptTemplateCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    content: str


class PromptTemplateUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    content: str  # creates new version
