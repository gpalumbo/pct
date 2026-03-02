"""Scheduler — find queued tasks, apply concurrency limits."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pct.agent.pool import AgentPool
from pct.engine.execution import _is_task_blocked, execute_task
from pct.models.enums import ExecutionStatus
from pct.storage.feature_io import list_features
from pct.storage.task_io import list_tasks

logger = logging.getLogger(__name__)


def get_runnable_tasks(project_root: Path) -> list[tuple[str, str]]:
    """Return tasks with execution_status=queued and not blocked.

    Returns a list of (feature_id, task_id) tuples.
    """
    runnable: list[tuple[str, str]] = []
    features = list_features(project_root)
    for feature in features:
        tasks = list_tasks(project_root, feature.id)
        for task in tasks:
            if task.execution_status != ExecutionStatus.queued:
                continue
            if _is_task_blocked(project_root, task):
                continue
            runnable.append((feature.id, task.id))
    return runnable


async def schedule_tasks(
    project_root: Path,
    pool: AgentPool,
) -> list[asyncio.Task]:
    """Schedule runnable tasks into the agent pool.

    Creates asyncio.Tasks for each runnable task, limited by the pool's
    semaphores. Returns the list of running asyncio tasks.
    """
    runnable = get_runnable_tasks(project_root)
    if not runnable:
        logger.debug("No runnable tasks found")
        return []

    running: list[asyncio.Task] = []
    for feature_id, task_id in runnable:
        coro = execute_task(project_root, feature_id, task_id)
        atask = asyncio.create_task(coro, name=f"exec-{feature_id}-{task_id}")
        running.append(atask)
        logger.info("Scheduled task %s/%s for execution", feature_id, task_id)

    return running
