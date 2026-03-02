"""Tests for tool registry."""


from pct.agent.tools._base import ToolRegistry


class MockTool:
    @property
    def name(self):
        return "test"

    @property
    def description(self):
        return "Test tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        return "test result"


class ErrorTool:
    @property
    def name(self):
        return "error"

    @property
    def description(self):
        return "Error tool"

    @property
    def parameters(self):
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
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
        result = await registry.execute("test")
        assert result == "test result"

    async def test_execute_unknown(self):
        registry = ToolRegistry()
        result = await registry.execute("nonexistent")
        assert "Unknown tool" in result

    async def test_execute_error_handling(self):
        registry = ToolRegistry()
        registry.register(ErrorTool())
        result = await registry.execute("error")
        assert "Error executing error" in result

    def test_tool_names(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        assert "test" in registry.tool_names
