"""API routes for image generation."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from pct.auth.dependencies import get_current_user
from pct.imagegen import job_manager, service
from pct.imagegen.models import GenerateRequest, JobResponse, SelectImageRequest, SessionMetadata

router = APIRouter()


@router.post("/generate", response_model=dict)
async def generate_images(req: GenerateRequest, _user: dict = Depends(get_current_user)):
    """Start an async image generation job. Returns {job_id}."""
    try:
        job_id = service.start_generation(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"job_id": job_id}


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, _user: dict = Depends(get_current_user)):
    """Poll job status and progress."""
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{feature_id}/{task_id}/session", response_model=SessionMetadata)
async def get_session(
    feature_id: str, task_id: str, _user: dict = Depends(get_current_user)
):
    """Get image generation session metadata."""
    return service.load_metadata(feature_id, task_id)


@router.post("/{feature_id}/{task_id}/select", response_model=SessionMetadata)
async def select_image(
    feature_id: str,
    task_id: str,
    req: SelectImageRequest,
    _user: dict = Depends(get_current_user),
):
    """Select an image from a round for refinement."""
    return service.select_image(feature_id, task_id, req)


@router.get("/{feature_id}/{task_id}/images/{filename}")
async def get_image(
    feature_id: str, task_id: str, filename: str, _user: dict = Depends(get_current_user)
):
    """Serve a generated image file."""
    path = service._images_dir(feature_id, task_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png")
