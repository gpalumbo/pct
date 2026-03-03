"""Tests for agent models."""

from pct.agent.models import (
    AgentResult,
    AssembledContext,
    ContextMetadata,
    LLMMessage,
    ToolCall,
    ToolResult,
)
from pct.models.enums import TaskOutcome


class TestAgentResult:
    def test_defaults(self):
        r = AgentResult()
        assert r.outcome == TaskOutcome.in_progress
        assert r.output == ""
        assert r.tool_calls == []
        assert r.error is None

    def test_approved(self):
        r = AgentResult(
            outcome=TaskOutcome.approved,
            output="Done!",
            tokens_input=100,
            tokens_output=50,
        )
        assert r.outcome == TaskOutcome.approved


class TestToolCall:
    def test_round_trip(self):
        tc = ToolCall(id="call_1", function_name="read", arguments='{"source": "test.md"}')
        assert tc.function_name == "read"
        assert tc.arguments == '{"source": "test.md"}'
        assert tc.id == "call_1"


class TestToolResult:
    def test_basic(self):
        tr = ToolResult(tool_call_id="call_1", name="read", output="content")
        assert tr.tool_call_id == "call_1"
        assert tr.output == "content"
        assert tr.error is None


class TestLLMMessage:
    def test_basic(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is None
        assert msg.tokens is None


class TestAssembledContext:
    def test_full_text_all_parts(self):
        ctx = AssembledContext(base="base", retries="retries", rag="rag")
        assert ctx.full_text == "base\n\nretries\n\nrag"

    def test_full_text_empty_parts(self):
        ctx = AssembledContext(base="only base")
        assert ctx.full_text == "only base"

    def test_metadata_defaults(self):
        ctx = AssembledContext()
        assert ctx.metadata.total_tokens == 0
        assert ctx.metadata.items_included == 0


class TestContextMetadata:
    def test_defaults(self):
        cm = ContextMetadata()
        assert cm.total_tokens == 0
        assert cm.tier_breakdown == {}
