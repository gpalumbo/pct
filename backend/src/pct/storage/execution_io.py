"""Execution artifact I/O — attempt dirs, metadata, archival."""

import json
from pathlib import Path

import yaml


def _active_tasks_dir(project_root: Path) -> Path:
    return project_root / ".pct" / "execution" / "active-tasks"


def _completed_tasks_dir(project_root: Path) -> Path:
    return project_root / ".pct" / "execution" / "completed-tasks"


def _task_exec_dir(project_root: Path, task_id: str) -> Path:
    return _active_tasks_dir(project_root) / task_id


def _next_attempt_number(task_dir: Path) -> int:
    """Find the next attempt number (1-based)."""
    existing = sorted(task_dir.glob("attempt-*"))
    if not existing:
        return 1
    # Parse the highest number
    last = existing[-1].name  # e.g. "attempt-003"
    try:
        return int(last.split("-")[1]) + 1
    except (IndexError, ValueError):
        return len(existing) + 1


def write_attempt(
    project_root: Path,
    task_id: str,
    metadata: dict,
    output: str = "",
    agent_log: list[dict] | None = None,
) -> Path:
    """Create an attempt directory with metadata.yaml, output.md, and agent_log.jsonl."""
    task_dir = _task_exec_dir(project_root, task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    attempt_num = _next_attempt_number(task_dir)
    attempt_dir = task_dir / f"attempt-{attempt_num:03d}"
    attempt_dir.mkdir()

    # Write metadata.yaml
    meta_path = attempt_dir / "metadata.yaml"
    meta_path.write_text(
        yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )

    # Write output.md
    output_path = attempt_dir / "output.md"
    output_path.write_text(output, encoding="utf-8")

    # Write agent_log.jsonl
    if agent_log:
        log_path = attempt_dir / "agent_log.jsonl"
        lines = [json.dumps(entry, ensure_ascii=False) + "\n" for entry in agent_log]
        log_path.write_text("".join(lines), encoding="utf-8")

    return attempt_dir


def read_attempts(project_root: Path, task_id: str) -> list[dict]:
    """Read all attempt metadata for a task, ordered by attempt number."""
    task_dir = _task_exec_dir(project_root, task_id)
    if not task_dir.exists():
        return []
    results = []
    for attempt_dir in sorted(task_dir.glob("attempt-*")):
        meta_path = attempt_dir / "metadata.yaml"
        if meta_path.exists():
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            if data:
                data["_attempt_dir"] = str(attempt_dir)
                results.append(data)
    return results


def archive_task(project_root: Path, task_id: str) -> bool:
    """Move task execution data from active to completed. Returns True if moved."""
    src = _task_exec_dir(project_root, task_id)
    if not src.exists():
        return False
    dest_parent = _completed_tasks_dir(project_root)
    dest_parent.mkdir(parents=True, exist_ok=True)
    dest = dest_parent / task_id
    src.rename(dest)
    return True
