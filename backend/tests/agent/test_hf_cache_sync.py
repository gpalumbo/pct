"""Tests for HuggingFace cache detection and download status sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pct.agent.model_downloader import (
    check_hf_cache,
    ensure_model_ready,
    sync_hf_download_status,
)
from pct.models.agents import ModelRegistryEntry
from pct.models.enums import DownloadStatus, ProviderType
from pct.storage.registry_io import load_model_registry, save_model_registry

_SENTINEL = object()  # huggingface_hub uses _CACHED_NO_EXIST sentinel


def _make_entry(
    *,
    id: str = "test-model",
    name: str = "Test Model",
    provider_type: ProviderType = ProviderType.huggingface,
    model_identifier: str = "stabilityai/stable-diffusion-xl-base-1.0",
    file_path: str | None = None,
    gguf_filename: str | None = None,
    download_status: DownloadStatus | None = None,
) -> ModelRegistryEntry:
    return ModelRegistryEntry(
        id=id,
        name=name,
        provider_type=provider_type,
        model_identifier=model_identifier,
        file_path=file_path,
        gguf_filename=gguf_filename,
        download_status=download_status,
    )


# ── check_hf_cache ─────────────────────────────────────────────


class TestCheckHfCache:
    def test_non_hf_returns_none(self):
        entry = _make_entry(provider_type=ProviderType.remote_api)
        assert check_hf_cache(entry) is None

    def test_no_model_identifier_returns_none(self):
        entry = _make_entry(model_identifier="")
        assert check_hf_cache(entry) is None

    @patch("pct.agent.model_downloader.try_to_load_from_cache")
    def test_gguf_found(self, mock_cache):
        mock_cache.return_value = "/home/user/.cache/hf/models/model.gguf"
        entry = _make_entry(
            model_identifier="TheBloke/Mistral-7B-GGUF",
            gguf_filename="mistral-7b-q4.gguf",
        )
        result = check_hf_cache(entry)
        assert result == "/home/user/.cache/hf/models/model.gguf"
        mock_cache.assert_called_once_with("TheBloke/Mistral-7B-GGUF", "mistral-7b-q4.gguf")

    @patch("pct.agent.model_downloader.try_to_load_from_cache")
    def test_gguf_not_found(self, mock_cache):
        mock_cache.return_value = _SENTINEL  # not a str
        entry = _make_entry(
            model_identifier="TheBloke/Mistral-7B-GGUF",
            gguf_filename="mistral-7b-q4.gguf",
        )
        assert check_hf_cache(entry) is None

    @patch("pct.agent.model_downloader.try_to_load_from_cache")
    def test_diffusers_model_index_found(self, mock_cache, tmp_path):
        sentinel_file = tmp_path / "model_index.json"
        sentinel_file.write_text("{}")
        mock_cache.return_value = str(sentinel_file)
        entry = _make_entry()
        result = check_hf_cache(entry)
        assert result == str(tmp_path)
        mock_cache.assert_called_once_with(
            "stabilityai/stable-diffusion-xl-base-1.0", "model_index.json"
        )

    @patch("pct.agent.model_downloader.try_to_load_from_cache")
    def test_diffusers_config_json_fallback(self, mock_cache, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        def side_effect(repo_id, filename):
            if filename == "model_index.json":
                return _SENTINEL
            return str(config_file)

        mock_cache.side_effect = side_effect
        entry = _make_entry()
        result = check_hf_cache(entry)
        assert result == str(tmp_path)

    @patch("pct.agent.model_downloader.try_to_load_from_cache")
    def test_not_in_cache(self, mock_cache):
        mock_cache.return_value = _SENTINEL
        entry = _make_entry()
        assert check_hf_cache(entry) is None

    def test_no_huggingface_hub_returns_none(self):
        with patch("pct.agent.model_downloader.try_to_load_from_cache", None):
            entry = _make_entry()
            assert check_hf_cache(entry) is None


# ── sync_hf_download_status ─────────────────────────────────────


class TestSyncHfDownloadStatus:
    def _setup_registry(self, tmp_path: Path, entries: list[ModelRegistryEntry]):
        global_dir = tmp_path / ".pct"
        global_dir.mkdir(exist_ok=True)
        (global_dir / "registries").mkdir(exist_ok=True)
        save_model_registry(global_dir, entries)
        return global_dir

    @patch("pct.agent.model_downloader.check_hf_cache")
    def test_updates_found_in_cache(self, mock_check, tmp_path):
        entry = _make_entry(download_status=None)
        global_dir = self._setup_registry(tmp_path, [entry])
        mock_check.return_value = "/cache/sdxl"

        result = sync_hf_download_status(global_dir)

        assert len(result) == 1
        assert result[0].file_path == "/cache/sdxl"
        assert result[0].download_status == DownloadStatus.ready

        # Verify persisted
        persisted = load_model_registry(global_dir)
        assert persisted[0].download_status == DownloadStatus.ready

    @patch("pct.agent.model_downloader.check_hf_cache")
    def test_no_op_when_file_path_valid(self, mock_check, tmp_path):
        model_file = tmp_path / "model_index.json"
        model_file.write_text("{}")
        entry = _make_entry(
            file_path=str(model_file),
            download_status=DownloadStatus.ready,
        )
        global_dir = self._setup_registry(tmp_path, [entry])

        result = sync_hf_download_status(global_dir)

        assert result[0].download_status == DownloadStatus.ready
        assert result[0].file_path == str(model_file)
        mock_check.assert_not_called()

    @patch("pct.agent.model_downloader.check_hf_cache")
    def test_fixes_status_when_file_exists_but_status_wrong(self, mock_check, tmp_path):
        model_file = tmp_path / "model_index.json"
        model_file.write_text("{}")
        entry = _make_entry(
            file_path=str(model_file),
            download_status=None,  # should be ready
        )
        global_dir = self._setup_registry(tmp_path, [entry])

        result = sync_hf_download_status(global_dir)

        assert result[0].download_status == DownloadStatus.ready
        mock_check.assert_not_called()

    @patch("pct.agent.model_downloader.check_hf_cache")
    def test_reverts_missing_to_pending(self, mock_check, tmp_path):
        entry = _make_entry(
            file_path="/nonexistent/model",
            download_status=DownloadStatus.ready,
        )
        global_dir = self._setup_registry(tmp_path, [entry])
        mock_check.return_value = None

        result = sync_hf_download_status(global_dir)

        assert result[0].download_status == DownloadStatus.pending

    @patch("pct.agent.model_downloader.check_hf_cache")
    def test_skips_non_hf_entries(self, mock_check, tmp_path):
        entry = _make_entry(provider_type=ProviderType.remote_api, id="remote-model")
        global_dir = self._setup_registry(tmp_path, [entry])

        result = sync_hf_download_status(global_dir)

        assert result[0].download_status is None
        mock_check.assert_not_called()

    @patch("pct.agent.model_downloader.check_hf_cache")
    def test_no_save_when_unchanged(self, mock_check, tmp_path):
        entry = _make_entry(
            download_status=None,  # not ready, no file_path
        )
        global_dir = self._setup_registry(tmp_path, [entry])
        mock_check.return_value = None

        with patch("pct.agent.model_downloader.save_model_registry") as mock_save:
            sync_hf_download_status(global_dir)
            mock_save.assert_not_called()


# ── ensure_model_ready cache fallback ────────────────────────────


class TestEnsureModelReadyCacheFallback:
    def _setup_registry(self, tmp_path: Path, entry: ModelRegistryEntry):
        from pct.config import Settings, set_settings

        global_dir = tmp_path / ".pct"
        global_dir.mkdir(exist_ok=True)
        (global_dir / "registries").mkdir(exist_ok=True)
        save_model_registry(global_dir, [entry])
        set_settings(Settings(project_root=tmp_path, global_config_dir=global_dir))
        return global_dir

    @pytest.mark.asyncio
    @patch("pct.agent.model_downloader.check_hf_cache")
    async def test_skips_download_when_cache_hit(self, mock_check, tmp_path):
        entry = _make_entry(download_status=None)
        self._setup_registry(tmp_path, entry)
        mock_check.return_value = "/cache/sdxl"
        on_status = AsyncMock()

        result = await ensure_model_ready(entry, on_status, require_gguf=False)

        assert result.file_path == "/cache/sdxl"
        assert result.download_status == DownloadStatus.ready
        on_status.assert_not_called()

    @pytest.mark.asyncio
    @patch("pct.agent.model_downloader.check_hf_cache")
    async def test_proceeds_to_download_when_no_cache(self, mock_check, tmp_path):
        entry = _make_entry(download_status=None)
        self._setup_registry(tmp_path, entry)
        mock_check.return_value = None
        on_status = AsyncMock()

        with patch("huggingface_hub.list_repo_files", side_effect=Exception("test abort")):
            with pytest.raises(ValueError, match="Failed to download"):
                await ensure_model_ready(entry, on_status, require_gguf=False)
