"""Quick smoke test: local LLM + tool loop.

Usage:
    # 1. Download a model (once):
    #    pip install huggingface-hub
    #    huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \
    #      qwen2.5-7b-instruct-q4_k_m.gguf --local-dir ./models
    #
    # 2. Install llama-cpp-python with CUDA:
    #    CMAKE_ARGS="-DGGML_CUDA=on" pip install 'pct[local-llm]'
    #
    # 3. Run this script:
    #    python scripts/test_local_chat.py
    #    python scripts/test_local_chat.py --model ./models/some-other-model.gguf
    #    python scripts/test_local_chat.py --tools   # enable bash tool

"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure the backend package is importable when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pct.agent.chat_loop import execute_chat_turn
from pct.agent.models import AssembledContext
from pct.agent.providers.local_llm import LocalLLMProvider
from pct.agent.tools import BashTool, ToolRegistry

DEFAULT_MODEL = "./models/qwen2.5-7b-instruct-q4_k_m.gguf"


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(BashTool(timeout=10.0))
    return registry


async def run(model_path: str, prompt: str, use_tools: bool) -> None:
    print(f"Loading model: {model_path}")
    provider = LocalLLMProvider(
        model_path=model_path,
        context_length=8192,
        n_gpu_layers=-1,
    )

    registry = build_registry() if use_tools else None
    mode = "with tools (bash)" if use_tools else "no tools"
    print(f"Mode: {mode}")
    print(f"Prompt: {prompt}")
    print("-" * 60)

    context = AssembledContext(base=prompt)

    async def on_token(token: str) -> None:
        print(token, end="", flush=True)

    # Stream tokens when no tools; tools force non-streaming internally
    callback = on_token if not use_tools else None

    result = await execute_chat_turn(
        provider,
        context,
        system_prompt="You are a helpful assistant. When asked to run commands, use the bash tool.",
        on_token=callback,
        tool_registry=registry,
        timeout_seconds=120,
    )

    # If tools were used, output wasn't streamed — print it now
    if use_tools and result.output:
        print(result.output)

    print()
    print("-" * 60)
    print(f"Outcome: {result.outcome}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print(f"Tokens in/out: {result.tokens_input}/{result.tokens_output}")

    if result.tool_calls:
        print(f"Tool calls made: {len(result.tool_calls)}")
        for tc in result.tool_calls:
            print(f"  - {tc.function_name}({tc.arguments})")

    if result.error:
        print(f"Error: {result.error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test local LLM with optional tool loop")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Path to GGUF model file (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="Enable the bash tool for the LLM to use",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Prompt to send (default: depends on --tools flag)",
    )
    args = parser.parse_args()

    if args.prompt is None:
        if args.tools:
            args.prompt = "What operating system is this machine running? Use the bash tool to find out."
        else:
            args.prompt = "Explain what a linked list is in two sentences."

    if not Path(args.model).exists():
        print(f"Model not found: {args.model}")
        print()
        print("Download one with:")
        print("  huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \\")
        print("    qwen2.5-7b-instruct-q4_k_m.gguf --local-dir ./models")
        sys.exit(1)
    asyncio.run(run(args.model, args.prompt, args.tools))


if __name__ == "__main__":
    main()
