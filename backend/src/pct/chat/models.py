"""Data models for the planning chat system."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class PlanningMessage(BaseModel):
    model_config = {"populate_by_name": True}

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    role: str  # "user", "assistant", "system", "tool", "tool_call", "tool_result"
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        validation_alias="timestamp",
    )
    tokens: int | None = None
    included: bool = True
    agent_id: str | None = None
    model_id: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None


class ChatSession(BaseModel):
    id: str
    title: str = ""
    agent_id: str | None = None
    feature_id: str | None = None
    task_id: str | None = None
    stage_id: str | None = None
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0


class SendMessageRequest(BaseModel):
    content: str
    agent_id: str | None = None
    artifact_path: str | None = None
    feature_id: str | None = None
    task_id: str | None = None


class UpdateMessageRequest(BaseModel):
    role: str | None = None
    content: str | None = None
    included: bool | None = None
