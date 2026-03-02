"""Tests for agent models."""

from pct.agent.models import AgentResult, TaskOutcome, ToolCall


class TestAgentResult:
    def test_defaults(self):
        r = AgentResult()
        assert r.outcome == TaskOutcome.in_progress
        assert r.output == ""
        assert r.tool_calls == []
        assert r.error is None

    def test_success(self):
        r = AgentResult(outcome=TaskOutcome.success, output="Done!", tokens_input=100, tokens_output=50)
        assert r.outcome == TaskOutcome.success


class TestToolCall:
    def test_round_trip(self):
        tc = ToolCall(tool_name="read", arguments={"path": "test.md"}, result="content")
        assert tc.tool_name == "read"
        assert tc.arguments == {"path": "test.md"}
