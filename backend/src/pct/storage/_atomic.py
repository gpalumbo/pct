"""Atomic file write helper — works on Windows and Unix."""

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write(target: Path, content: str) -> None:
    """Write content to target atomically via temp file + rename.

    On Windows, we close the fd before writing to avoid file locking issues.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    try:
        os.close(fd)  # Close fd so write_text can open it
        Path(tmp_path).write_text(content, encoding="utf-8")
        Path(tmp_path).replace(target)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
