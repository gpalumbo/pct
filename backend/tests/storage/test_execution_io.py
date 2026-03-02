"""Tests for execution I/O."""

from pathlib import Path

from pct.storage.execution_io import archive_task, read_attempts, write_attempt


class TestExecutionIO:
    def test_write_and_read_attempt(self, tmp_project_root: Path):
        metadata = {"status": "success", "agent_id": "coding-agent", "duration_seconds": 10.5}
        attempt_dir = write_attempt(
            tmp_project_root,
            "task-1",
            metadata=metadata,
            output="# Output\n\nResult here.",
            agent_log=[{"role": "user", "content": "Do X"}, {"role": "assistant", "content": "Done"}],
        )
        assert attempt_dir.name == "attempt-001"
        assert (attempt_dir / "metadata.yaml").exists()
        assert (attempt_dir / "output.md").exists()
        assert (attempt_dir / "agent_log.jsonl").exists()

        attempts = read_attempts(tmp_project_root, "task-1")
        assert len(attempts) == 1
        assert attempts[0]["status"] == "success"
        assert attempts[0]["agent_id"] == "coding-agent"

    def test_multiple_attempts(self, tmp_project_root: Path):
        write_attempt(tmp_project_root, "t1", {"attempt": 1})
        write_attempt(tmp_project_root, "t1", {"attempt": 2})
        write_attempt(tmp_project_root, "t1", {"attempt": 3})

        attempts = read_attempts(tmp_project_root, "t1")
        assert len(attempts) == 3
        assert attempts[0]["attempt"] == 1
        assert attempts[2]["attempt"] == 3

    def test_attempt_zero_padded(self, tmp_project_root: Path):
        dir1 = write_attempt(tmp_project_root, "t1", {"n": 1})
        assert dir1.name == "attempt-001"
        dir2 = write_attempt(tmp_project_root, "t1", {"n": 2})
        assert dir2.name == "attempt-002"

    def test_read_nonexistent(self, tmp_project_root: Path):
        assert read_attempts(tmp_project_root, "nonexistent") == []

    def test_write_without_agent_log(self, tmp_project_root: Path):
        attempt_dir = write_attempt(tmp_project_root, "t1", {"minimal": True})
        assert not (attempt_dir / "agent_log.jsonl").exists()
        assert (attempt_dir / "metadata.yaml").exists()
        assert (attempt_dir / "output.md").exists()

    def test_archive_task(self, tmp_project_root: Path):
        write_attempt(tmp_project_root, "t1", {"data": "test"})

        # Ensure completed-tasks dir exists
        (tmp_project_root / ".pct" / "execution" / "completed-tasks").mkdir(parents=True, exist_ok=True)

        assert archive_task(tmp_project_root, "t1") is True
        # Active dir should be gone
        assert not (tmp_project_root / ".pct" / "execution" / "active-tasks" / "t1").exists()
        # Completed dir should exist
        assert (tmp_project_root / ".pct" / "execution" / "completed-tasks" / "t1").is_dir()

    def test_archive_nonexistent(self, tmp_project_root: Path):
        assert archive_task(tmp_project_root, "nope") is False
