"""Git worktree lifecycle.

Manages creation, listing, and removal of git worktrees for parallel
feature development. All operations are async using subprocess.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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


async def create_worktree(
    project_path: Path,
    branch: str,
    worktree_path: Path,
) -> bool:
    """Create a new git worktree at worktree_path on the given branch.

    Creates a new branch if it doesn't already exist. Returns True on success.
    """
    # Create the worktree with a new branch
    rc, stdout, stderr = await _run_git(
        "worktree",
        "add",
        "-b",
        branch,
        str(worktree_path),
        cwd=project_path,
    )

    if rc != 0:
        # Branch may already exist — try without -b
        rc, stdout, stderr = await _run_git(
            "worktree",
            "add",
            str(worktree_path),
            branch,
            cwd=project_path,
        )

    if rc != 0:
        logger.error(
            "Failed to create worktree at %s on branch %s: %s",
            worktree_path,
            branch,
            stderr,
        )
        return False

    logger.info("Created worktree at %s on branch %s", worktree_path, branch)
    return True


async def list_worktrees(project_path: Path) -> list[dict[str, str]]:
    """List all git worktrees for the repository.

    Returns a list of dicts with keys: 'path', 'branch', 'head'.
    """
    rc, stdout, stderr = await _run_git(
        "worktree", "list", "--porcelain", cwd=project_path
    )

    if rc != 0:
        logger.error("Failed to list worktrees: %s", stderr)
        return []

    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[len("worktree ") :]}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD ") :]
        elif line.startswith("branch "):
            current["branch"] = line[len("branch ") :]
        elif line == "bare":
            current["bare"] = "true"
        elif line == "detached":
            current["detached"] = "true"

    if current:
        worktrees.append(current)

    return worktrees


async def remove_worktree(
    project_path: Path,
    worktree_path: Path,
    force: bool = False,
) -> bool:
    """Remove a git worktree. Returns True on success.

    Args:
        project_path: Root repository path.
        worktree_path: Path to the worktree to remove.
        force: If True, use --force to remove even with modifications.
    """
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(worktree_path))

    rc, stdout, stderr = await _run_git(*args, cwd=project_path)

    if rc != 0:
        logger.error("Failed to remove worktree %s: %s", worktree_path, stderr)
        return False

    logger.info("Removed worktree at %s", worktree_path)
    return True
