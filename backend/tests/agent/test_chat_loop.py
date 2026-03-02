"""Tests for chat loop."""


from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AgentResult, TaskOutcome, ToolCall
from pct.agent.tools._base import ToolRegistry


class MockProvider:
    """Mock provider for testing."""

    def __init__(self, responses=None):
        self.responses = responses or [AgentResult(outcome=TaskOutcome.success, output="Done")]
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
    def description(self):
        return "A mock tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        return self._result


class TestChatLoop:
    async def test_no_tools(self):
        provider = MockProvider()
        result = await execute_chat_turn(provider, [{"role": "user", "content": "Hi"}])
        assert result.outcome == TaskOutcome.success
        assert result.output == "Done"

    async def test_with_tools_no_calls(self):
        provider = MockProvider()
        registry = ToolRegistry()
        registry.register(MockTool())
        result = await execute_chat_turn(
            provider, [{"role": "user", "content": "Hi"}], tool_registry=registry
        )
        assert result.outcome == TaskOutcome.success

    async def test_tool_execution(self):
        # First call returns tool calls, second call returns final result
        provider = MockProvider([
            AgentResult(
                outcome=TaskOutcome.in_progress,
                tool_calls=[ToolCall(tool_name="mock_tool", arguments={})],
            ),
            AgentResult(outcome=TaskOutcome.success, output="Final"),
        ])
        registry = ToolRegistry()
        registry.register(MockTool("tool output"))

        result = await execute_chat_turn(
            provider, [{"role": "user", "content": "Do something"}], tool_registry=registry
        )
        assert result.outcome == TaskOutcome.success
        assert len(result.tool_calls) >= 1

    async def test_error_handling(self):
        class ErrorProvider:
            async def execute(self, messages, on_token=None, tools=None):
                raise RuntimeError("Provider error")

            async def interrupt(self):
                pass

        result = await execute_chat_turn(ErrorProvider(), [{"role": "user", "content": "Hi"}])
        assert result.outcome == TaskOutcome.failure
        assert "Provider error" in result.error

    async def test_token_callback(self):
        tokens = []

        async def on_token(t):
            tokens.append(t)

        provider = MockProvider()
        await execute_chat_turn(provider, [{"role": "user", "content": "Hi"}], on_token=on_token)
        # Provider mock doesn't call on_token, so tokens stays empty
        # This just tests that on_token is passed through without error
