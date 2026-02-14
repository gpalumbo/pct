"""Tests for pct.agent.protocols — protocol conformance checks."""

import asyncio
import inspect

from pct.agent.models import AgentResult
from pct.agent.protocols import AgentProvider, CompletionBackend
from pct.agent.providers.local_llm import LocalLLMProvider

from tests.agent.conftest import FakeLlama


class TestProtocolConformance:
    def test_local_provider_is_agent_provider(self, local_provider):
        """LocalLLMProvider satisfies the AgentProvider protocol."""
        assert isinstance(local_provider, AgentProvider)

    def test_fake_llama_is_completion_backend(self, fake_llama):
        """FakeLlama satisfies the CompletionBackend protocol."""
        assert isinstance(fake_llama, CompletionBackend)

    async def test_provider_execute_returns_agent_result(self, local_provider):
        """Provider.execute() returns an AgentResult instance."""
        messages = [{"role": "user", "content": "Hello"}]
        result = await local_provider.execute(messages)
        assert isinstance(result, AgentResult)

    def test_provider_execute_is_coroutine(self, local_provider):
        """Provider.execute is a coroutine function."""
        assert inspect.iscoroutinefunction(local_provider.execute)
