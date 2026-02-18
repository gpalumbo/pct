"""Tests for pct.agent.providers.local_llm — LocalLLMProvider with FakeLlama."""

import json

import pytest

from pct.agent.models import AgentResult, TaskOutcome
from pct.agent.providers.local_llm import LocalLLMProvider, _parse_tool_calls_from_content

from tests.agent.conftest import FakeLlama


class TestNonStreaming:
    async def test_non_streaming_completion(self, local_provider):
        """Full response is returned in result.output."""
        messages = [{"role": "user", "content": "Hi"}]
        result = await local_provider.execute(messages)
        assert isinstance(result, AgentResult)
        assert result.output == "Test response."

    async def test_backend_receives_correct_messages(self, fake_llama):
        """FakeLlama records the messages it received."""
        provider = LocalLLMProvider(backend=fake_llama)
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Explain X."},
        ]
        await provider.execute(messages)
        assert fake_llama.last_messages == messages

    async def test_multiple_responses_cycle(self):
        """FakeLlama cycles through its response list."""
        llama = FakeLlama(responses=["First", "Second", "Third"])
        provider = LocalLLMProvider(backend=llama)
        messages = [{"role": "user", "content": "Go"}]

        r1 = await provider.execute(messages)
        r2 = await provider.execute(messages)
        r3 = await provider.execute(messages)
        r4 = await provider.execute(messages)

        assert r1.output == "First"
        assert r2.output == "Second"
        assert r3.output == "Third"
        assert r4.output == "First"  # cycles back


class TestStreaming:
    async def test_streaming_completion(self, fake_llama_streaming):
        """Tokens are streamed via the on_token callback."""
        provider = LocalLLMProvider(backend=fake_llama_streaming)
        messages = [{"role": "user", "content": "Hello"}]
        tokens: list[str] = []

        async def collect(token: str) -> None:
            tokens.append(token)

        result = await provider.execute(messages, on_token=collect)
        assert len(tokens) > 0
        assert "".join(tokens) == "Hello from the local LLM!"
        assert result.output == "Hello from the local LLM!"


class TestErrorHandling:
    async def test_interrupt_stops_generation(self):
        """Interrupting during streaming yields partial output and INTERRUPTED outcome."""
        # Use a longer response so we can interrupt mid-stream
        llama = FakeLlama(
            responses=["A" * 100],
            stream_chunk_size=1,
        )
        provider = LocalLLMProvider(backend=llama)
        messages = [{"role": "user", "content": "Generate"}]
        tokens: list[str] = []
        call_count = 0

        async def collect_and_interrupt(token: str) -> None:
            nonlocal call_count
            tokens.append(token)
            call_count += 1
            if call_count >= 5:
                await provider.interrupt()

        result = await provider.execute(messages, on_token=collect_and_interrupt)
        assert result.outcome == TaskOutcome.INTERRUPTED
        assert len(result.output) < 100  # didn't finish

    def test_missing_llama_dependency(self):
        """Constructing without backend or model_path raises ValueError."""
        with pytest.raises(ValueError, match="Either backend or model_path"):
            LocalLLMProvider()

    async def test_backend_error_propagation(self, fake_llama_failing):
        """Backend failure (fail_after=0) results in ERROR outcome."""
        provider = LocalLLMProvider(backend=fake_llama_failing)
        messages = [{"role": "user", "content": "Hi"}]
        result = await provider.execute(messages)
        assert result.outcome == TaskOutcome.ERROR
        assert result.error is not None
        assert "Backend failure" in result.error


class TestToolCallContentFallback:
    """Tests for parsing tool calls from content when tool_calls field is empty."""

    def test_parse_bare_json_tool_call(self):
        content = json.dumps({"name": "bash", "arguments": {"command": "ls"}})
        calls = _parse_tool_calls_from_content(content)
        assert len(calls) == 1
        assert calls[0].function_name == "bash"
        assert json.loads(calls[0].arguments) == {"command": "ls"}

    def test_parse_tool_call_tag(self):
        content = '<tool_call>\n{{"name": "bash", "arguments": {"command": "pwd"}}}\n</tool_call>'
        calls = _parse_tool_calls_from_content(content)
        assert len(calls) == 1
        assert calls[0].function_name == "bash"
        assert json.loads(calls[0].arguments) == {"command": "pwd"}

    def test_parse_tool_call_tag_mismatched_braces(self):
        """LLM emits double-open but single-close brace: {{"name": ...}"""
        content = '<tool_call>\n{{"name": "read", "arguments": {"source": "https://wiki.factorio.com/Console#Kill_all_enemies"}}\n</tool_call>'
        calls = _parse_tool_calls_from_content(content)
        assert len(calls) == 1
        assert calls[0].function_name == "read"

    def test_parse_multiple_tool_call_tags(self):
        content = (
            '<tool_call>{"name": "bash", "arguments": {"command": "ls"}}</tool_call>\n'
            '<tool_call>{"name": "bash", "arguments": {"command": "pwd"}}</tool_call>'
        )
        calls = _parse_tool_calls_from_content(content)
        assert len(calls) == 2

    def test_parse_with_parameters_key(self):
        """Some models use 'parameters' instead of 'arguments'."""
        content = json.dumps({"name": "bash", "parameters": {"command": "ls"}})
        calls = _parse_tool_calls_from_content(content)
        assert len(calls) == 1
        assert json.loads(calls[0].arguments) == {"command": "ls"}

    def test_parse_returns_empty_for_plain_text(self):
        calls = _parse_tool_calls_from_content("Just a normal text response.")
        assert calls == []

    def test_parse_returns_empty_for_empty_string(self):
        calls = _parse_tool_calls_from_content("")
        assert calls == []

    def test_parse_ignores_json_without_name(self):
        content = json.dumps({"foo": "bar"})
        calls = _parse_tool_calls_from_content(content)
        assert calls == []

    async def test_provider_fallback_populates_tool_calls(self):
        """When backend puts tool call in content, provider still populates tool_calls."""
        tool_call_json = json.dumps(
            {"name": "bash", "arguments": {"command": "echo hi"}}
        )
        llama = FakeLlama(responses=[tool_call_json])
        provider = LocalLLMProvider(backend=llama)
        messages = [{"role": "user", "content": "run echo"}]
        result = await provider.execute(messages, tools=[{"type": "function", "function": {"name": "bash"}}])
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].function_name == "bash"
        assert result.output == ""  # content cleared since it was a tool call

    async def test_structured_tool_calls_take_precedence(self):
        """When backend returns structured tool_calls, content fallback is skipped."""
        llama = FakeLlama(
            tool_call_responses={
                0: [
                    {
                        "id": "call_abc",
                        "function": {
                            "name": "bash",
                            "arguments": '{"command": "ls"}',
                        },
                    }
                ]
            }
        )
        provider = LocalLLMProvider(backend=llama)
        messages = [{"role": "user", "content": "list files"}]
        result = await provider.execute(messages, tools=[{"type": "function", "function": {"name": "bash"}}])
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "call_abc"
