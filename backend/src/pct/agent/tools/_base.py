"""Tool protocol and registry for the agent execution engine."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Interface that all agent tools must implement."""

    @property
    def name(self) -> str: ...

    @property
    def definition(self) -> dict[str, Any]:
        """OpenAI function-calling schema dict."""
        ...

    async def execute(self, arguments: str) -> str:
        """Run the tool with the given JSON arguments string. Returns output text."""
        ...


class ToolRegistry:
    """Holds tools by name, provides definitions for the LLM, and dispatches execution."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        return [t.definition for t in self._tools.values()]

    async def execute(self, name: str, arguments: str) -> str:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return await self._tools[name].execute(arguments)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())
