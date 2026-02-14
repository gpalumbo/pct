"""Tests for pct.agent.chat_loop — message building and single-turn execution."""

import asyncio

import pytest

from pct.agent.chat_loop import build_messages, execute_chat_turn
from pct.agent.models import AgentResult, AssembledContext, TaskOutcome


class TestBuildMessages:
    def test_build_messages_with_system_prompt(self, sample_context):
        """With a system prompt, messages start with system then user."""
        msgs = build_messages(sample_context, system_prompt="You are a coding assistant.")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are a coding assistant."
        assert msgs[1]["role"] == "user"
        assert sample_context.full_text in msgs[1]["content"]

    def test_build_messages_without_system_prompt(self, sample_context):
        """Without system prompt, only a user message is produced."""
        msgs = build_messages(sample_context)
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert sample_context.full_text in msgs[0]["content"]


class TestExecuteChatTurn:
    async def test_single_turn_execution(self, local_provider, sample_context):
        """execute_chat_turn returns an AgentResult with output."""
        result = await execute_chat_turn(local_provider, sample_context)
        assert isinstance(result, AgentResult)
        assert len(result.output) > 0

    async def test_streaming_callback_receives_tokens(self, local_provider, sample_context):
        """on_token callback is called for each streamed chunk."""
        tokens: list[str] = []

        async def collect(token: str) -> None:
            tokens.append(token)

        await execute_chat_turn(local_provider, sample_context, on_token=collect)
        assert len(tokens) > 0

    async def test_streaming_collects_full_output(self, local_provider, sample_context):
        """result.output equals all streamed tokens joined together."""
        tokens: list[str] = []

        async def collect(token: str) -> None:
            tokens.append(token)

        result = await execute_chat_turn(local_provider, sample_context, on_token=collect)
        assert result.output == "".join(tokens)

    async def test_timeout_raises(self, sample_context):
        """A very short timeout causes asyncio.TimeoutError."""

        class SlowProvider:
            async def execute(self, messages, on_token=None, tools=None):
                await asyncio.sleep(10)
                return AgentResult()

            async def interrupt(self):
                pass

        with pytest.raises(asyncio.TimeoutError):
            await execute_chat_turn(
                SlowProvider(), sample_context, timeout_seconds=0.01
            )

    async def test_error_handling_model_failure(self, sample_context, fake_llama_failing):
        """When the backend fails, result has outcome=ERROR and error field set."""
        provider = __import__(
            "pct.agent.providers.local_llm", fromlist=["LocalLLMProvider"]
        ).LocalLLMProvider(backend=fake_llama_failing)
        result = await execute_chat_turn(provider, sample_context)
        assert result.outcome == TaskOutcome.ERROR
        assert result.error is not None

    async def test_no_callback_still_works(self, local_provider, sample_context):
        """on_token=None completes without error."""
        result = await execute_chat_turn(local_provider, sample_context, on_token=None)
        assert isinstance(result, AgentResult)
        assert len(result.output) > 0

    async def test_messages_recorded_in_result(self, local_provider, sample_context):
        """result.messages is populated with the conversation."""
        result = await execute_chat_turn(local_provider, sample_context)
        assert len(result.messages) > 0
