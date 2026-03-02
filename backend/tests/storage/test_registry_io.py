"""Tests for registry I/O."""

from pathlib import Path

from pct.models.agents import LoRARegistryEntry, LoRAVersion, ModelRegistryEntry
from pct.models.enums import ProviderType
from pct.storage.registry_io import (
    load_lora_registry,
    load_model_registry,
    save_lora_registry,
    save_model_registry,
)


class TestModelRegistryIO:
    def test_load_nonexistent(self, tmp_path: Path):
        assert load_model_registry(tmp_path) == []

    def test_save_and_load_round_trip(self, tmp_path: Path):
        models = [
            ModelRegistryEntry(
                id="user-model",
                name="User",
                provider_type=ProviderType.user,
                model_identifier="user",
            ),
            ModelRegistryEntry(
                id="llama3",
                name="Llama 3",
                provider_type=ProviderType.local,
                model_identifier="llama3.gguf",
                context_length=8192,
                file_path="/models/llama3.gguf",
            ),
        ]
        save_model_registry(tmp_path, models)
        loaded = load_model_registry(tmp_path)
        assert len(loaded) == 2
        assert loaded[0].id == "user-model"
        assert loaded[1].context_length == 8192

    def test_creates_dirs(self, tmp_path: Path):
        models = [
            ModelRegistryEntry(id="m", name="M", provider_type=ProviderType.local, model_identifier="m")
        ]
        save_model_registry(tmp_path, models)
        assert (tmp_path / "registries" / "models.yaml").exists()


class TestLoRARegistryIO:
    def test_load_nonexistent(self, tmp_path: Path):
        assert load_lora_registry(tmp_path) == []

    def test_save_and_load_round_trip(self, tmp_path: Path):
        loras = [
            LoRARegistryEntry(
                id="code-style",
                name="Code Style",
                base_model_id="llama3",
                description="Fine-tuned for code",
                versions=[LoRAVersion(version=1, file_path="/loras/v1.safetensors")],
                active_version=1,
            ),
        ]
        save_lora_registry(tmp_path, loras)
        loaded = load_lora_registry(tmp_path)
        assert len(loaded) == 1
        assert loaded[0].id == "code-style"
        assert loaded[0].base_model_id == "llama3"
        assert len(loaded[0].versions) == 1
