"""Tests for pct.agent.tools — Tool protocol, BashTool, ToolRegistry, and tool loop."""

from __future__ import annotations

import json
import sys

import pytest

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AssembledContext, ContextMetadata, TaskOutcome
from pct.agent.providers.local_llm import LocalLLMProvider
from pct.agent.tools import BashTool, ToolRegistry

from tests.agent.conftest import FakeLlama


# ---------------------------------------------------------------------------
# BashTool
# ---------------------------------------------------------------------------


class TestBashTool:
    async def test_bash_tool_runs_command(self):
        """echo hello → 'hello\\n'."""
        tool = BashTool()
        result = await tool.execute(json.dumps({"command": "echo hello"}))
        assert result.strip() == "hello"

    async def test_bash_tool_captures_stderr(self):
        """stderr output is included in the result."""
        tool = BashTool()
        result = await tool.execute(
            json.dumps({"command": "echo err >&2"})
        )
        assert "err" in result

    async def test_bash_tool_timeout(self):
        """A long-running command times out and reports an error."""
        tool = BashTool(timeout=0.1)
        # sleep 10 will definitely exceed 0.1s
        cmd = "sleep 10" if sys.platform != "win32" else "ping -n 10 127.0.0.1"
        result = await tool.execute(json.dumps({"command": cmd}))
        assert "timed out" in result

    def test_bash_tool_definition_schema(self):
        """definition returns a valid OpenAI function schema."""
        tool = BashTool()
        defn = tool.definition
        assert defn["type"] == "function"
        assert defn["function"]["name"] == "bash"
        params = defn["function"]["parameters"]
        assert "command" in params["properties"]
        assert "command" in params["required"]


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    def test_get_definitions(self):
        """get_definitions returns a list of tool schemas."""
        registry = ToolRegistry()
        registry.register(BashTool())
        defs = registry.get_definitions()
        assert len(defs) == 1
        assert defs[0]["function"]["name"] == "bash"

    async def test_execute_dispatches(self):
        """execute dispatches to the correct tool by name."""
        registry = ToolRegistry()
        registry.register(BashTool())
        result = await registry.execute("bash", json.dumps({"command": "echo dispatched"}))
        assert "dispatched" in result

    async def test_unknown_tool_raises(self):
        """execute raises KeyError for an unknown tool name."""
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="Unknown tool"):
            await registry.execute("nonexistent", "{}")


# ---------------------------------------------------------------------------
# Tool loop integration (via chat_loop + FakeLlama)
# ---------------------------------------------------------------------------


def _make_tool_call(call_id: str, name: str, arguments: dict) -> dict:
    """Helper to build an OpenAI-format tool_call dict for FakeLlama."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }


def _sample_context() -> AssembledContext:
    return AssembledContext(
        base="Do the task.",
        metadata=ContextMetadata(total_tokens=10, budget=8000),
    )


class TestToolLoop:
    async def test_tool_loop_single_call(self):
        """LLM requests bash → tool runs → LLM gets result → final output."""
        llama = FakeLlama(
            responses=["Final answer: it worked."],
            tool_call_responses={
                0: [_make_tool_call("call_1", "bash", {"command": "echo hello"})],
            },
        )
        provider = LocalLLMProvider(backend=llama)

        registry = ToolRegistry()
        registry.register(BashTool())

        result = await execute_chat_turn(
            provider, _sample_context(), tool_registry=registry
        )

        assert result.outcome == TaskOutcome.APPROVED
        assert result.output == "Final answer: it worked."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].function_name == "bash"
        # LLM was called twice: once returning tool_call, once returning text
        assert llama.call_count == 2

    async def test_tool_loop_no_tools(self):
        """Without a registry, works as before (no regression)."""
        llama = FakeLlama(responses=["Plain response."])
        provider = LocalLLMProvider(backend=llama)

        result = await execute_chat_turn(provider, _sample_context())

        assert result.outcome == TaskOutcome.APPROVED
        assert result.output == "Plain response."
        assert result.tool_calls == []
        assert llama.call_count == 1

    async def test_tool_loop_max_iterations(self):
        """Safety cap prevents infinite tool-call loops."""
        # Every call returns a tool_call — should stop at max_iterations
        always_tool = {
            i: [_make_tool_call(f"call_{i}", "bash", {"command": "echo loop"})]
            for i in range(20)
        }
        llama = FakeLlama(
            responses=["never reached"],
            tool_call_responses=always_tool,
        )
        provider = LocalLLMProvider(backend=llama)

        registry = ToolRegistry()
        registry.register(BashTool())

        result = await execute_chat_turn(
            provider,
            _sample_context(),
            tool_registry=registry,
            max_tool_iterations=3,
        )

        assert result.outcome == TaskOutcome.ERROR
        assert "exceeded" in result.error
        # Should have called provider at most max_iterations + 1 times
        assert llama.call_count <= 4