"""Tests for git worktree operations — create/list/remove (mock git commands)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pct.git.worktree import create_worktree, list_worktrees, remove_worktree


@pytest.fixture
def project_path(tmp_path: Path) -> Path:
    """A temporary directory acting as the project root."""
    return tmp_path


class TestCreateWorktree:
    @pytest.mark.asyncio
    async def test_create_worktree_success(self, project_path: Path, tmp_path: Path):
        """create_worktree returns True when git succeeds."""
        wt_path = tmp_path / "worktrees" / "feature-branch"

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (0, "Preparing worktree", "")

            result = await create_worktree(
                project_path, "feature/my-feature", wt_path
            )

        assert result is True
        mock_git.assert_called_once_with(
            "worktree",
            "add",
            "-b",
            "feature/my-feature",
            str(wt_path),
            cwd=project_path,
        )

    @pytest.mark.asyncio
    async def test_create_worktree_branch_exists_fallback(
        self, project_path: Path, tmp_path: Path
    ):
        """When -b fails (branch exists), falls back to add without -b."""
        wt_path = tmp_path / "worktrees" / "existing-branch"

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            # First call fails (branch exists), second succeeds
            mock_git.side_effect = [
                (128, "", "fatal: branch already exists"),
                (0, "Preparing worktree", ""),
            ]

            result = await create_worktree(
                project_path, "feature/existing", wt_path
            )

        assert result is True
        assert mock_git.call_count == 2

    @pytest.mark.asyncio
    async def test_create_worktree_failure(
        self, project_path: Path, tmp_path: Path
    ):
        """create_worktree returns False when both attempts fail."""
        wt_path = tmp_path / "worktrees" / "bad-branch"

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (128, "", "fatal: error")

            result = await create_worktree(
                project_path, "feature/bad", wt_path
            )

        assert result is False


class TestListWorktrees:
    @pytest.mark.asyncio
    async def test_list_worktrees_parses_porcelain(self, project_path: Path):
        """list_worktrees correctly parses git worktree list --porcelain output."""
        porcelain_output = (
            "worktree /home/user/project\n"
            "HEAD abc123\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree /home/user/project-wt1\n"
            "HEAD def456\n"
            "branch refs/heads/feature/f1\n"
        )

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (0, porcelain_output.strip(), "")

            worktrees = await list_worktrees(project_path)

        assert len(worktrees) == 2
        assert worktrees[0]["path"] == "/home/user/project"
        assert worktrees[0]["branch"] == "refs/heads/main"
        assert worktrees[0]["head"] == "abc123"
        assert worktrees[1]["path"] == "/home/user/project-wt1"
        assert worktrees[1]["branch"] == "refs/heads/feature/f1"

    @pytest.mark.asyncio
    async def test_list_worktrees_empty(self, project_path: Path):
        """list_worktrees returns empty list on failure."""
        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (128, "", "fatal: not a git repo")

            worktrees = await list_worktrees(project_path)

        assert worktrees == []

    @pytest.mark.asyncio
    async def test_list_worktrees_handles_detached(self, project_path: Path):
        """list_worktrees handles detached HEAD entries."""
        porcelain_output = (
            "worktree /home/user/project\n"
            "HEAD abc123\n"
            "detached\n"
        )

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (0, porcelain_output.strip(), "")

            worktrees = await list_worktrees(project_path)

        assert len(worktrees) == 1
        assert worktrees[0]["detached"] == "true"


class TestRemoveWorktree:
    @pytest.mark.asyncio
    async def test_remove_worktree_success(
        self, project_path: Path, tmp_path: Path
    ):
        """remove_worktree returns True on success."""
        wt_path = tmp_path / "worktrees" / "old-wt"

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (0, "", "")

            result = await remove_worktree(project_path, wt_path)

        assert result is True
        mock_git.assert_called_once_with(
            "worktree", "remove", str(wt_path), cwd=project_path
        )

    @pytest.mark.asyncio
    async def test_remove_worktree_force(
        self, project_path: Path, tmp_path: Path
    ):
        """remove_worktree with force=True passes --force flag."""
        wt_path = tmp_path / "worktrees" / "dirty-wt"

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (0, "", "")

            result = await remove_worktree(project_path, wt_path, force=True)

        assert result is True
        mock_git.assert_called_once_with(
            "worktree", "remove", "--force", str(wt_path), cwd=project_path
        )

    @pytest.mark.asyncio
    async def test_remove_worktree_failure(
        self, project_path: Path, tmp_path: Path
    ):
        """remove_worktree returns False on failure."""
        wt_path = tmp_path / "worktrees" / "nonexistent"

        with patch("pct.git.worktree._run_git", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (128, "", "fatal: not a worktree")

            result = await remove_worktree(project_path, wt_path)

        assert result is False
