"""Tests for tool registry."""

import json

import pytest

from pct.agent.tools._base import ToolRegistry


class MockTool:
    @property
    def name(self):
        return "test"

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": "test",
                "description": "Test tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }

    async def execute(self, arguments: str) -> str:
        return "test result"


class ErrorTool:
    @property
    def name(self):
        return "error"

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": "error",
                "description": "Error tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }

    async def execute(self, arguments: str) -> str:
        raise ValueError("Tool error")


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        assert registry.get("test") is tool
        assert registry.get("nonexistent") is None

    def test_get_definitions(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        defs = registry.get_definitions()
        assert len(defs) == 1
        assert defs[0]["function"]["name"] == "test"

    async def test_execute(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        result = await registry.execute("test", "{}")
        assert result == "test result"

    async def test_execute_unknown(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="Unknown tool"):
            await registry.execute("nonexistent", "{}")

    async def test_execute_error_propagates(self):
        registry = ToolRegistry()
        registry.register(ErrorTool())
        with pytest.raises(ValueError, match="Tool error"):
            await registry.execute("error", "{}")

    def test_tool_names(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        assert "test" in registry.tool_names
