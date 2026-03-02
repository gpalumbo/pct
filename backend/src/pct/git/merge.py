"""Merge — one lock per feature branch.

Ensures that merges into a feature branch are serialized to prevent
conflicts from concurrent task completions.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-level dict of asyncio.Lock per feature_id.
# This ensures only one merge into a feature branch happens at a time.
_feature_locks: dict[str, asyncio.Lock] = {}


def _get_lock(feature_id: str) -> asyncio.Lock:
    """Get or create the asyncio.Lock for a feature branch."""
    if feature_id not in _feature_locks:
        _feature_locks[feature_id] = asyncio.Lock()
    return _feature_locks[feature_id]


async def _run_git(
    *args: str,
    cwd: str | Path,
) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    return proc.returncode or 0, stdout, stderr


async def merge_task_branch(
    project_path: Path,
    feature_id: str,
    task_slug: str,
) -> bool:
    """Merge a task branch into the feature branch using --no-ff.

    Acquires a per-feature lock to serialize merges. The task branch
    name convention is: ``feature/{feature_id}/{task_slug}``.
    The feature branch convention is: ``feature/{feature_id}``.

    Returns True on success, False on failure (e.g. merge conflict).
    """
    lock = _get_lock(feature_id)
    feature_branch = f"feature/{feature_id}"
    task_branch = f"feature/{feature_id}/{task_slug}"

    async with lock:
        # Checkout the feature branch
        rc, _, stderr = await _run_git(
            "checkout", feature_branch, cwd=project_path
        )
        if rc != 0:
            logger.error(
                "Failed to checkout %s: %s", feature_branch, stderr
            )
            return False

        # Merge task branch with --no-ff
        rc, stdout, stderr = await _run_git(
            "merge",
            "--no-ff",
            task_branch,
            "-m",
            f"Merge {task_slug} into {feature_id}",
            cwd=project_path,
        )

        if rc != 0:
            logger.error(
                "Merge conflict merging %s into %s: %s",
                task_branch,
                feature_branch,
                stderr,
            )
            # Abort the failed merge
            await _run_git("merge", "--abort", cwd=project_path)
            return False

        logger.info(
            "Successfully merged %s into %s", task_branch, feature_branch
        )
        return True


async def detect_conflicts(project_path: Path) -> list[str]:
    """Detect files with merge conflicts in the working tree.

    Looks for unmerged paths using ``git diff --name-only --diff-filter=U``.
    Returns a list of conflicting file paths.
    """
    rc, stdout, stderr = await _run_git(
        "diff", "--name-only", "--diff-filter=U", cwd=project_path
    )

    if rc != 0:
        logger.error("Failed to detect conflicts: %s", stderr)
        return []

    if not stdout:
        return []

    return stdout.splitlines()
