"""In-memory async job tracking for image generation."""

from __future__ import annotations

import asyncio
import uuid

from pct.imagegen.models import JobResponse, JobStatus


_jobs: dict[str, JobResponse] = {}
_tasks: dict[str, asyncio.Task] = {}


def create_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = JobResponse(job_id=job_id, status=JobStatus.PENDING)
    return job_id


def get_job(job_id: str) -> JobResponse | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return
    for key, value in kwargs.items():
        setattr(job, key, value)


def register_task(job_id: str, task: asyncio.Task) -> None:
    _tasks[job_id] = task


def cleanup_job(job_id: str) -> None:
    _jobs.pop(job_id, None)
    _tasks.pop(job_id, None)
