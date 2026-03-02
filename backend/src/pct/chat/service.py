"""Chat service — session and message CRUD."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from pct.models.chat import ChatMessage
from pct.models.enums import MessageRole
from pct.storage.chat_io import append_message, list_sessions, load_messages, new_session


class ChatService:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def list_sessions(self) -> list[str]:
        return list_sessions(self.project_root)

    def get_or_create_session(self, session_id: str) -> list[ChatMessage]:
        messages = load_messages(self.project_root, session_id)
        if not messages:
            new_session(self.project_root, session_id)
        return messages

    def create_session(self, session_id: str) -> str:
        new_session(self.project_root, session_id)
        return session_id

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        return load_messages(self.project_root, session_id)

    def add_message(self, session_id: str, role: MessageRole, content: str) -> ChatMessage:
        msg = ChatMessage(
            id=str(uuid.uuid4())[:8],
            role=role,
            content=content,
            created_at=datetime.now(UTC),
        )
        append_message(self.project_root, session_id, msg)
        return msg

    def update_message(
        self,
        session_id: str,
        message_id: str,
        content: str | None = None,
        role: MessageRole | None = None,
        included: bool | None = None,
    ) -> ChatMessage | None:
        """Update a message by rewriting the session file."""
        messages = load_messages(self.project_root, session_id)
        target = None
        for msg in messages:
            if msg.id == message_id:
                if content is not None:
                    msg.content = content
                if role is not None:
                    msg.role = role
                if included is not None:
                    msg.included = included
                target = msg
                break
        if target is None:
            return None
        self._rewrite_session(session_id, messages)
        return target

    def delete_message(self, session_id: str, message_id: str) -> bool:
        messages = load_messages(self.project_root, session_id)
        filtered = [m for m in messages if m.id != message_id]
        if len(filtered) == len(messages):
            return False
        self._rewrite_session(session_id, filtered)
        return True

    def truncate_from(self, session_id: str, message_id: str) -> int:
        """Delete the specified message and all subsequent. Returns count deleted."""
        messages = load_messages(self.project_root, session_id)
        idx = None
        for i, m in enumerate(messages):
            if m.id == message_id:
                idx = i
                break
        if idx is None:
            return 0
        kept = messages[:idx]
        deleted_count = len(messages) - idx
        self._rewrite_session(session_id, kept)
        return deleted_count

    def _rewrite_session(self, session_id: str, messages: list[ChatMessage]) -> None:
        """Rewrite entire session from message list."""
        import json

        path = self.project_root / ".pct" / "chat_history" / f"{session_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(m.model_dump(mode="json"), ensure_ascii=False) + "\n" for m in messages]
        path.write_text("".join(lines), encoding="utf-8")
