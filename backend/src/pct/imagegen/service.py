"""Image gen service — HuggingFace Diffusers pipeline.

Lazy-loads the diffusion pipeline on first use. Generation runs in
asyncio.to_thread to avoid blocking the event loop. Images are saved
to work/{feature_id}/{task_id}/images/.

Pipeline loading is registry-driven: ``DiffusionPipeline.from_pretrained``
reads the model's ``model_index.json`` and dynamically imports only the
needed pipeline class.  An LRU-1 cache evicts the old model on switch.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from pct.models.imagegen import GeneratedImage, ImageRound, ImageSession
from pct.storage.directory_manager import create_task_work_dir

# ---------------------------------------------------------------------------
# Pipeline cache (LRU-1: one model at a time)
# ---------------------------------------------------------------------------


@dataclass
class CachedPipeline:
    """Holds a loaded text2img pipeline and its derived img2img variant."""

    model_id: str
    model_path: str
    pipeline: Any
    img2img_pipeline: Any | None = None
    architecture: str | None = None
    pipeline_class_name: str = ""
    native_resolution: int = 1024


_cached: CachedPipeline | None = None
_cache_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# Architecture detection
# ---------------------------------------------------------------------------

_ARCH_PATTERNS: dict[str, str] = {
    "StableDiffusionXL": "sdxl",
    "StableDiffusion3": "sd3",
    "StableDiffusion": "sd15",  # must come after XL/3
    "Flux": "flux",
    "QwenImage": "qwen",
    "Kandinsky": "kandinsky",
    "PixArt": "pixart",
    "Wuerstchen": "wuerstchen",
}


def detect_architecture(class_name: str) -> str | None:
    """Map a pipeline class name to an architecture family string."""
    for pattern, arch in _ARCH_PATTERNS.items():
        if pattern in class_name:
            return arch
    return None


def detect_native_resolution(model_path: str) -> int:
    """Read native resolution from model metadata.

    Looks for ``sample_size`` in ``unet/config.json`` or
    ``transformer/config.json`` and multiplies by 8 (VAE scale factor).
    Returns 1024 as fallback.
    """
    for subdir in ("unet", "transformer"):
        config_file = Path(model_path) / subdir / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    cfg = json.load(f)
                sample_size = cfg.get("sample_size")
                if sample_size is not None:
                    # sample_size can be int or list — take first element if list
                    if isinstance(sample_size, list):
                        sample_size = sample_size[0]
                    return int(sample_size) * 8
            except Exception:
                logger.debug("Could not read sample_size from {}", config_file)
    return 1024


# ---------------------------------------------------------------------------
# img2img class mapping
# ---------------------------------------------------------------------------

_IMG2IMG_CLASS_MAP: dict[str, str] = {
    "StableDiffusionXLPipeline": "StableDiffusionXLImg2ImgPipeline",
    "StableDiffusionPipeline": "StableDiffusionImg2ImgPipeline",
    "StableDiffusion3Pipeline": "StableDiffusion3Img2ImgPipeline",
}


def _get_img2img_class(text2img_class_name: str) -> type | None:
    """Resolve the img2img pipeline class for a given text2img class.

    Uses an explicit mapping dict, with a naming-convention fallback
    (insert ``Img2Img`` before ``Pipeline``).
    """
    import diffusers

    # Explicit map first
    mapped = _IMG2IMG_CLASS_MAP.get(text2img_class_name)
    if mapped:
        cls = getattr(diffusers, mapped, None)
        if cls is not None:
            return cls

    # Naming convention fallback: FooPipeline -> FooImg2ImgPipeline
    if text2img_class_name.endswith("Pipeline"):
        candidate = text2img_class_name.replace("Pipeline", "Img2ImgPipeline")
        cls = getattr(diffusers, candidate, None)
        if cls is not None:
            return cls

    return None


# ---------------------------------------------------------------------------
# Skip optional pipeline components
# ---------------------------------------------------------------------------


def _build_skip_kwargs(model_path: str) -> dict[str, None]:
    """Read model_index.json and return kwargs that disable optional components.

    Many model distributions omit weights for optional components like
    safety_checker, feature_extractor, or image_encoder.  Rather than
    letting ``from_pretrained`` fail with an OSError we proactively pass
    ``component=None`` for every component listed in the pipeline class's
    ``_optional_components``.

    Returns a dict like ``{"safety_checker": None, "feature_extractor": None}``.
    Falls back to the minimal safety-checker-only dict on any error.
    """
    fallback: dict[str, None] = {"safety_checker": None}
    try:
        import diffusers

        index_path = Path(model_path) / "model_index.json"
        if not index_path.exists():
            return fallback

        with open(index_path) as f:
            index = json.load(f)

        class_name = index.get("_class_name")
        if not class_name:
            return fallback

        pipeline_cls = getattr(diffusers, class_name, None)
        if pipeline_cls is None:
            return fallback

        optional: list[str] = getattr(pipeline_cls, "_optional_components", [])
        if not optional:
            return fallback

        return {name: None for name in optional}

    except Exception:
        logger.debug("Could not read _optional_components, using fallback")
        return fallback


# ---------------------------------------------------------------------------
# Pipeline loading
# ---------------------------------------------------------------------------


async def get_pipeline(
    model_id: str | None = None,
    model_path: str | None = None,
) -> CachedPipeline | None:
    """Load (or return cached) the diffusion pipeline for *model_path*.

    Uses ``DiffusionPipeline.from_pretrained`` which reads
    ``model_index.json`` and dynamically imports the correct pipeline class.

    Evicts the old pipeline when a different *model_id* is requested.
    Returns ``None`` if diffusers is not installed or loading fails.
    """
    global _cached

    if model_path is None:
        # No model specified — return whatever is cached, or None
        return _cached

    # Resolve file paths to the directory containing model_index.json
    # (guards against registry entries that point to a specific .safetensors)
    mp = Path(model_path)
    if mp.is_file():
        for parent in (mp.parent, *mp.parents):
            if (parent / "model_index.json").exists():
                model_path = str(parent)
                break

    # Fast path: already loaded
    if _cached is not None and _cached.model_id == model_id:
        return _cached

    async with _cache_lock:
        # Double-check after lock
        if _cached is not None and _cached.model_id == model_id:
            return _cached

        # Evict old model
        if _cached is not None:
            logger.info(
                "Evicting pipeline {} in favour of {}",
                _cached.model_id,
                model_id,
            )
            _cached.pipeline = None
            _cached.img2img_pipeline = None
            _cached = None
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

        # Load new model
        try:

            def _load() -> tuple[Any, str]:
                import torch
                from diffusers import DiffusionPipeline

                skip_kwargs = _build_skip_kwargs(model_path)
                # Use float16 on CUDA, float32 on CPU to avoid dtype mismatches
                dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                pipe = DiffusionPipeline.from_pretrained(
                    model_path,
                    torch_dtype=dtype,
                    local_files_only=True,
                    requires_safety_checker=False,
                    **skip_kwargs,
                )
                if torch.cuda.is_available():
                    pipe = pipe.to("cuda")
                return pipe, type(pipe).__name__

            pipe, cls_name = await asyncio.to_thread(_load)
            arch = detect_architecture(cls_name)
            native_res = detect_native_resolution(model_path)
            _cached = CachedPipeline(
                model_id=model_id or "",
                model_path=model_path,
                pipeline=pipe,
                architecture=arch,
                pipeline_class_name=cls_name,
                native_resolution=native_res,
            )
            logger.info(
                "Loaded pipeline {} (class={}, arch={})",
                model_id,
                cls_name,
                arch,
            )
            return _cached

        except ImportError:
            logger.warning(
                "diffusers not installed — image generation unavailable"
            )
            return None
        except Exception as e:
            logger.error("Failed to load diffusion pipeline: {}", e)
            return None


async def get_img2img_pipeline(cached: CachedPipeline) -> Any | None:
    """Derive an img2img pipeline from *cached*, sharing weights via from_pipe().

    Returns the img2img pipeline object, or None if unsupported.
    """
    if cached.img2img_pipeline is not None:
        return cached.img2img_pipeline

    try:

        def _derive() -> Any | None:
            cls = _get_img2img_class(cached.pipeline_class_name)
            if cls is None:
                logger.warning(
                    "No img2img class for {}", cached.pipeline_class_name
                )
                return None
            return cls.from_pipe(cached.pipeline)

        img2img = await asyncio.to_thread(_derive)
        if img2img is not None:
            cached.img2img_pipeline = img2img
            logger.info("img2img pipeline ready (shared weights)")
        return img2img

    except Exception as e:
        logger.error("Failed to derive img2img pipeline: {}", e)
        return None


# ---------------------------------------------------------------------------
# Synchronous generation (runs in thread)
# ---------------------------------------------------------------------------


class GenerationCancelled(Exception):
    """Raised when image generation is cancelled between images."""


def _decode_latents(pipeline: Any, latents: Any) -> Any:
    """Decode latent tensor to a PIL Image via the pipeline's VAE."""
    import torch
    from PIL import Image as PILImage

    with torch.no_grad():
        # Scale latents (standard VAE scaling factor)
        scaling_factor = getattr(pipeline, "vae_scale_factor", None)
        vae = getattr(pipeline, "vae", None)
        if vae is None:
            return None

        # Most pipelines store the scaling factor on the scheduler config or vae config
        vae_scaling = getattr(vae.config, "scaling_factor", 0.18215)
        decoded = vae.decode(latents / vae_scaling, return_dict=False)[0]

        # Convert to PIL: clamp to [0,1], permute to HWC, scale to 255
        decoded = (decoded / 2 + 0.5).clamp(0, 1)
        decoded = decoded.cpu().permute(0, 2, 3, 1).float().numpy()
        image_array = (decoded[0] * 255).round().astype("uint8")
        return PILImage.fromarray(image_array)


def _sync_generate(
    pipeline: Any,
    prompt: str,
    negative_prompt: str | None,
    guidance_scale: float,
    num_images: int = 4,
    seed: int | None = None,
    source_image: Any | None = None,
    strength: float = 0.75,
    img2img_pipeline: Any | None = None,
    width: int = 1024,
    height: int = 1024,
    num_inference_steps: int = 30,
    cancel_event: threading.Event | None = None,
    per_image_callback: Callable[[Any, int, int], None] | None = None,
    midpoint_callback: Callable[[Any, int], None] | None = None,
    max_sequence_length: int | None = None,
    true_cfg_scale: float | None = None,
) -> list[tuple[Any, int]]:
    """Synchronous generation call. Returns list of (PIL.Image, seed) tuples.

    When *per_image_callback* is provided it is called after each image
    with ``(pil_image, seed, index)`` — still on the generation thread.

    When *midpoint_callback* is provided it is called at the halfway step
    with ``(pil_image, image_index)`` — a decoded preview of the in-progress image.
    """
    import torch

    # Choose the right pipeline
    active_pipeline = img2img_pipeline if source_image is not None else pipeline

    results: list[tuple[Any, int]] = []
    midpoint_step = num_inference_steps // 2

    for i in range(num_images):
        # Check for cancellation between images
        if cancel_event is not None and cancel_event.is_set():
            logger.info("Generation cancelled after {} images", len(results))
            raise GenerationCancelled()

        img_seed = (seed or torch.randint(0, 2**32, (1,)).item()) + i
        generator = torch.Generator().manual_seed(img_seed)

        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "guidance_scale": guidance_scale,
            "generator": generator,
            "num_inference_steps": num_inference_steps,
            "height": height,
            "width": width,
        }
        if negative_prompt:
            kwargs["negative_prompt"] = negative_prompt

        if source_image is not None:
            kwargs["image"] = source_image
            kwargs["strength"] = strength

        if max_sequence_length is not None:
            kwargs["max_sequence_length"] = max_sequence_length
        if true_cfg_scale is not None:
            kwargs["true_cfg_scale"] = true_cfg_scale

        # Midpoint preview callback
        if midpoint_callback is not None:
            current_image_index = i

            def _step_callback(pipe, step_index, timestep, callback_kwargs):
                if step_index == midpoint_step:
                    latents = callback_kwargs.get("latents")
                    if latents is not None:
                        preview = _decode_latents(pipe, latents)
                        if preview is not None:
                            midpoint_callback(preview, current_image_index)
                return callback_kwargs

            kwargs["callback_on_step_end"] = _step_callback

        output = active_pipeline(**kwargs)
        image = output.images[0]
        results.append((image, img_seed))

        if per_image_callback is not None:
            per_image_callback(image, img_seed, i)

    return results


# ---------------------------------------------------------------------------
# High-level generate
# ---------------------------------------------------------------------------


async def generate(
    project_root: Path,
    feature_id: str,
    task_id: str,
    prompt: str,
    negative_prompt: str | None = None,
    guidance_scale: float = 7.5,
    num_images: int = 4,
    seed: int | None = None,
    on_image_complete: Callable[[GeneratedImage], None] | None = None,
    on_midpoint: Callable[[str, int], None] | None = None,
    source_image_id: str | None = None,
    divergence: float | None = None,
    width: int = 1024,
    height: int = 1024,
    model_id: str | None = None,
    model_path: str | None = None,
    num_inference_steps: int = 30,
    max_sequence_length: int | None = None,
    true_cfg_scale: float | None = None,
    cancel_event: threading.Event | None = None,
) -> ImageRound | None:
    """Generate images for a task.

    Saves images to work/{feature_id}/{task_id}/images/ and returns
    an ImageRound describing the generated images.

    When source_image_id is provided, runs img2img instead of text2img.
    divergence maps to the diffusion strength parameter (default 0.75).

    Returns None if the pipeline is unavailable.
    """
    cached = await get_pipeline(model_id=model_id, model_path=model_path)
    if cached is None:
        logger.warning(
            "Image generation skipped — pipeline unavailable for {}/{}",
            feature_id,
            task_id,
        )
        return None

    pipeline = cached.pipeline

    # Ensure output directory exists
    task_dir = create_task_work_dir(project_root, feature_id, task_id)
    images_dir = task_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # Handle img2img source
    source_image = None
    img2img_pipe = None
    strength = 0.75

    if source_image_id is not None:
        source_path = images_dir / f"{source_image_id}.png"
        if not source_path.exists():
            logger.warning(
                "Source image not found: {}", source_path
            )
            return None

        from PIL import Image

        source_image = Image.open(source_path).convert("RGB")
        source_image = source_image.resize((width, height))

        img2img_pipe = await get_img2img_pipeline(cached)
        if img2img_pipe is None:
            logger.warning("img2img pipeline unavailable")
            return None

        if divergence is not None:
            strength = divergence

    # Progressive callback: save each image and notify as it finishes
    # (runs on the generation thread inside _sync_generate)
    generated: list[GeneratedImage] = []
    loop = asyncio.get_running_loop()

    def _per_image(pil_image: Any, img_seed: int, idx: int) -> None:
        image_id = str(uuid.uuid4())[:8]
        file_path = images_dir / f"{image_id}.png"
        pil_image.save(str(file_path))

        # Clean up any midpoint preview for this index
        for preview_file in images_dir.glob("*_preview.jpg"):
            try:
                preview_file.unlink()
            except OSError:
                pass

        img = GeneratedImage(
            id=image_id,
            file_path=str(file_path.relative_to(project_root)),
            seed=img_seed,
            index=idx,
        )
        generated.append(img)

        if on_image_complete is not None:
            loop.call_soon_threadsafe(on_image_complete, img)

    # Midpoint preview callback: save a JPEG preview and notify
    def _midpoint(pil_image: Any, idx: int) -> None:
        preview_id = str(uuid.uuid4())[:8]
        preview_path = images_dir / f"{preview_id}_preview.jpg"
        pil_image.save(str(preview_path), format="JPEG", quality=70)

        if on_midpoint is not None:
            loop.call_soon_threadsafe(on_midpoint, preview_id, idx)

    # Run generation in a thread
    image_results = await asyncio.to_thread(
        _sync_generate,
        pipeline,
        prompt,
        negative_prompt,
        guidance_scale,
        num_images,
        seed,
        source_image,
        strength,
        img2img_pipe,
        width,
        height,
        num_inference_steps,
        cancel_event,
        _per_image,
        _midpoint,
        max_sequence_length,
        true_cfg_scale,
    )

    # Fallback: if callback wasn't invoked (e.g. mocked _sync_generate),
    # save images the old way
    if not generated:
        for idx, (pil_image, img_seed) in enumerate(image_results):
            image_id = str(uuid.uuid4())[:8]
            file_path = images_dir / f"{image_id}.png"

            await asyncio.to_thread(pil_image.save, str(file_path))

            img = GeneratedImage(
                id=image_id,
                file_path=str(file_path.relative_to(project_root)),
                seed=img_seed,
                index=idx,
            )
            generated.append(img)

            if on_image_complete is not None:
                on_image_complete(img)

    # Count existing rounds to determine round number
    round_number = 1  # Default for first round

    image_round = ImageRound(
        round_number=round_number,
        prompt=prompt,
        negative_prompt=negative_prompt,
        guidance_scale=guidance_scale,
        divergence=divergence,
        source_image_id=source_image_id,
        images=generated,
    )

    logger.info(
        "Generated {} images for {}/{}", len(generated), feature_id, task_id
    )
    return image_round


# ---------------------------------------------------------------------------
# Ensure pipeline (convenience for job manager)
# ---------------------------------------------------------------------------


async def ensure_pipeline(
    model_id: str | None = None,
    model_path: str | None = None,
) -> bool:
    """Ensure the diffusion pipeline is loaded. Returns True if available."""
    return (await get_pipeline(model_id=model_id, model_path=model_path)) is not None


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


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
        "Selected image {} for task {}/{}", image_id, feature_id, task_id
    )
    return True
