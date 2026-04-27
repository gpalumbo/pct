"""Router — /api/imagegen endpoints."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from pct.auth.dependencies import get_current_user, get_settings
from pct.config import Settings
from pct.imagegen.job_manager import get_job_manager
from pct.imagegen.models import (
    ARCHITECTURE_RESOLUTIONS,
    SDXL_RESOLUTIONS,
    GenerateRequest,
    GenerateResponse,
    ImagegenModelInfo,
    JobStatus,
    JobStatusResponse,
    SelectImageRequest,
    build_resolutions,
)
from pct.imagegen.service import (
    detect_architecture,
    detect_native_resolution,
    get_session,
    select_image,
)
from pct.sse import sse_event
from pct.storage.registry_io import load_model_registry

router = APIRouter(prefix="/api/imagegen", tags=["imagegen"])

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


@router.get("/models")
async def list_imagegen_models(
    settings: Settings = Depends(get_settings),
    _user: str = Depends(get_current_user),
):
    """List diffusion models from the registry (those with model_index.json)."""
    models = load_model_registry(settings.global_config_dir)
    results: list[dict] = []
    for m in models:
        if m.file_path and Path(m.file_path).is_dir():
            if (Path(m.file_path) / "model_index.json").exists():
                # Detect architecture from model_index.json pipeline class
                arch: str | None = None
                try:
                    import json

                    idx = json.loads(
                        (Path(m.file_path) / "model_index.json").read_text()
                    )
                    cls_name = idx.get("_class_name", "")
                    arch = detect_architecture(cls_name)
                except Exception:
                    pass

                native_res = detect_native_resolution(m.file_path)
                results.append(
                    ImagegenModelInfo(
                        id=m.id,
                        name=m.name,
                        architecture=arch,
                        download_status=m.download_status,
                        native_resolution=native_res,
                    ).model_dump(mode="json")
                )
    return {"models": results}


@router.get("/resolutions")
async def get_resolutions(
    architecture: str | None = Query(default=None),
    native_resolution: int | None = Query(default=None),
):
    """Return resolution presets for the given architecture (default: sdxl).

    When *native_resolution* is provided, generates presets dynamically
    scaled to that native pixel size instead of using the static lookup.
    """
    if native_resolution is not None:
        return {"resolutions": build_resolutions(native_resolution)}
    arch = architecture or "sdxl"
    resolutions = ARCHITECTURE_RESOLUTIONS.get(arch, SDXL_RESOLUTIONS)
    return {"resolutions": resolutions}


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
        width=req.width,
        height=req.height,
        model_id=req.model_id,
        draft=req.draft,
    )

    # Run the job in the background and register the task for cancellation
    task = asyncio.create_task(
        manager.run_job(
            job_id,
            settings.project_root,
            global_config_dir=settings.global_config_dir,
        ),
        name=f"imagegen-{job_id}",
    )
    manager.register_task(job_id, task)

    return GenerateResponse(job_id=job_id, status=JobStatus.pending)


@router.get("/jobs")
async def list_jobs(
    feature_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    _user: str = Depends(get_current_user),
):
    """List jobs, optionally filtered by feature/task. Only active jobs returned."""
    manager = get_job_manager()
    _ACTIVE = {JobStatus.pending, JobStatus.loading, JobStatus.running}
    jobs = manager.list_jobs(feature_id=feature_id, task_id=task_id)
    return [
        JobStatusResponse(
            job_id=j.job_id,
            status=j.status,
            status_message=j.status_message,
            feature_id=j.feature_id,
            task_id=j.task_id,
            images=j.images,
            error=j.error,
            model_id=j.model_id,
        )
        for j in jobs
        if j.status in _ACTIVE
    ]


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
        status_message=job.status_message,
        feature_id=job.feature_id,
        task_id=job.task_id,
        images=job.images,
        error=job.error,
        model_id=job.model_id,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    _user: str = Depends(get_current_user),
):
    """Stream job status updates via SSE until the job completes or fails."""
    manager = get_job_manager()
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # If already terminal, return single event and close
    if job.status in (JobStatus.completed, JobStatus.failed):
        async def done_stream():
            if job.status == JobStatus.completed:
                yield sse_event({"done": True, "status": "completed", "images": job.images})
            else:
                yield sse_event({"error": job.error or "Unknown error", "status": "failed"})
        return StreamingResponse(done_stream(), media_type="text/event-stream")

    # Subscribe and stream live events
    queue = manager.subscribe(job_id)

    async def event_stream():
        try:
            # Send current state as initial event
            yield sse_event({
                "status": job.status.value,
                "status_message": job.status_message,
                "images": job.images,
            })
            while True:
                event = await queue.get()
                yield sse_event(event)
                if "done" in event or "error" in event:
                    break
        finally:
            manager.unsubscribe(job_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
    """Cancel a pending/loading/running job."""
    manager = get_job_manager()
    ok = manager.cancel_job(job_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    return {"cancelled": True, "job_id": job_id}
