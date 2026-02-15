"""Factory to create a fully-populated ToolRegistry for agent use."""

from __future__ import annotations

from pathlib import Path

from pct.agent.tools._base import ToolRegistry
from pct.agent.tools.bash import BashTool
from pct.agent.tools.file_tools import FileEditTool, FileReadTool, FileWriteTool
from pct.agent.tools.rag_tools import RAGSearchTool
from pct.agent.tools.todo_tools import TodoCreateTool, TodoEditTool, TodoReadTool
from pct.agent.tools.web_tools import WebFetchTool, WebSearchTool


def create_global_registry(project_root: Path, project_id: str) -> ToolRegistry:
    """Instantiate and register all agent tools into a single registry."""
    registry = ToolRegistry()

    # Shell
    registry.register(BashTool())

    # File operations
    registry.register(FileReadTool(root_dir=project_root))
    registry.register(FileWriteTool(root_dir=project_root))
    registry.register(FileEditTool(root_dir=project_root))

    # Web
    registry.register(WebSearchTool())
    registry.register(WebFetchTool())

    # Todo / task management
    registry.register(TodoReadTool(root_dir=project_root))
    registry.register(TodoCreateTool(root_dir=project_root))
    registry.register(TodoEditTool(root_dir=project_root))

    # RAG semantic search
    registry.register(RAGSearchTool(project_id=project_id))

    return registry
