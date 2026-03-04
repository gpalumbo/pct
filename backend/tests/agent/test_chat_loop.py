"""Tests for chat loop."""

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AgentResult, AssembledContext, ToolCall
from pct.agent.tools._base import ToolRegistry
from pct.models.enums import TaskOutcome


class MockProvider:
    """Mock provider for testing."""

    agent_config = None

    def __init__(self, responses=None):
        self.responses = responses or [
            AgentResult(outcome=TaskOutcome.approved, output="Done")
        ]
        self._call_count = 0

    @property
    def name(self) -> str:
        return "MockProvider"

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


class TestChatLoop:
    async def test_no_tools(self):
        provider = MockProvider()
        ctx = AssembledContext()
        ctx.append_user("Hi")
        result = await execute_chat_turn(provider, ctx)
        assert result.outcome == TaskOutcome.approved
        assert result.output == "Done"

    async def test_with_tools_no_calls(self):
        provider = MockProvider()
        registry = ToolRegistry()
        registry.register(MockTool())
        ctx = AssembledContext()
        ctx.append_user("Hi")
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

        ctx = AssembledContext()
        ctx.append_user("Do something")
        result = await execute_chat_turn(provider, ctx, tool_registry=registry)
        assert result.outcome == TaskOutcome.approved
        assert len(result.tool_calls) >= 1
        # Tool result should be recorded on the context
        tool_results = [m for m in ctx.messages if m.role == "tool_result"]
        assert len(tool_results) == 1
        assert tool_results[0].content == "tool output"

    async def test_error_handling(self):
        class ErrorProvider:
            agent_config = None
            name = "ErrorProvider"

            async def execute(self, messages, on_token=None, tools=None):
                raise RuntimeError("Provider error")

            async def interrupt(self):
                pass

        ctx = AssembledContext()
        ctx.append_user("Hi")
        result = await execute_chat_turn(ErrorProvider(), ctx)
        assert result.outcome == TaskOutcome.error
        assert "Provider error" in result.error

    async def test_token_callback(self):
        tokens = []

        async def on_token(t):
            tokens.append(t)

        provider = MockProvider()
        ctx = AssembledContext()
        ctx.append_user("Hi")
        await execute_chat_turn(provider, ctx, on_token=on_token)
        # Provider mock doesn't call on_token, so tokens stays empty
        # This just tests that on_token is passed through without error

    async def test_flush_bubble_called_on_iteration(self):
        """on_flush_bubble is called at iteration > 0."""
        flush_calls = []

        async def on_flush():
            flush_calls.append(True)

        provider = MockProvider([
            AgentResult(
                outcome=TaskOutcome.in_progress,
                tool_calls=[
                    ToolCall(id="c1", function_name="mock_tool", arguments="{}")
                ],
            ),
            AgentResult(outcome=TaskOutcome.approved, output="Final"),
        ])
        registry = ToolRegistry()
        registry.register(MockTool("output"))

        ctx = AssembledContext()
        ctx.append_user("Do it")
        result = await execute_chat_turn(
            provider, ctx, tool_registry=registry, on_flush_bubble=on_flush,
        )
        assert result.outcome == TaskOutcome.approved
        assert len(flush_calls) == 1

    async def test_context_messages_populated(self):
        """After a tool turn, context.messages should contain tool_results."""
        provider = MockProvider([
            AgentResult(
                outcome=TaskOutcome.in_progress,
                tool_calls=[
                    ToolCall(id="c1", function_name="mock_tool", arguments="{}")
                ],
            ),
            AgentResult(outcome=TaskOutcome.approved, output="Done"),
        ])
        registry = ToolRegistry()
        registry.register(MockTool("result_data"))

        ctx = AssembledContext(agent_prompt="Be helpful")
        ctx.append_user("Hello")
        await execute_chat_turn(provider, ctx, tool_registry=registry)

        # Should have: user + tool_result
        assert len(ctx.messages) == 2
        assert ctx.messages[0].role == "user"
        assert ctx.messages[1].role == "tool_result"
        assert ctx.messages[1].content == "result_data"

    async def test_system_prompt_in_llm_messages(self):
        """build_llm_messages includes system prompt from context."""
        ctx = AssembledContext(agent_prompt="Be helpful")
        ctx.append_user("Hello")
        msgs = ctx.build_llm_messages()
        assert msgs[0]["role"] == "system"
        assert "Be helpful" in msgs[0]["content"]
        assert msgs[1]["role"] == "user"
