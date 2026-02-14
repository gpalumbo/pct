"""Tool protocol, registry, and built-in tools for the agent execution engine."""

from __future__ import annotations

import asyncio
import json
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


class BashTool:
    """Runs a shell command via asyncio.create_subprocess_shell."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "bash"

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Run a shell command and return its output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute.",
                        },
                    },
                    "required": ["command"],
                },
            },
        }

    async def execute(self, arguments: str) -> str:
        parsed = json.loads(arguments)
        command = parsed["command"]

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"[error] Command timed out after {self._timeout}s"

        output = stdout.decode()
        if stderr:
            output += stderr.decode()
        return output


class ToolRegistry:
    """Holds tools by name, provides definitions for the LLM, and dispatches execution."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_definitions(self) -> list[dict[str, Any]]:
        return [t.definition for t in self._tools.values()]

    async def execute(self, name: str, arguments: str) -> str:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return await self._tools[name].execute(arguments)