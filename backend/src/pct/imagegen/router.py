"""Router — /api/imagegen endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from pct.auth.dependencies import get_current_user, get_settings
from pct.config import Settings
from pct.imagegen.job_manager import get_job_manager
from pct.imagegen.models import (
    GenerateRequest,
    GenerateResponse,
    JobStatus,
    JobStatusResponse,
    SelectImageRequest,
)
from pct.imagegen.service import get_session, select_image

router = APIRouter(prefix="/api/imagegen", tags=["imagegen"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_images(
    req: GenerateRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """Submit an image generation job.

    The job runs asynchronously. Poll /jobs/{job_id} for status.
    """
    manager = get_job_manager()
    job_id = manager.create_job(
        feature_id=req.feature_id,
        task_id=req.task_id,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        guidance_scale=req.guidance_scale,
        divergence=req.divergence,
        source_image_id=req.source_image_id,
    )

    # Fire and forget — run the job in the background
    asyncio.create_task(
        manager.run_job(job_id, settings.project_root),
        name=f"imagegen-{job_id}",
    )

    return GenerateResponse(job_id=job_id, status=JobStatus.pending)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _user: str = Depends(get_current_user),
):
    """Get the status of an image generation job."""
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        feature_id=job.feature_id,
        task_id=job.task_id,
        images=job.images,
        error=job.error,
    )


@router.get("/{feature_id}/{task_id}/session")
async def get_image_session(
    feature_id: str,
    task_id: str,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """Get the image generation session for a task."""
    session = get_session(settings.project_root, feature_id, task_id)
    return session.model_dump(mode="json")


@router.post("/{feature_id}/{task_id}/select")
async def select_generated_image(
    feature_id: str,
    task_id: str,
    req: SelectImageRequest,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """Select a generated image as the accepted output for a task."""
    ok = select_image(settings.project_root, feature_id, task_id, req.image_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to select image")
    return {"selected": True, "image_id": req.image_id}
