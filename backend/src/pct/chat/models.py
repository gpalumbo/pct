"""Chat request/response models."""

from pydantic import BaseModel

from pct.models.enums import MessageRole


class SessionCreate(BaseModel):
    session_id: str
    session_type: str = "planning"  # "planning" or "task-stage"


class MessageCreate(BaseModel):
    content: str
    role: MessageRole = MessageRole.user


class MessageUpdate(BaseModel):
    content: str | None = None
    role: MessageRole | None = None
    included: bool | None = None


class SendMessage(BaseModel):
    content: str
    agent_id: str | None = None


class SSEEvent(BaseModel):
    type: str  # "token", "done", "error"
    content: str = ""
    message_id: str | None = None
