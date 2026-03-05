"""Image generation request/response models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request to generate images for a task."""

    feature_id: str
    task_id: str
    prompt: str
    negative_prompt: str | None = None
    guidance_scale: float = 7.5
    num_images: int = Field(default=4, ge=1, le=6)
    divergence: float | None = None
    source_image_id: str | None = None


class JobStatus(StrEnum):
    """Image generation job lifecycle states."""

    pending = "pending"
    downloading = "downloading"
    running = "running"
    completed = "completed"
    failed = "failed"


class GenerateResponse(BaseModel):
    """Response after submitting a generation request."""

    job_id: str
    status: JobStatus = JobStatus.pending


class JobStatusResponse(BaseModel):
    """Status of an image generation job."""

    job_id: str
    status: JobStatus
    feature_id: str | None = None
    task_id: str | None = None
    images: list[dict] = Field(default_factory=list)
    error: str | None = None


class SelectImageRequest(BaseModel):
    """Request to select a generated image as the accepted output."""

    image_id: str
