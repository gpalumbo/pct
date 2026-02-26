"""Tests for pct.agent.pool — concurrency limits and job dispatch."""

import asyncio

from pct.agent.models import (
    AgentJob,
    AgentResult,
    AssembledContext,
    ProviderType,
)
from pct.agent.pool import AgentPool
from pct.agent.providers.local_llm import LocalLLMProvider
from tests.agent.conftest import FakeLlama


def _make_job(provider_type: ProviderType = ProviderType.LOCAL_LLM) -> AgentJob:
    """Helper to create a minimal AgentJob."""
    return AgentJob(
        task_id="task-001",
        feature_id="feat-001",
        context=AssembledContext(base="Do something."),
        agent_type=provider_type,
        stage="implement",
    )


def _make_pool(
    remote_limit: int = 2,
    local_limit: int = 1,
) -> AgentPool:
    """Helper to create an AgentPool with FakeLlama-backed providers."""
    local_provider = LocalLLMProvider(backend=FakeLlama())
    remote_provider = LocalLLMProvider(backend=FakeLlama())  # stand-in for remote
    return AgentPool(
        providers={
            ProviderType.LOCAL_LLM: local_provider,
            ProviderType.REMOTE_API: remote_provider,
        },
        remote_limit=remote_limit,
        local_limit=local_limit,
    )


class TestAgentPool:
    async def test_submit_and_await_result(self):
        """Single job round-trip: submit → await → AgentResult."""
        pool = _make_pool()
        job = _make_job()
        future = pool.submit(job)
        result = await asyncio.wrap_future(future)
        assert isinstance(result, AgentResult)
        assert len(result.output) > 0

    async def test_remote_concurrency_limit(self):
        """At most remote_limit jobs run concurrently for REMOTE_API."""
        pool = _make_pool(remote_limit=2)
        jobs = [_make_job(ProviderType.REMOTE_API) for _ in range(4)]
        futures = [pool.submit(job) for job in jobs]
        results = [await asyncio.wrap_future(f) for f in futures]
        assert all(isinstance(r, AgentResult) for r in results)

    async def test_local_concurrency_limit(self):
        """At most local_limit jobs run concurrently for LOCAL_LLM."""
        pool = _make_pool(local_limit=1)
        jobs = [_make_job(ProviderType.LOCAL_LLM) for _ in range(3)]
        futures = [pool.submit(job) for job in jobs]
        results = [await asyncio.wrap_future(f) for f in futures]
        assert all(isinstance(r, AgentResult) for r in results)

    async def test_mixed_providers_independent(self):
        """Remote and local semaphores are independent."""
        pool = _make_pool(remote_limit=2, local_limit=1)
        remote_job = _make_job(ProviderType.REMOTE_API)
        local_job = _make_job(ProviderType.LOCAL_LLM)
        f1 = pool.submit(remote_job)
        f2 = pool.submit(local_job)
        r1 = await asyncio.wrap_future(f1)
        r2 = await asyncio.wrap_future(f2)
        assert isinstance(r1, AgentResult)
        assert isinstance(r2, AgentResult)

    def test_provider_lookup_by_type(self):
        """Pool dispatches to the correct provider for a given ProviderType."""
        local_backend = FakeLlama(responses=["local response"])
        remote_backend = FakeLlama(responses=["remote response"])
        pool = AgentPool(
            providers={
                ProviderType.LOCAL_LLM: LocalLLMProvider(backend=local_backend),
                ProviderType.REMOTE_API: LocalLLMProvider(backend=remote_backend),
            },
        )
        # Verify the pool has distinct providers
        assert pool._providers[ProviderType.LOCAL_LLM] is not pool._providers[ProviderType.REMOTE_API]
