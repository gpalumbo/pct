"""Auto-download HuggingFace models on first use."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Awaitable, Callable

from pct.models.agents import ModelRegistryEntry
from pct.models.enums import DownloadStatus, ProviderType
from loguru import logger

# Matches GGUF split shard pattern: -NNNNN-of-NNNNN.gguf
_GGUF_SHARD_RE = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)

OnStatus = Callable[[str], Awaitable[None]]


async def ensure_model_ready(
    entry: ModelRegistryEntry,
    on_status: OnStatus,
    *,
    require_gguf: bool = True,
) -> ModelRegistryEntry:
    """Check if a model file exists; if not, download from HuggingFace Hub.

    When *require_gguf* is ``True`` (the default), only GGUF files are
    downloaded and an error is raised if the repository contains none.
    Pass ``False`` to download the full repository snapshot (e.g. for
    diffusers-style image-generation models).

    Returns the (possibly updated) registry entry with resolved ``file_path``
    and ``download_status``.
    """
    # Only auto-download for HuggingFace models
    if entry.provider_type != ProviderType.huggingface:
        return entry

    # If file already exists on disk, nothing to do
    if entry.file_path and Path(entry.file_path).exists():
        return entry

    repo_id = entry.model_identifier
    if not repo_id:
        raise ValueError(
            f"Model '{entry.id}' has provider_type=huggingface but no model_identifier "
            "(HuggingFace repo ID). Set it in Settings > Models."
        )

    await on_status(f"Model files not found locally. Preparing to download {repo_id}...")

    try:
        from huggingface_hub import list_repo_files, snapshot_download
    except ImportError:
        raise ValueError(
            "huggingface-hub is not installed. "
            "Install it with: pip install huggingface-hub"
        )

    # Update registry status to downloading
    entry = _update_registry_status(entry, DownloadStatus.downloading)

    try:
        # Check what files are in the repo
        await on_status(f"Checking repository contents for {repo_id}...")
        repo_files = list_repo_files(repo_id)
        gguf_files = [f for f in repo_files if f.endswith(".gguf")]

        if gguf_files and entry.gguf_filename:
            # User selected a specific variant — download only that file (+ shards)
            allow = _gguf_allow_patterns(entry.gguf_filename)
            await on_status(
                f"Downloading selected variant '{entry.gguf_filename}' from {repo_id}..."
            )
            local_dir = snapshot_download(repo_id, allow_patterns=allow)
        elif gguf_files and require_gguf:
            raise ValueError(
                f"Repository '{repo_id}' contains {len(gguf_files)} GGUF files "
                "but no variant was selected. Please select a GGUF variant in "
                "Settings > Models before downloading."
            )
        elif gguf_files:
            # Non-GGUF-required path with GGUF files but no selection — download all
            await on_status(
                f"Found {len(gguf_files)} GGUF file(s) in {repo_id}. "
                "Downloading GGUF files only..."
            )
            local_dir = snapshot_download(repo_id, allow_patterns=["*.gguf"])
        elif require_gguf:
            raise ValueError(
                f"Repository '{repo_id}' contains no GGUF files. "
                "llama-cpp-python requires GGUF format for inference. "
                "Please choose a GGUF-quantised version of this model."
            )
        else:
            await on_status(f"No GGUF files found. Downloading full model from {repo_id}...")
            local_dir = snapshot_download(repo_id)

        # Find the actual model file path
        local_path = Path(local_dir)
        resolved_path = _find_model_file(local_path, gguf_files, entry.gguf_filename)

        await on_status(f"Download complete. Model ready at {resolved_path}")

        # Update registry with the resolved path and ready status
        entry = _update_registry_entry(entry, str(resolved_path), DownloadStatus.ready)
        return entry

    except Exception as e:
        # Revert status to pending on failure
        _update_registry_status(entry, DownloadStatus.pending)
        raise ValueError(f"Failed to download model '{repo_id}': {e}") from e


def _gguf_allow_patterns(gguf_filename: str) -> list[str]:
    """Build allow_patterns for snapshot_download based on the selected GGUF file.

    For split shards (e.g. ``model-fp16-00001-of-00002.gguf``), returns a
    wildcard pattern that matches all shards.  For single files, returns
    ``[gguf_filename]``.
    """
    match = _GGUF_SHARD_RE.search(gguf_filename)
    if match:
        base = gguf_filename[: match.start()]
        return [f"{base}-*-of-*.gguf"]
    return [gguf_filename]


def _find_model_file(
    local_dir: Path,
    gguf_files: list[str],
    gguf_filename: str | None = None,
) -> Path:
    """Find the primary model file in the downloaded snapshot directory."""
    # Prefer the user-selected variant
    if gguf_filename:
        resolved = local_dir / gguf_filename
        if resolved.exists():
            return resolved

    if gguf_files:
        # For GGUF: prefer non-split files, otherwise take the first shard
        non_split = [f for f in gguf_files if "-00001-of-" not in f and "-of-" not in f]
        primary = non_split[0] if non_split else gguf_files[0]
        resolved = local_dir / primary
        if resolved.exists():
            return resolved

    # Fallback: look for common model file patterns
    for pattern in ["*.gguf", "*.safetensors", "*.bin", "config.json"]:
        found = list(local_dir.rglob(pattern))
        if found:
            return found[0]

    # Last resort: return the directory itself (for diffusers-style models)
    return local_dir


def _update_registry_status(
    entry: ModelRegistryEntry, status: DownloadStatus
) -> ModelRegistryEntry:
    """Update the download_status field in the global registry."""
    from pct import config
    from pct.storage.registry_io import load_model_registry, save_model_registry

    global_dir = config.settings.global_config_dir
    models = load_model_registry(global_dir)
    updated_entry = entry
    for i, m in enumerate(models):
        if m.id == entry.id:
            models[i] = m.model_copy(update={"download_status": status})
            updated_entry = models[i]
            break
    save_model_registry(global_dir, models)
    return updated_entry


def _update_registry_entry(
    entry: ModelRegistryEntry, file_path: str, status: DownloadStatus
) -> ModelRegistryEntry:
    """Update both file_path and download_status in the global registry."""
    from pct import config
    from pct.storage.registry_io import load_model_registry, save_model_registry

    global_dir = config.settings.global_config_dir
    models = load_model_registry(global_dir)
    updated_entry = entry
    for i, m in enumerate(models):
        if m.id == entry.id:
            models[i] = m.model_copy(
                update={"file_path": file_path, "download_status": status}
            )
            updated_entry = models[i]
            break
    save_model_registry(global_dir, models)
    return updated_entry
