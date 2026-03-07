"""Image generation request/response models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

ARCHITECTURE_RESOLUTIONS: dict[str, list[dict[str, str | int]]] = {
    "sdxl": [
        {"label": "1:1 Square", "width": 1024, "height": 1024},
        {"label": "4:3 Landscape", "width": 1152, "height": 896},
        {"label": "3:4 Portrait", "width": 896, "height": 1152},
        {"label": "3:2 Landscape", "width": 1216, "height": 832},
        {"label": "2:3 Portrait", "width": 832, "height": 1216},
        {"label": "16:9 Landscape", "width": 1344, "height": 768},
        {"label": "9:16 Portrait", "width": 768, "height": 1344},
        {"label": "21:9 Ultra-wide", "width": 1536, "height": 640},
        {"label": "9:21 Ultra-tall", "width": 640, "height": 1536},
    ],
    "sd15": [
        {"label": "1:1 Square", "width": 512, "height": 512},
        {"label": "4:3 Landscape", "width": 640, "height": 480},
        {"label": "3:4 Portrait", "width": 480, "height": 640},
        {"label": "16:9 Landscape", "width": 680, "height": 384},
        {"label": "9:16 Portrait", "width": 384, "height": 680},
    ],
    "flux": [
        {"label": "1:1 Square", "width": 1024, "height": 1024},
        {"label": "4:3 Landscape", "width": 1152, "height": 896},
        {"label": "3:4 Portrait", "width": 896, "height": 1152},
        {"label": "16:9 Landscape", "width": 1344, "height": 768},
        {"label": "9:16 Portrait", "width": 768, "height": 1344},
    ],
}

# Backward-compat alias
SDXL_RESOLUTIONS: list[dict[str, str | int]] = ARCHITECTURE_RESOLUTIONS["sdxl"]


class GenerateRequest(BaseModel):
    """Request to generate images for a task."""

    feature_id: str
    task_id: str
    prompt: str
    negative_prompt: str | None = None
    guidance_scale: float = 7.5
    num_images: int = Field(default=4, ge=1, le=6)
    divergence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_image_id: str | None = None
    width: int = Field(default=1024, ge=512, le=1536, multiple_of=8)
    height: int = Field(default=1024, ge=512, le=1536, multiple_of=8)
    model_id: str | None = None


class JobStatus(StrEnum):
    """Image generation job lifecycle states."""

    pending = "pending"
    loading = "loading"
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
    status_message: str | None = None
    feature_id: str | None = None
    task_id: str | None = None
    images: list[dict] = Field(default_factory=list)
    error: str | None = None
    model_id: str | None = None


class ImagegenModelInfo(BaseModel):
    """Summary of a diffusion model available for image generation."""

    id: str
    name: str
    architecture: str | None = None
    download_status: str | None = None


class SelectImageRequest(BaseModel):
    """Request to select a generated image as the accepted output."""

    image_id: str
