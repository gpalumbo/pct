"""Chat history I/O — JSONL format."""

import json
from pathlib import Path

from pct.models.chat import ChatMessage


def _chat_dir(project_root: Path) -> Path:
    return project_root / ".pct" / "chat_history"


def _session_path(project_root: Path, session_id: str) -> Path:
    return _chat_dir(project_root) / f"{session_id}.jsonl"


def append_message(project_root: Path, session_id: str, message: ChatMessage) -> None:
    """Append a single message to a JSONL chat log."""
    chat_dir = _chat_dir(project_root)
    chat_dir.mkdir(parents=True, exist_ok=True)
    path = _session_path(project_root, session_id)
    line = json.dumps(message.model_dump(mode="json"), ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def load_messages(project_root: Path, session_id: str) -> list[ChatMessage]:
    """Load all messages from a JSONL chat log."""
    path = _session_path(project_root, session_id)
    if not path.exists():
        return []
    messages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            data = json.loads(line)
            messages.append(ChatMessage(**data))
    return messages


def new_session(project_root: Path, session_id: str) -> Path:
    """Create or clear a chat session file. Returns path."""
    chat_dir = _chat_dir(project_root)
    chat_dir.mkdir(parents=True, exist_ok=True)
    path = _session_path(project_root, session_id)
    path.write_text("", encoding="utf-8")
    return path


def list_sessions(project_root: Path) -> list[str]:
    """List all session IDs."""
    chat_dir = _chat_dir(project_root)
    if not chat_dir.exists():
        return []
    return sorted(f.stem for f in chat_dir.glob("*.jsonl"))
