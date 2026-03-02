"""BashTool — execute shell commands with 30s timeout."""

import asyncio
from typing import Any


class BashTool:
    def __init__(self, cwd: str | None = None):
        self.cwd = cwd

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a shell command. 30-second timeout."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
            },
            "required": ["command"],
        }

    async def execute(self, command: str = "", **kwargs: Any) -> str:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            except TimeoutError:
                proc.kill()
                return "Error: Command timed out (30s limit)"

            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")
            result = ""
            if output:
                result += output
            if errors:
                result += f"\n[stderr]\n{errors}"
            if proc.returncode != 0:
                result += f"\n[exit code: {proc.returncode}]"
            return result.strip() or "(no output)"
        except Exception as e:
            return f"Error: {e}"
