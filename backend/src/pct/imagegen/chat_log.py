"""Helper to persist image-gen activity to the task's chat history.

Image generation prompts/results are written as `imagegen_positive`,
`imagegen_negative`, and `imagegen_result` PlanningMessage rows in the
task-stage chat JSONL, alongside other planning-chat messages.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from pct.chat.models import PlanningMessage
from pct.chat.service import append_task_stage_message, update_session_context
from pct.storage.task_io import load_task


def append_imagegen_message(
    project_root: Path,
    feature_id: str,
    task_id: str,
    role: str,
    content: str,
    *,
    agent_id: str | None = None,
    model_id: str | None = None,
) -> None:
    """Append an imagegen_* message to the task's current-stage chat history.

    Silently no-ops if the task can't be loaded or has no current stage —
    chat persistence must never block image generation.
    """
    try:
        task = load_task(project_root, feature_id, task_id)
        if task is None or not task.current_stage_id:
            return
        stage_id = task.current_stage_id
        msg = PlanningMessage(
            role=role,
            content=content,
            agent_id=agent_id,
            model_id=model_id,
        )
        append_task_stage_message(feature_id, task_id, stage_id, msg)

        # Wire the deterministic frontend session id to the task-stage so
        # GET /sessions/{id}/messages reads from the same JSONL.
        # Frontend convention: TaskDetailPanel.tsx uses
        #   `${featureId}--${task.id}--${task.current_stage_id}`
        session_id = f"{feature_id}--{task_id}--{stage_id}"
        try:
            update_session_context(session_id, feature_id, task_id, stage_id)
        except Exception as e:
            logger.debug("Could not update session context for {}: {}", session_id, e)
    except Exception as e:
        logger.warning("Failed to persist imagegen chat message: {}", e)
