"""Router — /api/imagegen endpoints."""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

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

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


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
        num_images=req.num_images,
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


def _validate_path_part(value: str, name: str) -> None:
    """Reject path-traversal attempts."""
    if not _SAFE_ID.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid {name}")


@router.get("/images/{feature_id}/{task_id}/{image_id}")
async def serve_image(
    feature_id: str,
    task_id: str,
    image_id: str,
    settings: Settings = Depends(get_settings),
):
    """Serve a generated image PNG.

    No auth — images are local and <img> tags cannot send Bearer headers.
    """
    _validate_path_part(feature_id, "feature_id")
    _validate_path_part(task_id, "task_id")
    _validate_path_part(image_id, "image_id")

    path = settings.project_root / "work" / feature_id / task_id / "images" / f"{image_id}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")


@router.get("/features/{feature_id}/images")
async def list_feature_images(
    feature_id: str,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """List all generated images across tasks in a feature."""
    _validate_path_part(feature_id, "feature_id")

    feature_dir = settings.project_root / "work" / feature_id
    images: list[dict[str, str]] = []
    if feature_dir.is_dir():
        for task_dir in sorted(feature_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            img_dir = task_dir / "images"
            if not img_dir.is_dir():
                continue
            for img_file in sorted(img_dir.glob("*.png")):
                image_id = img_file.stem
                images.append(
                    {
                        "id": image_id,
                        "task_id": task_dir.name,
                        "feature_id": feature_id,
                        "filename": img_file.name,
                        "url": f"/api/imagegen/images/{feature_id}/{task_dir.name}/{image_id}",
                    }
                )
    return {"images": images}


@router.get("/{feature_id}/{task_id}/images")
async def list_task_images(
    feature_id: str,
    task_id: str,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """List generated images for a specific task, sorted newest-first."""
    _validate_path_part(feature_id, "feature_id")
    _validate_path_part(task_id, "task_id")

    img_dir = settings.project_root / "work" / feature_id / task_id / "images"
    images: list[dict[str, object]] = []
    if img_dir.is_dir():
        for img_file in img_dir.glob("*.png"):
            image_id = img_file.stem
            images.append(
                {
                    "id": image_id,
                    "task_id": task_id,
                    "feature_id": feature_id,
                    "filename": img_file.name,
                    "url": f"/api/imagegen/images/{feature_id}/{task_id}/{image_id}",
                    "created_at": img_file.stat().st_mtime,
                }
            )
    images.sort(key=lambda x: x["created_at"], reverse=True)
    return {"images": images}


@router.delete("/{feature_id}/{task_id}/images/{image_id}")
async def delete_image(
    feature_id: str,
    task_id: str,
    image_id: str,
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """Delete a generated image file from disk."""
    _validate_path_part(feature_id, "feature_id")
    _validate_path_part(task_id, "task_id")
    _validate_path_part(image_id, "image_id")

    path = settings.project_root / "work" / feature_id / task_id / "images" / f"{image_id}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    path.unlink()
    return {"deleted": True, "image_id": image_id}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    _user: str = Depends(get_current_user),
):
    """Cancel a pending/downloading/running job."""
    manager = get_job_manager()
    ok = manager.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    return {"cancelled": True, "job_id": job_id}
