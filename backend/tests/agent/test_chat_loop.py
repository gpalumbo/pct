"""Tests for chat loop."""

import json

from pct.agent.chat_loop import build_messages, execute_chat_turn
from pct.agent.models import AgentResult, AssembledContext, ToolCall
from pct.agent.tools._base import ToolRegistry
from pct.models.enums import TaskOutcome


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, responses=None):
        self.responses = responses or [
            AgentResult(outcome=TaskOutcome.approved, output="Done")
        ]
        self._call_count = 0

    async def execute(self, messages, on_token=None, tools=None):
        result = self.responses[min(self._call_count, len(self.responses) - 1)]
        self._call_count += 1
        return result

    async def interrupt(self):
        pass


class MockTool:
    def __init__(self, result="tool result"):
        self._result = result

    @property
    def name(self):
        return "mock_tool"

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": "mock_tool",
                "description": "A mock tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }

    async def execute(self, arguments: str) -> str:
        return self._result


class TestBuildMessages:
    def test_with_system_prompt(self):
        ctx = AssembledContext(base="Hello world")
        msgs = build_messages(ctx, system_prompt="You are helpful.")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are helpful."
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "Hello world"

    def test_without_system_prompt(self):
        ctx = AssembledContext(base="Hello world")
        msgs = build_messages(ctx)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"


class TestChatLoop:
    async def test_no_tools(self):
        provider = MockProvider()
        ctx = AssembledContext(base="Hi")
        result = await execute_chat_turn(provider, ctx)
        assert result.outcome == TaskOutcome.approved
        assert result.output == "Done"

    async def test_with_tools_no_calls(self):
        provider = MockProvider()
        registry = ToolRegistry()
        registry.register(MockTool())
        ctx = AssembledContext(base="Hi")
        result = await execute_chat_turn(provider, ctx, tool_registry=registry)
        assert result.outcome == TaskOutcome.approved

    async def test_tool_execution(self):
        # First call returns tool calls, second call returns final result
        provider = MockProvider([
            AgentResult(
                outcome=TaskOutcome.in_progress,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        function_name="mock_tool",
                        arguments="{}",
                    )
                ],
            ),
            AgentResult(outcome=TaskOutcome.approved, output="Final"),
        ])
        registry = ToolRegistry()
        registry.register(MockTool("tool output"))

        ctx = AssembledContext(base="Do something")
        result = await execute_chat_turn(provider, ctx, tool_registry=registry)
        assert result.outcome == TaskOutcome.approved
        assert len(result.tool_calls) >= 1

    async def test_error_handling(self):
        class ErrorProvider:
            async def execute(self, messages, on_token=None, tools=None):
                raise RuntimeError("Provider error")

            async def interrupt(self):
                pass

        ctx = AssembledContext(base="Hi")
        result = await execute_chat_turn(ErrorProvider(), ctx)
        assert result.outcome == TaskOutcome.error
        assert "Provider error" in result.error

    async def test_token_callback(self):
        tokens = []

        async def on_token(t):
            tokens.append(t)

        provider = MockProvider()
        ctx = AssembledContext(base="Hi")
        await execute_chat_turn(provider, ctx, on_token=on_token)
        # Provider mock doesn't call on_token, so tokens stays empty
        # This just tests that on_token is passed through without error

    async def test_messages_recorded(self):
        provider = MockProvider()
        ctx = AssembledContext(base="Hello")
        result = await execute_chat_turn(
            provider, ctx, system_prompt="Be helpful."
        )
        # Should have system + user messages plus the assistant response
        assert len(result.messages) >= 2
