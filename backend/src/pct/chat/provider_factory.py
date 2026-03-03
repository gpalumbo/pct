"""Bridge AgentConfig to AgentProvider for chat execution."""

from __future__ import annotations

import logging

from pct.agent.models import AgentConfig
from pct.agent.protocols import AgentProvider
from pct.agent.providers.claude_code import ClaudeCodeProvider
from pct.agent.providers.local_llm import LocalLLMProvider
from pct.models.enums import ProviderType

logger = logging.getLogger(__name__)


def resolve_provider(agent_id: str) -> tuple[AgentProvider, AgentConfig]:
    """Look up an AgentConfig and create the appropriate provider.

    Returns ``(provider, agent_config)`` so callers can access config fields
    like ``prompt_template``.

    Uses prototype2's storage layer to load agent configs from pct.yaml.
    """
    from pct.storage.project_io import load_project_config

    from pct import config

    project = load_project_config(config.settings.project_root)
    if project is None:
        raise ValueError("No project config found")

    # Find agent in project config
    agent_data = None
    for agent in getattr(project, "agents", []):
        if getattr(agent, "id", None) == agent_id:
            agent_data = agent
            break

    if agent_data is None:
        raise ValueError(f"Agent not found: {agent_id}")

    # Map project Agent model to AgentConfig
    from pct.models.enums import AgentType

    agent_cfg = AgentConfig(
        id=agent_data.id,
        agent_type=getattr(agent_data, "agent_type", AgentType.llm),
        provider_type=getattr(agent_data, "provider_type", ProviderType.local),
        model=getattr(agent_data, "model", ""),
        prompt_template=getattr(agent_data, "prompt_template", None),
        context_length=getattr(agent_data, "context_length", None),
        temperature=getattr(agent_data, "temperature", None),
    )

    if agent_cfg.provider_type in (ProviderType.local, ProviderType.huggingface):
        # Attempt to resolve model path from global registry
        model_path = _resolve_model_path(agent_cfg.model)
        if model_path is None:
            raise ValueError(
                f"Model '{agent_cfg.model}' not found in registry "
                f"(referenced by agent '{agent_id}')"
            )
        return LocalLLMProvider(
            model_path=model_path,
            context_length=agent_cfg.context_length,
            temperature=agent_cfg.temperature,
        ), agent_cfg

    if agent_cfg.provider_type == ProviderType.remote_api:
        return ClaudeCodeProvider(), agent_cfg

    raise ValueError(f"Unsupported provider type: {agent_cfg.provider_type}")


def _resolve_model_path(model_id: str) -> str | None:
    """Look up model_path from global registries or project config."""
    try:
        from pct.storage.registry_io import load_global_models

        models = load_global_models()
        for m in models:
            if getattr(m, "id", None) == model_id:
                return getattr(m, "model_path", None)
    except (ImportError, Exception):
        pass
    return None


def get_default_planning_agent_id() -> str | None:
    """Return the configured planning agent, or first agent if none set."""
    try:
        from pct.storage.project_io import load_project_config

        from pct import config

        project = load_project_config(config.settings.project_root)
        if project is None:
            return None

        if getattr(project, "planning_agent_id", None):
            return project.planning_agent_id

        agents = getattr(project, "agents", [])
        if agents:
            return agents[0].id
    except Exception:
        pass
    return None
