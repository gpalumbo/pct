"""Scan the model registry and update image-gen architecture metadata.

Reads each ModelRegistryEntry whose file_path points to a directory
containing model_index.json, detects the diffusers pipeline class and
native resolution, and writes the results back to the registry so the
frontend can show a stable "Detected: …" badge without re-scanning the
filesystem on every API request.
"""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from pct.imagegen.service import detect_architecture, detect_native_resolution
from pct.storage.registry_io import load_model_registry, save_model_registry


def rescan_imagegen_metadata(global_dir: Path) -> int:
    """Refresh `architecture` and `native_resolution` on every registry entry.

    Returns the number of entries whose metadata changed.
    """
    models = load_model_registry(global_dir)
    changed = 0

    for i, entry in enumerate(models):
        new_arch: str | None = None
        new_native: int | None = None

        if entry.file_path:
            mp = Path(entry.file_path)
            index_file = mp / "model_index.json" if mp.is_dir() else None
            if index_file is not None and index_file.exists():
                try:
                    idx = json.loads(index_file.read_text(encoding="utf-8"))
                    cls_name = idx.get("_class_name", "")
                    new_arch = detect_architecture(cls_name)
                except Exception as e:
                    logger.debug(
                        "Could not parse {} for {}: {}",
                        index_file, entry.id, e,
                    )
                try:
                    new_native = detect_native_resolution(str(mp))
                except Exception as e:
                    logger.debug(
                        "Could not detect native resolution for {}: {}",
                        entry.id, e,
                    )

        if entry.architecture != new_arch or entry.native_resolution != new_native:
            models[i] = entry.model_copy(
                update={
                    "architecture": new_arch,
                    "native_resolution": new_native,
                }
            )
            changed += 1

    if changed:
        save_model_registry(global_dir, models)

    return changed
