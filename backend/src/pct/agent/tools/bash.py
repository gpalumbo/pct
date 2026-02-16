"""Bash shell tool for agent execution."""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any


class BashTool:
    """Runs a shell command via subprocess in a thread."""

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

        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._run, command),
                timeout=self._timeout,
            )
        except TimeoutError:
            return f"[error] Command timed out after {self._timeout}s"

        return result

    def _run(self, command: str) -> str:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=self._timeout,
        )
        output = proc.stdout.decode()
        if proc.stderr:
            output += proc.stderr.decode()
        return output
