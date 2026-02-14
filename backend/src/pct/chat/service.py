"""Persistence service for planning chat sessions and messages.

Storage layout:
  <project_root>/.pct/chat_history/sessions.yaml
  <project_root>/.pct/chat_history/planning-<nnn>.jsonl
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

import yaml

from pct import config
from pct.chat.models import ChatSession, PlanningMessage, UpdateMessageRequest


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _chat_history_dir() -> Path:
    if config.settings.project_root:
        root = Path(config.settings.project_root)
    else:
        root = Path.cwd()
    base = root / ".pct" / "chat_history"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _sessions_path() -> Path:
    return _chat_history_dir() / "sessions.yaml"


def _messages_path(session_id: str) -> Path:
    return _chat_history_dir() / f"{session_id}.jsonl"


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------


def _load_sessions() -> list[dict]:
    path = _sessions_path()
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


def _save_sessions(sessions: list[dict]) -> None:
    path = _sessions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(sessions, f, default_flow_style=False, sort_keys=False)


def list_sessions() -> list[ChatSession]:
    return [ChatSession(**s) for s in _load_sessions()]


def get_session(session_id: str) -> ChatSession | None:
    for s in _load_sessions():
        if s.get("id") == session_id:
            return ChatSession(**s)
    return None


def create_session(title: str, agent_id: str | None = None) -> ChatSession:
    sessions = _load_sessions()
    # Derive next session number
    existing_nums = []
    for s in sessions:
        sid = s.get("id", "")
        if sid.startswith("planning-"):
            try:
                existing_nums.append(int(sid.split("-", 1)[1]))
            except ValueError:
                pass
    next_num = max(existing_nums, default=0) + 1
    session_id = f"planning-{next_num:03d}"

    session = ChatSession(id=session_id, title=title, agent_id=agent_id)
    sessions.append(session.model_dump(mode="json"))
    _save_sessions(sessions)
    return session


def get_or_create_default_session() -> ChatSession:
    sessions = list_sessions()
    if sessions:
        return sessions[0]
    return create_session("Planning")


def _update_session_metadata(session_id: str) -> None:
    """Update message_count and updated timestamp for a session."""
    sessions = _load_sessions()
    messages = load_messages(session_id)
    for i, s in enumerate(sessions):
        if s.get("id") == session_id:
            s["message_count"] = len(messages)
            s["updated"] = datetime.now(UTC).isoformat()
            sessions[i] = s
            _save_sessions(sessions)
            return


# ---------------------------------------------------------------------------
# Message I/O (JSONL)
# ---------------------------------------------------------------------------


def load_messages(session_id: str) -> list[PlanningMessage]:
    path = _messages_path(session_id)
    if not path.exists():
        return []
    messages = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(PlanningMessage(**json.loads(line)))
    return messages


def append_message(session_id: str, msg: PlanningMessage) -> PlanningMessage:
    path = _messages_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(msg.model_dump_json() + "\n")
    _update_session_metadata(session_id)
    return msg


def update_message(
    session_id: str, message_id: str, updates: UpdateMessageRequest
) -> PlanningMessage | None:
    """Update a message by rewriting the JSONL file."""
    messages = load_messages(session_id)
    target = None
    for i, m in enumerate(messages):
        if m.id == message_id:
            if updates.role is not None:
                m.role = updates.role
            if updates.content is not None:
                m.content = updates.content
            if updates.included is not None:
                m.included = updates.included
            messages[i] = m
            target = m
            break
    if target is None:
        return None
    # Rewrite the file
    path = _messages_path(session_id)
    with open(path, "w") as f:
        for m in messages:
            f.write(m.model_dump_json() + "\n")
    return target


def delete_message(session_id: str, message_id: str) -> bool:
    """Delete a message by rewriting the JSONL file without it."""
    messages = load_messages(session_id)
    new_messages = [m for m in messages if m.id != message_id]
    if len(new_messages) == len(messages):
        return False
    path = _messages_path(session_id)
    with open(path, "w") as f:
        for m in new_messages:
            f.write(m.model_dump_json() + "\n")
    _update_session_metadata(session_id)
    return True


def get_included_messages(session_id: str) -> list[PlanningMessage]:
    return [m for m in load_messages(session_id) if m.included]
