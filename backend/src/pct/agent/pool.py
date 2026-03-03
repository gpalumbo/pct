"""Agent concurrency pool — dispatches jobs to providers with semaphore limits."""

from __future__ import annotations

import asyncio

from pct.agent.models import AgentJob, AgentResult
from pct.agent.protocols import AgentProvider
from pct.models.enums import ProviderType


class AgentPool:
    """Manages concurrent agent execution with per-provider-type limits.

    Parameters
    ----------
    providers : dict mapping ProviderType to an AgentProvider instance.
    remote_limit : max concurrent remote API jobs.
    local_limit : max concurrent local LLM jobs.
    """

    def __init__(
        self,
        providers: dict[ProviderType, AgentProvider],
        remote_limit: int = 2,
        local_limit: int = 1,
    ) -> None:
        self._providers = providers
        self._semaphores: dict[ProviderType, asyncio.Semaphore] = {
            ProviderType.remote_api: asyncio.Semaphore(remote_limit),
            ProviderType.local: asyncio.Semaphore(local_limit),
        }
        self._tasks: list[asyncio.Task[AgentResult]] = []

    def submit(self, job: AgentJob) -> asyncio.Future[AgentResult]:
        """Submit a job for execution. Returns a future for the result."""
        task = asyncio.ensure_future(self._run_job(job))
        self._tasks.append(task)
        return task

    async def _run_job(self, job: AgentJob) -> AgentResult:
        """Execute a single job, respecting the per-provider semaphore."""
        provider = self._providers[job.agent_type]
        semaphore = self._semaphores.get(job.agent_type, self._semaphores[ProviderType.remote_api])
        messages = [{"role": "user", "content": job.context.full_text}]
        async with semaphore:
            return await provider.execute(messages)

    async def shutdown(self) -> None:
        """Gracefully shut down the pool."""
        for task in self._tasks:
            if not task.done():
                task.cancel()
        self._tasks.clear()
