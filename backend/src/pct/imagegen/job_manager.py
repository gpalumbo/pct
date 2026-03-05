"""Job manager — track async generation jobs.

In-memory dict of job_id -> status. Job lifecycle: pending -> running ->
completed/failed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pct.imagegen.models import JobStatus
from pct.imagegen.service import ensure_pipeline, generate
from loguru import logger


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
    status: JobStatus = JobStatus.pending
    images: list[dict] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class JobManager:
    """Manages async image generation jobs.

    Stores job state in memory. In production this could be backed by
    a persistent store, but for the initial implementation an in-memory
    dict is sufficient.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

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
        )
        logger.info("Created image gen job {} for {}/{}", job_id, feature_id, task_id)
        return job_id

    def get_job(self, job_id: str) -> JobRecord | None:
        """Get a job record by id."""
        return self._jobs.get(job_id)

    def set_downloading(self, job_id: str) -> None:
        """Transition a job to downloading state."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.downloading
            logger.debug("Job {} -> downloading", job_id)

    def set_running(self, job_id: str) -> None:
        """Transition a job to running state."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.running
            logger.debug("Job {} -> running", job_id)

    def set_completed(self, job_id: str, images: list[dict]) -> None:
        """Transition a job to completed state with results."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.completed
            job.images = images
            job.completed_at = datetime.now(UTC)
            logger.info("Job {} completed with {} images", job_id, len(images))

    def set_failed(self, job_id: str, error: str) -> None:
        """Transition a job to failed state."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.failed
            job.error = error
            job.completed_at = datetime.now(UTC)
            logger.warning("Job {} failed: {}", job_id, error)

    def add_image(self, job_id: str, image_dict: dict) -> None:
        """Append a single completed image to a running job (progressive)."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.running:
            job.images.append(image_dict)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending/downloading/running job. Returns True if cancelled."""
        job = self._jobs.get(job_id)
        if job and job.status in (
            JobStatus.pending,
            JobStatus.downloading,
            JobStatus.running,
        ):
            job.status = JobStatus.failed
            job.error = "Cancelled"
            job.completed_at = datetime.now(UTC)
            logger.info("Job {} cancelled", job_id)
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
    ) -> None:
        """Execute a generation job asynchronously.

        Imports and calls the image generation service. Updates job
        status throughout the lifecycle.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return

        self.set_downloading(job_id)

        try:
            pipeline_ok = await ensure_pipeline()
            if not pipeline_ok:
                self.set_failed(job_id, "Pipeline unavailable")
                return

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
