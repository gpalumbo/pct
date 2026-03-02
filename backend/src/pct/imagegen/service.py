"""Image gen service — HuggingFace Diffusers pipeline.

Lazy-loads the diffusion pipeline on first use. Generation runs in
asyncio.to_thread to avoid blocking the event loop. Images are saved
to work/{feature_id}/{task_id}/images/.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from pct.models.imagegen import GeneratedImage, ImageRound, ImageSession
from pct.storage.directory_manager import create_task_work_dir

logger = logging.getLogger(__name__)

# Lazy singleton for the diffusion pipeline
_pipeline: Any = None
_pipeline_lock = asyncio.Lock()


async def _get_pipeline() -> Any:
    """Lazy-load the HuggingFace Diffusers pipeline.

    Returns None if diffusers is not installed or the model cannot be loaded.
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    async with _pipeline_lock:
        # Double-check after acquiring lock
        if _pipeline is not None:
            return _pipeline

        try:

            def _load():
                from diffusers import StableDiffusionPipeline

                pipe = StableDiffusionPipeline.from_pretrained(
                    "runwayml/stable-diffusion-v1-5",
                )
                return pipe

            _pipeline = await asyncio.to_thread(_load)
            logger.info("Loaded diffusion pipeline")
            return _pipeline
        except ImportError:
            logger.warning(
                "diffusers not installed — image generation unavailable"
            )
            return None
        except Exception as e:
            logger.error("Failed to load diffusion pipeline: %s", e)
            return None


def _sync_generate(
    pipeline: Any,
    prompt: str,
    negative_prompt: str | None,
    guidance_scale: float,
    num_images: int = 4,
    seed: int | None = None,
) -> list[tuple[Any, int]]:
    """Synchronous generation call. Returns list of (PIL.Image, seed) tuples."""
    import torch

    results: list[tuple[Any, int]] = []

    for i in range(num_images):
        img_seed = (seed or torch.randint(0, 2**32, (1,)).item()) + i
        generator = torch.Generator().manual_seed(img_seed)

        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "guidance_scale": guidance_scale,
            "generator": generator,
            "num_inference_steps": 30,
        }
        if negative_prompt:
            kwargs["negative_prompt"] = negative_prompt

        output = pipeline(**kwargs)
        image = output.images[0]
        results.append((image, img_seed))

    return results


async def generate(
    project_root: Path,
    feature_id: str,
    task_id: str,
    prompt: str,
    negative_prompt: str | None = None,
    guidance_scale: float = 7.5,
    num_images: int = 4,
    seed: int | None = None,
) -> ImageRound | None:
    """Generate images for a task.

    Saves images to work/{feature_id}/{task_id}/images/ and returns
    an ImageRound describing the generated images.

    Returns None if the pipeline is unavailable.
    """
    pipeline = await _get_pipeline()
    if pipeline is None:
        logger.warning(
            "Image generation skipped — pipeline unavailable for %s/%s",
            feature_id,
            task_id,
        )
        return None

    # Ensure output directory exists
    task_dir = create_task_work_dir(project_root, feature_id, task_id)
    images_dir = task_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # Run generation in a thread
    image_results = await asyncio.to_thread(
        _sync_generate,
        pipeline,
        prompt,
        negative_prompt,
        guidance_scale,
        num_images,
        seed,
    )

    # Save images and build response
    generated: list[GeneratedImage] = []
    for idx, (pil_image, img_seed) in enumerate(image_results):
        image_id = str(uuid.uuid4())[:8]
        filename = f"{image_id}.png"
        file_path = images_dir / filename

        await asyncio.to_thread(pil_image.save, str(file_path))

        generated.append(
            GeneratedImage(
                id=image_id,
                file_path=str(file_path.relative_to(project_root)),
                seed=img_seed,
                index=idx,
            )
        )

    # Count existing rounds to determine round number
    round_number = 1  # Default for first round

    image_round = ImageRound(
        round_number=round_number,
        prompt=prompt,
        negative_prompt=negative_prompt,
        guidance_scale=guidance_scale,
        images=generated,
    )

    logger.info(
        "Generated %d images for %s/%s", len(generated), feature_id, task_id
    )
    return image_round


def get_session(
    project_root: Path,
    feature_id: str,
    task_id: str,
) -> ImageSession:
    """Get or create the image session for a task.

    Returns an ImageSession. Currently returns an empty session since
    session persistence is not yet implemented (future: stored in
    task metadata or separate YAML).
    """
    return ImageSession(task_id=task_id)


def select_image(
    project_root: Path,
    feature_id: str,
    task_id: str,
    image_id: str,
) -> bool:
    """Mark an image as the accepted output for a task.

    Returns True on success. Currently a stub that logs the selection.
    Full persistence will be added when image sessions are stored.
    """
    logger.info(
        "Selected image %s for task %s/%s", image_id, feature_id, task_id
    )
    return True
