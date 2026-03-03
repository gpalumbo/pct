"""Cleanup — remove worktrees after success, preserve on failure.

After a task completes its execution:
  - On success: remove the worktree (branch is already merged).
  - On failure: preserve the worktree for debugging.
"""

from __future__ import annotations

from pathlib import Path

from pct.git.worktree import remove_worktree
from loguru import logger


async def cleanup_on_success(
    project_path: Path,
    worktree_path: Path,
) -> bool:
    """Remove a worktree after successful task completion.

    Returns True if removal succeeded or worktree didn't exist.
    """
    wt = Path(worktree_path)
    if not wt.exists():
        logger.debug("Worktree already gone: {}", worktree_path)
        return True

    ok = await remove_worktree(project_path, wt)
    if ok:
        logger.info("Cleaned up worktree after success: {}", worktree_path)
    else:
        logger.warning("Failed to clean up worktree: {}", worktree_path)
    return ok


async def cleanup_on_failure(
    project_path: Path,
    worktree_path: Path,
) -> None:
    """Log that a worktree is being preserved after failure.

    The worktree is intentionally NOT removed so the user or developer
    can inspect the state for debugging.
    """
    logger.info(
        "Preserving worktree for debugging after failure: {}", worktree_path
    )


async def force_cleanup(
    project_path: Path,
    worktree_path: Path,
) -> bool:
    """Force-remove a worktree regardless of state.

    Use this when the user explicitly requests cleanup.
    Returns True on success.
    """
    wt = Path(worktree_path)
    if not wt.exists():
        return True

    ok = await remove_worktree(project_path, wt, force=True)
    if ok:
        logger.info("Force-cleaned worktree: {}", worktree_path)
    return ok
