"""Registry I/O — global model and LoRA registries at ~/.pct/registries/."""

from pathlib import Path

import yaml

from pct.models.agents import LoRARegistryEntry, ModelRegistryEntry
from pct.storage._atomic import atomic_write
from pct.storage.directory_manager import ensure_global_config_dir


def _registries_dir(global_dir: Path) -> Path:
    return global_dir / "registries"


def load_model_registry(global_dir: Path) -> list[ModelRegistryEntry]:
    """Load model registry from ~/.pct/registries/models.yaml."""
    path = _registries_dir(global_dir) / "models.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [ModelRegistryEntry(**entry) for entry in data]


def save_model_registry(global_dir: Path, models: list[ModelRegistryEntry]) -> None:
    """Atomically save model registry."""
    ensure_global_config_dir(global_dir)
    path = _registries_dir(global_dir) / "models.yaml"
    content = yaml.safe_dump(
        [m.model_dump(mode="json") for m in models],
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    atomic_write(path, content)


def load_lora_registry(global_dir: Path) -> list[LoRARegistryEntry]:
    """Load LoRA registry from ~/.pct/registries/loras.yaml."""
    path = _registries_dir(global_dir) / "loras.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [LoRARegistryEntry(**entry) for entry in data]


def save_lora_registry(global_dir: Path, loras: list[LoRARegistryEntry]) -> None:
    """Atomically save LoRA registry."""
    ensure_global_config_dir(global_dir)
    path = _registries_dir(global_dir) / "loras.yaml"
    content = yaml.safe_dump(
        [entry.model_dump(mode="json") for entry in loras],
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    atomic_write(path, content)
