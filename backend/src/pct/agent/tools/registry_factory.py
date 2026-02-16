"""Factory to create a fully-populated ToolRegistry for agent use."""

from __future__ import annotations

from pathlib import Path

from pct.agent.tools._base import ToolRegistry
from pct.agent.tools.bash import BashTool
from pct.agent.tools.file_tools import FileTool
from pct.agent.tools.read_tool import ReadTool
from pct.agent.tools.search_tool import SearchTool
from pct.agent.tools.todo_tool import TodoTool


def create_global_registry(project_root: Path, project_id: str) -> ToolRegistry:
    """Instantiate and register all agent tools into a single registry."""
    registry = ToolRegistry()

    registry.register(ReadTool(root_dir=project_root))
    registry.register(FileTool(root_dir=project_root))
    registry.register(SearchTool(project_id=project_id))
    registry.register(TodoTool(root_dir=project_root))
    registry.register(BashTool())

    return registry
