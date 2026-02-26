"""Optional import wrapper for llama_cpp.

Provides a clear error message when llama-cpp-python is not installed.
"""

from __future__ import annotations

try:
    from llama_cpp import Llama  # type: ignore[import-untyped]
except ImportError:
    Llama = None  # type: ignore[assignment,misc]

LLAMA_AVAILABLE = Llama is not None


def require_llama() -> type:
    """Return the Llama class or raise a helpful ImportError."""
    if Llama is None:
        raise ImportError("llama-cpp-python is not installed. Install it with: pip install 'pct[local-llm]'")
    return Llama
