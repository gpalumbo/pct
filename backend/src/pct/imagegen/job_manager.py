"""Job manager — track async generation jobs.

In-memory dict of job_id -> status. Job lifecycle: pending -> running ->
completed/failed.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from pct.agent.model_downloader import ensure_model_ready
from pct.imagegen.models import JobStatus
from pct.imagegen.service import ensure_pipeline, generate
from pct.models.agents import ModelRegistryEntry
from pct.storage.registry_io import load_model_registry


@dataclass
class JobRecord:
    """Internal state for a generation job."""

    job_id: str
    feature_id: str
    task_id: str
    prompt: str
    negative_prompt: str | None = None
    guidance_scale: float = 7.5
    num_images: int = 4
    divergence: float | None = None
    source_image_id: str | None = None
    width: int = 1024
    height: int = 1024
    model_id: str | None = None
    status: JobStatus = JobStatus.pending
    status_message: str | None = None
    images: list[dict] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


def _resolve_model(
    model_id: str | None,
    global_config_dir: Path,
) -> ModelRegistryEntry | None:
    """Look up model_id in the registry and return the entry.

    If *model_id* is None, picks the first registry entry that looks
    like a diffusion model — either already downloaded (has
    ``model_index.json``) or a HuggingFace entry whose identifier
    contains a known diffusion keyword.

    Returns ``None`` when no suitable model is found.
    """
    models = load_model_registry(global_config_dir)

    # If explicit model_id, look it up directly
    if model_id is not None:
        for m in models:
            if m.id == model_id:
                return m
        logger.warning("Model {} not found in registry", model_id)
        return None

    # Auto-detect: first model already downloaded with model_index.json
    for m in models:
        if m.file_path and Path(m.file_path).is_dir():
            if (Path(m.file_path) / "model_index.json").exists():
                logger.info("Auto-selected diffusion model: {} ({})", m.name, m.id)
                return m

    # Fallback: first HuggingFace entry that looks like a diffusion model
    _DIFFUSION_HINTS = ("stable-diffusion", "sdxl", "flux", "pixart", "kandinsky", "wuerstchen")
    for m in models:
        ident = (m.model_identifier or "").lower()
        if any(hint in ident for hint in _DIFFUSION_HINTS):
            logger.info("Auto-selected diffusion model (not yet downloaded): {} ({})", m.name, m.id)
            return m

    return None


class JobManager:
    """Manages async image generation jobs.

    Stores job state in memory. In production this could be backed by
    a persistent store, but for the initial implementation an in-memory
    dict is sufficient.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._event_queues: dict[str, list[asyncio.Queue]] = {}

    def create_job(
        self,
        feature_id: str,
        task_id: str,
        prompt: str,
        negative_prompt: str | None = None,
        guidance_scale: float = 7.5,
        num_images: int = 4,
        divergence: float | None = None,
        source_image_id: str | None = None,
        width: int = 1024,
        height: int = 1024,
        model_id: str | None = None,
    ) -> str:
        """Create a new pending job. Returns the job_id."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = JobRecord(
            job_id=job_id,
            feature_id=feature_id,
            task_id=task_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            guidance_scale=guidance_scale,
            num_images=num_images,
            divergence=divergence,
            source_image_id=source_image_id,
            width=width,
            height=height,
            model_id=model_id,
        )
        logger.info("Created image gen job {} for {}/{}", job_id, feature_id, task_id)
        return job_id

    def get_job(self, job_id: str) -> JobRecord | None:
        """Get a job record by id."""
        return self._jobs.get(job_id)

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """Subscribe to SSE events for a job. Returns a queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._event_queues.setdefault(job_id, []).append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue for a job."""
        queues = self._event_queues.get(job_id)
        if queues:
            try:
                queues.remove(queue)
            except ValueError:
                pass
            if not queues:
                del self._event_queues[job_id]

    def _push_event(self, job_id: str, event: dict) -> None:
        """Push an event to all subscribers for a job (non-blocking)."""
        for queue in self._event_queues.get(job_id, []):
            queue.put_nowait(event)

    def set_loading(self, job_id: str) -> None:
        """Transition a job to loading state (loading pipeline into memory)."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.loading
            logger.debug("Job {} -> loading", job_id)
            self._push_event(job_id, {"status": "loading", "status_message": job.status_message})

    def set_running(self, job_id: str) -> None:
        """Transition a job to running state."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.running
            logger.debug("Job {} -> running", job_id)
            self._push_event(job_id, {"status": "running", "status_message": None})

    def set_completed(self, job_id: str, images: list[dict]) -> None:
        """Transition a job to completed state with results."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.completed
            job.images = images
            job.completed_at = datetime.now(UTC)
            logger.info("Job {} completed with {} images", job_id, len(images))
            self._push_event(job_id, {"done": True, "status": "completed", "images": images})

    def set_failed(self, job_id: str, error: str) -> None:
        """Transition a job to failed state."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.failed
            job.error = error
            job.completed_at = datetime.now(UTC)
            logger.warning("Job {} failed: {}", job_id, error)
            self._push_event(job_id, {"error": error, "status": "failed"})

    def add_image(self, job_id: str, image_dict: dict) -> None:
        """Append a single completed image to a running job (progressive)."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.running:
            job.images.append(image_dict)
            self._push_event(job_id, {"image": image_dict})

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending/loading/running job. Returns True if cancelled."""
        job = self._jobs.get(job_id)
        if job and job.status in (
            JobStatus.pending,
            JobStatus.loading,
            JobStatus.running,
        ):
            job.status = JobStatus.failed
            job.error = "Cancelled"
            job.completed_at = datetime.now(UTC)
            logger.info("Job {} cancelled", job_id)
            self._push_event(job_id, {"error": "Cancelled", "status": "failed"})
            return True
        return False

    def list_jobs(
        self,
        feature_id: str | None = None,
        task_id: str | None = None,
    ) -> list[JobRecord]:
        """List jobs, optionally filtered by feature/task."""
        results = list(self._jobs.values())
        if feature_id:
            results = [j for j in results if j.feature_id == feature_id]
        if task_id:
            results = [j for j in results if j.task_id == task_id]
        return sorted(results, key=lambda j: j.created_at)

    async def run_job(
        self,
        job_id: str,
        project_root: Path,
        global_config_dir: Path | None = None,
    ) -> None:
        """Execute a generation job asynchronously.

        Resolves the model from the registry, auto-downloads if needed,
        then loads the pipeline and runs generation.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return

        self.set_loading(job_id)

        try:
            # Resolve model from registry
            cfg_dir = global_config_dir or Path.home() / ".pct"
            entry = _resolve_model(job.model_id, cfg_dir)

            resolved_id: str | None = None
            model_path: str | None = None

            if entry is not None:
                resolved_id = entry.id

                async def _on_status(msg: str) -> None:
                    logger.info("Model download: {}", msg)
                    job.status_message = msg
                    self._push_event(job_id, {"status": "loading", "status_message": msg})

                entry = await ensure_model_ready(
                    entry, _on_status, require_gguf=False
                )
                model_path = entry.file_path

            pipeline_ok = await ensure_pipeline(
                model_id=resolved_id, model_path=model_path
            )
            if not pipeline_ok:
                self.set_failed(job_id, "Pipeline unavailable")
                return

            # Store the resolved model_id on the job
            job.model_id = resolved_id

            self.set_running(job_id)

            def on_image_complete(img):
                self.add_image(job_id, img.model_dump(mode="json"))

            result = await generate(
                project_root=project_root,
                feature_id=job.feature_id,
                task_id=job.task_id,
                prompt=job.prompt,
                negative_prompt=job.negative_prompt,
                guidance_scale=job.guidance_scale,
                num_images=job.num_images,
                on_image_complete=on_image_complete,
                source_image_id=job.source_image_id,
                divergence=job.divergence,
                width=job.width,
                height=job.height,
                model_id=resolved_id,
                model_path=model_path,
            )

            if result is None:
                self.set_failed(job_id, "Pipeline unavailable")
                return

            images = [img.model_dump(mode="json") for img in result.images]
            self.set_completed(job_id, images)

        except Exception as e:
            self.set_failed(job_id, str(e))
            logger.exception("Job {} failed with exception", job_id)


# Module-level singleton
_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    """Get or create the singleton JobManager."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
