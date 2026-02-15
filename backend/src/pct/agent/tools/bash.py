"""Bash shell tool for agent execution."""

from __future__ import annotations

import asyncio
import json
from typing import Any


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
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            return f"[error] Command timed out after {self._timeout}s"

        output = stdout.decode()
        if stderr:
            output += stderr.decode()
        return output
