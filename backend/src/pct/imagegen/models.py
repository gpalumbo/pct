"""Pydantic models for image generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    feature_id: str
    task_id: str
    prompt: str
    negative_prompt: str = ""
    guidance_scale: float = 7.5
    num_inference_steps: int = 30
    width: int = 512
    height: int = 512
    source_image: str | None = None
    divergence: float = Field(default=0.5, ge=0.1, le=0.9)
    seed: int | None = None


class GeneratedImage(BaseModel):
    filename: str
    seed: int
    round: int
    index: int


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    images: list[GeneratedImage] = Field(default_factory=list)
    error: str | None = None


class GenerationRound(BaseModel):
    round: int
    prompt: str
    params: dict = Field(default_factory=dict)
    images: list[GeneratedImage] = Field(default_factory=list)
    selected_image: str | None = None


class SessionMetadata(BaseModel):
    feature_id: str
    task_id: str
    model_id: str = "runwayml/stable-diffusion-v1-5"
    rounds: list[GenerationRound] = Field(default_factory=list)
    current_round: int = 0


class SelectImageRequest(BaseModel):
    round: int
    filename: str
