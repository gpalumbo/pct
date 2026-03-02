"""Auto-unblock — when task completes, check downstream tasks."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from pct.board.wikilinks import parse_wikilink
from pct.models.enums import ExecutionStatus
from pct.storage.feature_io import list_features
from pct.storage.project_io import load_project_config
from pct.storage.task_io import list_tasks, load_task, save_task

logger = logging.getLogger(__name__)


def _done_stage_id(project_root: Path) -> str:
    """Return the last enabled workflow stage id (the 'done' stage)."""
    project = load_project_config(project_root)
    if project is None:
        return "done"
    enabled = [s for s in project.workflow_stages if s.enabled]
    return enabled[-1].id if enabled else "done"


def _stage_auto_run(project_root: Path, stage_id: str) -> bool:
    """Check whether a workflow stage has auto_run enabled."""
    project = load_project_config(project_root)
    if project is None:
        return False
    for stage in project.workflow_stages:
        if stage.id == stage_id and stage.enabled:
            return stage.auto_run
    return False


def _all_deps_done(project_root: Path, blocked_by: list[str], done_stage: str) -> bool:
    """Check if every dependency in blocked_by is at the done stage."""
    for dep_link in blocked_by:
        feat_id, dep_task_id = parse_wikilink(dep_link)
        if dep_task_id:
            dep_task = load_task(project_root, feat_id, dep_task_id)
            if dep_task is None or dep_task.current_stage_id != done_stage:
                return False
    return True


def check_unblocked(
    project_root: Path,
    completed_feature_id: str,
    completed_task_id: str,
) -> list[tuple[str, str]]:
    """Scan ALL tasks across ALL features and auto-queue newly unblocked ones.

    When a task completes, other tasks that had it in their blocked_by list
    may become unblocked. If all of a task's blocked_by dependencies are now
    done AND the task's current stage has auto_run=True, then set the task's
    execution_status to queued.

    Args:
        project_root: Project root path.
        completed_feature_id: Feature id of the task that just completed.
        completed_task_id: Task id of the task that just completed.

    Returns:
        List of (feature_id, task_id) tuples that were newly queued.
    """
    completed_link_variants = {
        f"[[{completed_feature_id}#{completed_task_id}]]",
        f"{completed_feature_id}#{completed_task_id}",
    }

    done_stage = _done_stage_id(project_root)
    newly_queued: list[tuple[str, str]] = []

    features = list_features(project_root)
    for feature in features:
        tasks = list_tasks(project_root, feature.id)
        for task in tasks:
            if not task.blocked_by:
                continue

            # Check if this task references the completed task
            has_dep = False
            for dep_link in task.blocked_by:
                # Normalize for comparison
                inner = dep_link.strip("[]")
                if inner in {
                    f"{completed_feature_id}#{completed_task_id}",
                }:
                    has_dep = True
                    break
                if dep_link in completed_link_variants:
                    has_dep = True
                    break

            if not has_dep:
                continue

            # Check if ALL dependencies are now done
            if not _all_deps_done(project_root, task.blocked_by, done_stage):
                continue

            # Task is now unblocked — check if stage has auto_run
            if _stage_auto_run(project_root, task.current_stage_id) and task.execution_status in (
                ExecutionStatus.idle,
                ExecutionStatus.error,
            ):
                task.execution_status = ExecutionStatus.queued
                task.updated_at = datetime.now(UTC)
                save_task(project_root, task)
                newly_queued.append((feature.id, task.id))
                logger.info(
                    "Auto-queued task %s/%s after %s/%s completed",
                    feature.id,
                    task.id,
                    completed_feature_id,
                    completed_task_id,
                )

    return newly_queued
