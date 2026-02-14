"""Bridge AgentConfig to AgentProvider for chat execution."""

from __future__ import annotations

import logging

from pct.agent.models import AgentConfig, ProviderType
from pct.agent.protocols import AgentProvider
from pct.agent.providers.local_llm import LocalLLMProvider
from pct.agent.providers.claude_code import ClaudeCodeProvider
from pct.settings import service as settings_service

logger = logging.getLogger(__name__)


def resolve_provider(agent_id: str) -> AgentProvider:
    """Look up an AgentConfig and create the appropriate provider."""
    agent_cfg = settings_service.get_agent(agent_id)
    if agent_cfg is None:
        raise ValueError(f"Agent not found: {agent_id}")

    if agent_cfg.provider_type == ProviderType.LOCAL_LLM:
        model_entry = settings_service.get_model(agent_cfg.model)
        if model_entry is None:
            raise ValueError(
                f"Model '{agent_cfg.model}' not found in registry "
                f"(referenced by agent '{agent_id}')"
            )
        return LocalLLMProvider(
            model_path=model_entry.model_path,
            context_length=agent_cfg.context_length or model_entry.context_length,
        )

    if agent_cfg.provider_type == ProviderType.REMOTE_API:
        return ClaudeCodeProvider()

    raise ValueError(f"Unsupported provider type: {agent_cfg.provider_type}")


def get_default_planning_agent_id() -> str | None:
    """Return the configured planning agent, or first agent if none set."""
    cfg = settings_service.get_project_config()
    if cfg and cfg.planning_agent:
        return cfg.planning_agent
    agents = settings_service.list_agents()
    if agents:
        return agents[0].id
    return None
