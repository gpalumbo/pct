"""Execution logging — write attempt metadata.

Thin wrapper around execution_io for structured logging with
additional convenience methods.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from pct.storage.execution_io import read_attempts, write_attempt

logger = logging.getLogger(__name__)


def log_execution_start(
    project_root: Path,
    task_id: str,
    feature_id: str,
    stage_id: str,
    agent_id: str | None,
) -> None:
    """Log that a task execution is starting."""
    logger.info(
        "Execution started: task=%s feature=%s stage=%s agent=%s",
        task_id,
        feature_id,
        stage_id,
        agent_id or "none",
    )


def log_execution_result(
    project_root: Path,
    task_id: str,
    feature_id: str,
    stage_id: str,
    agent_id: str | None,
    outcome: str,
    duration_seconds: float,
    error: str | None = None,
    output: str = "",
    agent_log: list[dict] | None = None,
) -> Path:
    """Write a structured execution attempt and log it.

    Returns the path to the attempt directory.
    """
    metadata = {
        "feature_id": feature_id,
        "task_id": task_id,
        "stage_id": stage_id,
        "agent_id": agent_id or "none",
        "outcome": outcome,
        "duration_seconds": duration_seconds,
        "error": error,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    attempt_dir = write_attempt(
        project_root, task_id, metadata, output, agent_log
    )

    if error:
        logger.warning(
            "Execution failed: task=%s outcome=%s error=%s",
            task_id,
            outcome,
            error,
        )
    else:
        logger.info(
            "Execution completed: task=%s outcome=%s duration=%.2fs",
            task_id,
            outcome,
            duration_seconds,
        )

    return attempt_dir


def get_execution_history(
    project_root: Path,
    task_id: str,
) -> list[dict]:
    """Retrieve all attempt metadata for a task, ordered by attempt number."""
    return read_attempts(project_root, task_id)
