"""Post-merge — re-index changed files.

After a merge completes, determine which files changed and re-index
them in the RAG system so that context search stays up-to-date.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pct.rag.indexer import SUPPORTED_EXTENSIONS, index_file
from loguru import logger


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


async def get_changed_files(project_path: Path) -> list[str]:
    """Get the list of files changed in the most recent commit.

    Uses ``git diff --name-only HEAD~1`` to find changed files.
    Returns relative file paths.
    """
    rc, stdout, stderr = await _run_git(
        "diff", "--name-only", "HEAD~1", cwd=project_path
    )

    if rc != 0:
        logger.warning("Failed to get changed files: {}", stderr)
        return []

    if not stdout:
        return []

    return stdout.splitlines()


async def reindex_changed_files(project_path: Path) -> int:
    """Re-index files that changed in the most recent merge commit.

    Only indexes files with supported extensions. Runs indexing
    in a thread to avoid blocking the event loop.

    Returns the count of successfully indexed files.
    """
    changed = await get_changed_files(project_path)
    if not changed:
        logger.debug("No changed files to reindex")
        return 0

    count = 0
    for rel_path in changed:
        file_path = project_path / rel_path
        if not file_path.exists():
            continue
        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue

        # Run indexing in a thread since it may involve heavy computation
        indexed = await asyncio.to_thread(index_file, project_path, file_path)
        if indexed:
            count += 1
            logger.debug("Re-indexed: {}", rel_path)

    logger.info("Re-indexed {} files after merge", count)
    return count
