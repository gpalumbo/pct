"""Factory to create a fully-populated ToolRegistry for agent use."""

from __future__ import annotations

from pathlib import Path

from pct.agent.tools._base import ToolRegistry
from pct.agent.tools.bash import BashTool
from pct.agent.tools.file_tools import FileTool
from pct.agent.tools.read_tool import ReadTool
from pct.agent.tools.search_tool import SearchTool
from pct.agent.tools.todo_tool import TodoTool

_global_registry: ToolRegistry | None = None


def create_global_registry(project_root: Path, project_id: str = "") -> ToolRegistry:
    """Create or return the global tool registry (lazy singleton)."""
    global _global_registry
    if _global_registry is not None:
        return _global_registry

    registry = ToolRegistry()
    registry.register(ReadTool(root_dir=project_root))
    registry.register(FileTool(root_dir=project_root))
    registry.register(SearchTool(project_id=project_id))
    registry.register(TodoTool(root_dir=project_root))
    registry.register(BashTool())

    _global_registry = registry
    return registry


def reset_global_registry() -> None:
    """Reset the global registry (for testing)."""
    global _global_registry
    _global_registry = None
