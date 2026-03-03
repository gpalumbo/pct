"""Execution engine — dequeue, assemble context, execute, store result."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AgentResult, AssembledContext
from pct.agent.protocols import AgentProvider
from pct.board.wikilinks import parse_wikilink
from pct.chat.context_builder import expand_template
from pct.models.core import ErrorDetails, Task
from pct.models.enums import ExecutionStatus, TaskOutcome
from pct.storage.execution_io import write_attempt
from pct.storage.feature_io import list_features, load_feature_spec
from pct.storage.project_io import load_project_config
from pct.storage.task_io import list_tasks, load_task, load_task_body, save_task
from loguru import logger


def _resolve_provider(project_root: Path, agent_id: str | None) -> AgentProvider | None:
    """Resolve an agent_id to a provider instance via the project config.

    Returns None if agent_id is unset or provider cannot be resolved.
    """
    if agent_id is None:
        return None
    try:
        from pct.chat.provider_factory import resolve_provider

        provider, _cfg = resolve_provider(agent_id)
        return provider
    except Exception:
        return None


def _build_context(
    project_root: Path,
    feature_id: str,
    task_id: str,
    stage_prompt_template: str | None,
) -> AssembledContext:
    """Assemble the context for an agent execution turn.

    1. Resolve task context variables.
    2. Expand the stage prompt template.
    3. Return an AssembledContext with the expanded prompt as base.
    """
    variables = _resolve_task_variables(project_root, feature_id, task_id)

    if stage_prompt_template:
        prompt = expand_template(stage_prompt_template, variables)
    else:
        prompt = (
            f"Task: {variables.get('task_title', task_id)}\n\n"
            f"Artifact:\n{variables.get('artifact', '')}\n\n"
            f"Dependencies:\n{variables.get('blocked_by', 'None')}\n\n"
            f"Cross-references:\n{variables.get('cross_refs', 'None')}"
        )

    return AssembledContext(base=prompt)


def _resolve_task_variables(
    project_root: Path,
    feature_id: str,
    task_id: str,
) -> dict[str, str]:
    """Build the full context variables for a task."""
    variables: dict[str, str] = {}

    task = load_task(project_root, feature_id, task_id)
    if task is None:
        return variables

    variables["task_title"] = task.title
    variables["feature_title"] = feature_id
    variables["artifact_work_dir"] = f"work/{feature_id}/{task_id}/"
    variables["artifact_file_path"] = f"work/{feature_id}/{feature_id}.md"

    artifact_content = load_task_body(project_root, feature_id, task_id)
    variables["artifact"] = artifact_content

    feature_spec = load_feature_spec(project_root, feature_id)
    if feature_spec:
        variables["feature_title"] = feature_id

    blocked_by_parts = []
    for link in task.blocked_by:
        dep_feat, dep_task = parse_wikilink(link)
        if dep_task:
            dep_body = load_task_body(project_root, dep_feat, dep_task)
            if dep_body:
                blocked_by_parts.append(f"## {dep_feat}#{dep_task}\n{dep_body}")
    variables["blocked_by"] = "\n\n".join(blocked_by_parts)

    cross_ref_parts = []
    for link in task.cross_refs:
        ref_feat, ref_task = parse_wikilink(link)
        if ref_task:
            ref_body = load_task_body(project_root, ref_feat, ref_task)
            if ref_body:
                cross_ref_parts.append(f"## {ref_feat}#{ref_task}\n{ref_body}")
    variables["cross_refs"] = "\n\n".join(cross_ref_parts)

    return variables


def _get_stage_config(
    project_root: Path, stage_id: str
) -> tuple[str | None, str | None, bool]:
    """Return (agent_id, prompt_template, auto_run) for a workflow stage."""
    project = load_project_config(project_root)
    if project is None:
        return None, None, False
    for stage in project.workflow_stages:
        if stage.id == stage_id and stage.enabled:
            return stage.agent_id, stage.prompt_template, stage.auto_run
    return None, None, False


def _get_next_stage_id(project_root: Path, current_stage_id: str) -> str | None:
    """Return the next enabled stage id after current_stage_id, or None."""
    project = load_project_config(project_root)
    if project is None:
        return None
    enabled = [s for s in project.workflow_stages if s.enabled]
    for i, stage in enumerate(enabled):
        if stage.id == current_stage_id and i + 1 < len(enabled):
            return enabled[i + 1].id
    return None


async def execute_task(
    project_root: Path,
    feature_id: str,
    task_id: str,
    agent_id: str | None = None,
) -> AgentResult:
    """Execute a task through its current stage's agent.

    Steps:
      1. Load task, resolve provider from agent config.
      2. Build context using context_builder.
      3. Execute via chat_loop.execute_chat_turn.
      4. Store result via execution_io.write_attempt.
      5. On approved: advance task to next stage.
      6. On error: set execution_status=error, populate error_details.

    Returns the AgentResult from the execution.
    """
    task = load_task(project_root, feature_id, task_id)
    if task is None:
        return AgentResult(
            outcome=TaskOutcome.error,
            error=f"Task not found: {feature_id}/{task_id}",
        )

    # Mark as running
    task.execution_status = ExecutionStatus.running
    task.updated_at = datetime.now(UTC)
    save_task(project_root, task)

    # Resolve agent / stage config
    stage_agent_id, stage_prompt, _ = _get_stage_config(
        project_root, task.current_stage_id
    )
    effective_agent_id = agent_id or stage_agent_id
    provider = _resolve_provider(project_root, effective_agent_id)

    if provider is None:
        # No provider available — return a stub approved so the scheduler can
        # still advance the task (useful for user-type or tool-type agents).
        result = AgentResult(
            outcome=TaskOutcome.approved,
            output="No provider configured — task marked complete by engine.",
        )
    else:
        context = _build_context(
            project_root, feature_id, task_id, stage_prompt
        )
        result = await execute_chat_turn(
            provider,
            context,
            system_prompt="You are an agent executing a project task.",
        )

    # Store attempt
    attempt_meta = {
        "feature_id": feature_id,
        "task_id": task_id,
        "stage_id": task.current_stage_id,
        "agent_id": effective_agent_id or "none",
        "outcome": result.outcome.value,
        "tokens_input": result.tokens_input,
        "tokens_output": result.tokens_output,
        "duration_seconds": result.duration_seconds,
        "error": result.error,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    agent_log = [
        {"tool": tc.function_name, "args": tc.arguments}
        for tc in result.tool_calls
    ]
    write_attempt(project_root, task_id, attempt_meta, result.output, agent_log or None)

    # Reload task (in case of concurrent modification)
    task = load_task(project_root, feature_id, task_id)
    if task is None:
        return result

    if result.outcome == TaskOutcome.approved:
        # Advance to next stage
        next_stage = _get_next_stage_id(project_root, task.current_stage_id)
        if next_stage is not None:
            task.current_stage_id = next_stage
        task.execution_status = ExecutionStatus.idle
        task.error_details = None
        task.updated_at = datetime.now(UTC)
        save_task(project_root, task)
        logger.info(
            "Task {}/{} completed stage, advanced to {}",
            feature_id,
            task_id,
            task.current_stage_id,
        )
    else:
        task.execution_status = ExecutionStatus.error
        task.error_details = ErrorDetails(
            error_type="agent_execution",
            message=result.error or "Unknown error",
            partial_output=result.output[:1000] if result.output else None,
        )
        task.updated_at = datetime.now(UTC)
        save_task(project_root, task)
        logger.warning(
            "Task {}/{} execution failed: {}",
            feature_id,
            task_id,
            result.error,
        )

    return result


def _is_task_blocked(project_root: Path, task: Task) -> bool:
    """Check whether a task's blocked_by dependencies are all at the done stage."""
    if not task.blocked_by:
        return False

    project = load_project_config(project_root)
    if project is None:
        return True
    enabled = [s for s in project.workflow_stages if s.enabled]
    done_stage = enabled[-1].id if enabled else "done"

    for dep_link in task.blocked_by:
        feat_id, dep_task_id = parse_wikilink(dep_link)
        if dep_task_id:
            dep_task = load_task(project_root, feat_id, dep_task_id)
            if dep_task is None or dep_task.current_stage_id != done_stage:
                return True
    return False


def dequeue_next(project_root: Path) -> tuple[str, str] | None:
    """Find the first queued task that is not blocked.

    Scans all features and their tasks. Returns (feature_id, task_id) or None.
    """
    features = list_features(project_root)
    for feature in features:
        tasks = list_tasks(project_root, feature.id)
        for task in tasks:
            if task.execution_status != ExecutionStatus.queued:
                continue
            if _is_task_blocked(project_root, task):
                continue
            return (feature.id, task.id)
    return None
