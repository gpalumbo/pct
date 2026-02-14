"""Data models for the planning chat system."""

from datetime import datetime, UTC
from uuid import uuid4

from pydantic import BaseModel, Field


class PlanningMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tokens: int | None = None
    included: bool = True
    agent_id: str | None = None
    model_id: str | None = None


class ChatSession(BaseModel):
    id: str
    title: str = ""
    agent_id: str | None = None
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0


class SendMessageRequest(BaseModel):
    content: str
    agent_id: str | None = None


class UpdateMessageRequest(BaseModel):
    role: str | None = None
    content: str | None = None
    included: bool | None = None
