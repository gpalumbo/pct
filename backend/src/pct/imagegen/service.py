"""Core image generation logic using HuggingFace diffusers."""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

from loguru import logger

from pct import config
from pct.imagegen import job_manager
from pct.imagegen.models import (
    GenerateRequest,
    GeneratedImage,
    GenerationRound,
    JobStatus,
    SelectImageRequest,
    SessionMetadata,
)

# Lazy-loaded pipeline singleton
_pipeline = None
_pipeline_lock = asyncio.Lock()

NUM_IMAGES = 4


def _project_root() -> Path:
    if config.settings.project_root:
        return Path(config.settings.project_root)
    return Path.cwd()


def _images_dir(feature_id: str, task_id: str) -> Path:
    return _project_root() / "work" / feature_id / task_id / "images"


def _session_path(feature_id: str, task_id: str) -> Path:
    return _images_dir(feature_id, task_id) / "session.json"


_DEFAULT_MODEL = "sd-legacy/stable-diffusion-v1-5"
_IMAGEGEN_AGENT_ID = "stable-diffusion-v1-5"


def _resolve_model_id() -> str:
    """Get model ID from the imagegen agent config, falling back to default."""
    try:
        from pct.settings.service import get_agent

        agent = get_agent(_IMAGEGEN_AGENT_ID)
        if agent and agent.model:
            return agent.model
    except Exception:
        pass
    return _DEFAULT_MODEL


def _get_pipeline():
    """Lazy-load the Stable Diffusion pipeline singleton."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    try:
        import torch
        from diffusers import StableDiffusionPipeline
    except ImportError as exc:
        raise RuntimeError(
            "Image generation requires the 'imagegen' optional dependencies. "
            "Install with: pip install -e '.[imagegen]'"
        ) from exc

    model_id = _resolve_model_id()
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Loading Stable Diffusion pipeline '{}' ({}, {})", model_id, device, dtype)
    _pipeline = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)
    _pipeline = _pipeline.to(device)
    _pipeline.enable_attention_slicing()
    logger.info("Pipeline loaded successfully")
    return _pipeline


def start_generation(req: GenerateRequest) -> str:
    """Create a job and launch async generation."""
    job_id = job_manager.create_job()
    task = asyncio.create_task(_generate_images(job_id, req))
    job_manager.register_task(job_id, task)
    return job_id


async def _generate_images(job_id: str, req: GenerateRequest) -> None:
    """Run image generation in a thread pool."""
    job_manager.update_job(job_id, status=JobStatus.RUNNING, progress=0.05)

    try:
        loop = asyncio.get_event_loop()
        images = await loop.run_in_executor(None, _generate_sync, job_id, req)
        job_manager.update_job(
            job_id, status=JobStatus.COMPLETED, progress=1.0, images=images
        )
    except Exception as exc:
        logger.exception("Image generation failed for job {}", job_id)
        job_manager.update_job(
            job_id, status=JobStatus.FAILED, error=str(exc)
        )


def _generate_sync(job_id: str, req: GenerateRequest) -> list[GeneratedImage]:
    """Synchronous generation — runs in executor thread."""
    import torch

    pipe = _get_pipeline()
    out_dir = _images_dir(req.feature_id, req.task_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine round number from session
    session = load_metadata(req.feature_id, req.task_id)
    round_num = session.current_round + 1

    base_seed = req.seed if req.seed is not None else random.randint(0, 2**32 - 1)
    generated: list[GeneratedImage] = []

    is_img2img = req.source_image is not None
    img2img_pipe = None
    source_pil = None

    if is_img2img:
        from diffusers import StableDiffusionImg2ImgPipeline
        from PIL import Image

        img2img_pipe = StableDiffusionImg2ImgPipeline(**pipe.components)
        source_path = _images_dir(req.feature_id, req.task_id) / req.source_image
        source_pil = Image.open(source_path).convert("RGB").resize((req.width, req.height))

    for i in range(NUM_IMAGES):
        seed = base_seed + i
        generator = torch.Generator(device=pipe.device).manual_seed(seed)

        if is_img2img and img2img_pipe is not None:
            result = img2img_pipe(
                prompt=req.prompt,
                negative_prompt=req.negative_prompt or None,
                image=source_pil,
                strength=req.divergence,
                guidance_scale=req.guidance_scale,
                num_inference_steps=req.num_inference_steps,
                generator=generator,
            )
        else:
            result = pipe(
                prompt=req.prompt,
                negative_prompt=req.negative_prompt or None,
                guidance_scale=req.guidance_scale,
                num_inference_steps=req.num_inference_steps,
                width=req.width,
                height=req.height,
                generator=generator,
            )

        image = result.images[0]
        filename = f"round_{round_num:03d}_img_{i:03d}.png"
        image.save(out_dir / filename)

        gen_img = GeneratedImage(
            filename=filename, seed=seed, round=round_num, index=i
        )
        generated.append(gen_img)

        # Update progress
        progress = 0.1 + (0.9 * (i + 1) / NUM_IMAGES)
        job_manager.update_job(job_id, progress=progress)

    # Save round to session metadata
    gen_round = GenerationRound(
        round=round_num,
        prompt=req.prompt,
        params={
            "negative_prompt": req.negative_prompt,
            "guidance_scale": req.guidance_scale,
            "num_inference_steps": req.num_inference_steps,
            "width": req.width,
            "height": req.height,
            "divergence": req.divergence,
            "source_image": req.source_image,
        },
        images=generated,
    )
    session.rounds.append(gen_round)
    session.current_round = round_num
    save_metadata(session)

    return generated


def load_metadata(feature_id: str, task_id: str) -> SessionMetadata:
    """Load session metadata from JSON sidecar, or create a fresh one."""
    path = _session_path(feature_id, task_id)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionMetadata(**data)
    return SessionMetadata(feature_id=feature_id, task_id=task_id)


def save_metadata(session: SessionMetadata) -> None:
    """Persist session metadata to JSON sidecar."""
    path = _session_path(session.feature_id, session.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def select_image(feature_id: str, task_id: str, req: SelectImageRequest) -> SessionMetadata:
    """Mark a chosen image in a specific round."""
    session = load_metadata(feature_id, task_id)
    for r in session.rounds:
        if r.round == req.round:
            r.selected_image = req.filename
            break
    save_metadata(session)
    return session
