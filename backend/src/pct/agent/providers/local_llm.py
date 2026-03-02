"""LocalLLMProvider — llama-cpp-python based local inference."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pct.agent.models import AgentResult, TaskOutcome


class LocalLLMProvider:
    """Provider for local LLM models via llama-cpp-python."""

    def __init__(self, model_path: str, context_length: int = 4096, temperature: float = 0.7):
        self.model_path = model_path
        self.context_length = context_length
        self.temperature = temperature
        self._llm = None
        self._interrupted = False

    def _ensure_model(self):
        """Lazy load the model."""
        if self._llm is not None:
            return
        try:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.context_length,
                verbose=False,
            )
        except ImportError:
            msg = "llama-cpp-python is not installed. Install with: pip install llama-cpp-python"
            raise RuntimeError(msg) from None

    def _run_inference(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        """Synchronous inference — runs in thread."""
        self._ensure_model()
        start = time.time()
        self._interrupted = False

        result = self._llm.create_chat_completion(
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
        )

        output = result["choices"][0]["message"]["content"] or ""
        duration = time.time() - start

        return AgentResult(
            outcome=TaskOutcome.success,
            output=output,
            messages=messages + [{"role": "assistant", "content": output}],
            tokens_input=result.get("usage", {}).get("prompt_tokens", 0),
            tokens_output=result.get("usage", {}).get("completion_tokens", 0),
            duration_seconds=duration,
        )

    async def execute(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AgentResult:
        """Run inference in a thread to avoid blocking the event loop."""
        try:
            return await asyncio.to_thread(self._run_inference, messages, tools)
        except Exception as e:
            return AgentResult(
                outcome=TaskOutcome.failure,
                error=str(e),
            )

    async def interrupt(self) -> None:
        self._interrupted = True
