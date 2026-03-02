"""Agent pool — concurrency management with semaphores."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from pct.agent.models import AgentResult
from pct.agent.protocols import AgentProvider


class AgentPool:
    """Manages concurrent agent execution with semaphores per provider type."""

    def __init__(self, remote_limit: int = 2, local_limit: int = 1):
        self.semaphores = {
            "remote": asyncio.Semaphore(remote_limit),
            "local": asyncio.Semaphore(local_limit),
        }

    def _get_provider_type(self, provider: AgentProvider) -> str:
        """Determine the semaphore key for a provider."""
        from pct.agent.providers.local_llm import LocalLLMProvider

        if isinstance(provider, LocalLLMProvider):
            return "local"
        return "remote"

    async def execute(
        self,
        provider: AgentProvider,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        """Execute with concurrency limiting."""
        provider_type = self._get_provider_type(provider)
        semaphore = self.semaphores.get(provider_type, self.semaphores["remote"])

        async with semaphore:
            return await provider.execute(messages, on_token=on_token, tools=tools)
