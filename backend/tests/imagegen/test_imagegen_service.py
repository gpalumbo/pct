"""Tests for image generation service — with mocked pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pct.imagegen.job_manager import JobManager, get_job_manager
from pct.imagegen.models import JobStatus
from pct.models.agents import ModelRegistryEntry
from pct.models.enums import ProviderType
import threading

from pct.imagegen.models import build_resolutions
from pct.imagegen.service import (
    CachedPipeline,
    GenerationCancelled,
    _build_skip_kwargs,
    _sync_generate,
    detect_architecture,
    detect_native_resolution,
    generate,
    get_session,
    select_image,
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create project structure for image gen tests."""
    (tmp_path / "work").mkdir()
    return tmp_path


def _make_cached(pipeline=None, img2img=None, model_id="test", model_path="/fake"):
    """Helper to build a CachedPipeline for tests."""
    return CachedPipeline(
        model_id=model_id,
        model_path=model_path,
        pipeline=pipeline or MagicMock(),
        img2img_pipeline=img2img,
        architecture="sdxl",
        pipeline_class_name="StableDiffusionXLPipeline",
    )


class TestDetectArchitecture:
    def test_sdxl(self):
        assert detect_architecture("StableDiffusionXLPipeline") == "sdxl"

    def test_sd15(self):
        assert detect_architecture("StableDiffusionPipeline") == "sd15"

    def test_flux(self):
        assert detect_architecture("FluxPipeline") == "flux"

    def test_sd3(self):
        assert detect_architecture("StableDiffusion3Pipeline") == "sd3"

    def test_unknown(self):
        assert detect_architecture("SomethingElsePipeline") is None


class TestGenerateImages:
    @pytest.mark.asyncio
    async def test_generate_returns_none_without_pipeline(
        self, project_root: Path
    ):
        """generate() returns None when diffusers pipeline is not available."""
        with patch(
            "pct.imagegen.service.get_pipeline",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await generate(
                project_root, "f1", "t1", prompt="A cat",
                model_id="test", model_path="/fake",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_with_mock_pipeline(self, project_root: Path):
        """generate() returns an ImageRound with mocked images."""
        # Create a mock PIL image
        mock_image = MagicMock()
        mock_image.save = MagicMock()

        cached = _make_cached()

        with patch(
            "pct.imagegen.service.get_pipeline",
            new_callable=AsyncMock,
            return_value=cached,
        ), patch(
            "pct.imagegen.service._sync_generate",
            return_value=[(mock_image, 42), (mock_image, 43)],
        ):
            result = await generate(
                project_root,
                "f1",
                "t1",
                prompt="A beautiful sunset",
                num_images=2,
                model_id="test",
                model_path="/fake",
            )

        assert result is not None
        assert len(result.images) == 2
        assert result.prompt == "A beautiful sunset"
        assert result.images[0].index == 0
        assert result.images[1].index == 1

    @pytest.mark.asyncio
    async def test_generate_creates_directories(self, project_root: Path):
        """generate() returns None cleanly when pipeline unavailable."""
        with patch(
            "pct.imagegen.service.get_pipeline",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await generate(
                project_root, "f1", "t1", prompt="test",
                model_id="test", model_path="/fake",
            )

        # This test verifies the early-return path works without errors


class TestSyncGenerateImg2Img:
    def test_img2img_uses_img2img_pipeline(self):
        """When source_image is provided, img2img pipeline is called with image and strength."""
        mock_t2i_pipeline = MagicMock()
        mock_i2i_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_pil_image = MagicMock()
        mock_output.images = [mock_pil_image]
        mock_i2i_pipeline.return_value = mock_output

        source_img = MagicMock()

        results = _sync_generate(
            pipeline=mock_t2i_pipeline,
            prompt="refine this",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=1,
            seed=42,
            source_image=source_img,
            strength=0.6,
            img2img_pipeline=mock_i2i_pipeline,
        )

        assert len(results) == 1
        # img2img pipeline should be called, not text2img
        mock_i2i_pipeline.assert_called_once()
        mock_t2i_pipeline.assert_not_called()
        # Verify image and strength were passed
        call_kwargs = mock_i2i_pipeline.call_args[1]
        assert call_kwargs["image"] is source_img
        assert call_kwargs["strength"] == 0.6

    def test_text2img_unchanged_without_source(self):
        """When source_image is None, text2img pipeline is used as before."""
        mock_t2i_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_pil_image = MagicMock()
        mock_output.images = [mock_pil_image]
        mock_t2i_pipeline.return_value = mock_output

        results = _sync_generate(
            pipeline=mock_t2i_pipeline,
            prompt="a cat",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=1,
            seed=42,
        )

        assert len(results) == 1
        mock_t2i_pipeline.assert_called_once()
        call_kwargs = mock_t2i_pipeline.call_args[1]
        assert "image" not in call_kwargs
        assert "strength" not in call_kwargs


class TestGenerateImg2Img:
    @pytest.mark.asyncio
    async def test_generate_img2img_source_not_found(self, project_root: Path):
        """generate() returns None when source image file doesn't exist."""
        cached = _make_cached()

        with patch(
            "pct.imagegen.service.get_pipeline",
            new_callable=AsyncMock,
            return_value=cached,
        ):
            result = await generate(
                project_root,
                "f1",
                "t1",
                prompt="refine this",
                source_image_id="nonexistent",
                model_id="test",
                model_path="/fake",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_img2img_populates_round_fields(
        self, project_root: Path
    ):
        """generate() sets divergence and source_image_id on the returned ImageRound."""
        mock_image = MagicMock()
        mock_image.save = MagicMock()

        cached = _make_cached()
        mock_img2img = MagicMock()

        # Create a source image file
        task_dir = project_root / "work" / "f1" / "t1" / "images"
        task_dir.mkdir(parents=True, exist_ok=True)
        source_path = task_dir / "src123.png"
        # Write a minimal valid PNG
        from PIL import Image

        img = Image.new("RGB", (64, 64), color="red")
        img.save(str(source_path))

        with patch(
            "pct.imagegen.service.get_pipeline",
            new_callable=AsyncMock,
            return_value=cached,
        ), patch(
            "pct.imagegen.service.get_img2img_pipeline",
            new_callable=AsyncMock,
            return_value=mock_img2img,
        ), patch(
            "pct.imagegen.service._sync_generate",
            return_value=[(mock_image, 42)],
        ):
            result = await generate(
                project_root,
                "f1",
                "t1",
                prompt="refine",
                num_images=1,
                source_image_id="src123",
                divergence=0.6,
                model_id="test",
                model_path="/fake",
            )

        assert result is not None
        assert result.source_image_id == "src123"
        assert result.divergence == 0.6


class TestRunJobPassthrough:
    @pytest.mark.asyncio
    async def test_run_job_passes_source_image_id_and_divergence(
        self, project_root: Path
    ):
        """run_job passes source_image_id and divergence through to generate()."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="refine it",
            source_image_id="img42",
            divergence=0.5,
        )

        mock_round = MagicMock()
        mock_round.images = []

        mock_entry = ModelRegistryEntry(
            id="test-model",
            name="Test",
            provider_type=ProviderType.huggingface,
            model_identifier="test/model",
            file_path="/fake/path",
        )

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=mock_entry,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "pct.imagegen.job_manager.generate",
            new_callable=AsyncMock,
            return_value=mock_round,
        ) as mock_generate, patch(
            "pct.imagegen.job_manager.ensure_model_ready",
            new_callable=AsyncMock,
            side_effect=lambda entry, *a, **kw: entry,
        ):
            await manager.run_job(job_id, project_root)

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["source_image_id"] == "img42"
        assert call_kwargs["divergence"] == 0.5
        assert call_kwargs["model_id"] == "test-model"
        assert call_kwargs["model_path"] == "/fake/path"


class TestSyncGenerateResolution:
    def test_sync_generate_passes_width_height_to_pipeline(self):
        """_sync_generate includes width and height in pipeline kwargs."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_pil_image = MagicMock()
        mock_output.images = [mock_pil_image]
        mock_pipeline.return_value = mock_output

        _sync_generate(
            pipeline=mock_pipeline,
            prompt="a cat",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=1,
            seed=42,
            width=1344,
            height=768,
        )

        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["width"] == 1344
        assert call_kwargs["height"] == 768

    def test_sync_generate_default_resolution(self):
        """_sync_generate defaults to 1024x1024."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_output.images = [MagicMock()]
        mock_pipeline.return_value = mock_output

        _sync_generate(
            pipeline=mock_pipeline,
            prompt="a cat",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=1,
            seed=42,
        )

        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["width"] == 1024
        assert call_kwargs["height"] == 1024


class TestGenerateImg2ImgResolution:
    @pytest.mark.asyncio
    async def test_generate_img2img_resizes_to_custom_resolution(
        self, project_root: Path
    ):
        """generate() resizes source image to (width, height), not hardcoded 1024."""
        mock_image = MagicMock()
        mock_image.save = MagicMock()

        cached = _make_cached()
        mock_img2img = MagicMock()

        # Create a source image file
        task_dir = project_root / "work" / "f1" / "t1" / "images"
        task_dir.mkdir(parents=True, exist_ok=True)
        source_path = task_dir / "src456.png"
        from PIL import Image

        img = Image.new("RGB", (64, 64), color="blue")
        img.save(str(source_path))

        with patch(
            "pct.imagegen.service.get_pipeline",
            new_callable=AsyncMock,
            return_value=cached,
        ), patch(
            "pct.imagegen.service.get_img2img_pipeline",
            new_callable=AsyncMock,
            return_value=mock_img2img,
        ), patch(
            "pct.imagegen.service._sync_generate",
            return_value=[(mock_image, 42)],
        ) as mock_sync_gen:
            result = await generate(
                project_root,
                "f1",
                "t1",
                prompt="refine",
                num_images=1,
                source_image_id="src456",
                divergence=0.6,
                width=1344,
                height=768,
                model_id="test",
                model_path="/fake",
            )

        assert result is not None
        # _sync_generate should have received width=1344, height=768
        # Args are positional: ..., width, height, num_inference_steps, cancel_event
        call_args = mock_sync_gen.call_args[0]
        # Find by known values — width=1344 and height=768 are unique
        assert 1344 in call_args, f"width 1344 not in positional args: {call_args}"
        assert 768 in call_args, f"height 768 not in positional args: {call_args}"


class TestResolutionsEndpoint:
    def test_resolutions_returns_expected_list(self):
        """GET /api/imagegen/resolutions returns the SDXL preset list."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from pct.imagegen.router import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/api/imagegen/resolutions")
        assert resp.status_code == 200
        data = resp.json()
        assert "resolutions" in data
        resolutions = data["resolutions"]
        assert len(resolutions) == 9
        assert resolutions[0]["label"] == "1:1 Square"
        assert resolutions[0]["width"] == 1024
        assert resolutions[0]["height"] == 1024
        # Verify a landscape entry
        labels = [r["label"] for r in resolutions]
        assert "16:9 Landscape" in labels

    def test_resolutions_with_architecture_param(self):
        """GET /api/imagegen/resolutions?architecture=sd15 returns SD 1.5 presets."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from pct.imagegen.router import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/api/imagegen/resolutions?architecture=sd15")
        assert resp.status_code == 200
        data = resp.json()
        resolutions = data["resolutions"]
        assert len(resolutions) == 5
        assert resolutions[0]["width"] == 512


class TestRunJobPassesResolution:
    @pytest.mark.asyncio
    async def test_run_job_passes_width_height(self, project_root: Path):
        """run_job passes width and height through to generate()."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="landscape",
            width=1344,
            height=768,
        )

        mock_round = MagicMock()
        mock_round.images = []

        mock_entry = ModelRegistryEntry(
            id="test-model",
            name="Test",
            provider_type=ProviderType.huggingface,
            model_identifier="test/model",
            file_path="/fake/path",
        )

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=mock_entry,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "pct.imagegen.job_manager.generate",
            new_callable=AsyncMock,
            return_value=mock_round,
        ) as mock_generate, patch(
            "pct.imagegen.job_manager.ensure_model_ready",
            new_callable=AsyncMock,
            side_effect=lambda entry, *a, **kw: entry,
        ):
            await manager.run_job(job_id, project_root)

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["width"] == 1344
        assert call_kwargs["height"] == 768


class TestGetSession:
    def test_get_session_returns_empty_session(self, project_root: Path):
        """get_session returns an empty ImageSession."""
        session = get_session(project_root, "f1", "t1")
        assert session.task_id == "t1"
        assert session.rounds == []
        assert session.accepted_image_id is None


class TestSelectImage:
    def test_select_image_returns_true(self, project_root: Path):
        """select_image returns True (stub implementation)."""
        result = select_image(project_root, "f1", "t1", "img-123")
        assert result is True


class TestJobManager:
    def test_create_job(self):
        """JobManager.create_job creates a pending job."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="A cat",
        )

        assert job_id is not None
        job = manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.pending
        assert job.feature_id == "f1"
        assert job.task_id == "t1"

    def test_create_job_with_model_id(self):
        """JobManager.create_job stores model_id."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="A cat",
            model_id="my-model",
        )

        job = manager.get_job(job_id)
        assert job is not None
        assert job.model_id == "my-model"

    def test_job_lifecycle(self):
        """Job transitions through pending -> running -> completed."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="A dog"
        )

        manager.set_running(job_id)
        job = manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.running

        manager.set_completed(job_id, [{"id": "img-1", "path": "a.png"}])
        job = manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.completed
        assert len(job.images) == 1
        assert job.completed_at is not None

    def test_job_failure(self):
        """Job can transition to failed state."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="A bird"
        )

        manager.set_failed(job_id, "Pipeline crashed")
        job = manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.failed
        assert job.error == "Pipeline crashed"

    def test_list_jobs_filters(self):
        """list_jobs filters by feature_id and task_id."""
        manager = JobManager()
        manager.create_job(feature_id="f1", task_id="t1", prompt="A")
        manager.create_job(feature_id="f1", task_id="t2", prompt="B")
        manager.create_job(feature_id="f2", task_id="t1", prompt="C")

        all_jobs = manager.list_jobs()
        assert len(all_jobs) == 3

        f1_jobs = manager.list_jobs(feature_id="f1")
        assert len(f1_jobs) == 2

        f1_t1_jobs = manager.list_jobs(feature_id="f1", task_id="t1")
        assert len(f1_t1_jobs) == 1

    def test_get_nonexistent_job(self):
        """get_job returns None for unknown job_id."""
        manager = JobManager()
        assert manager.get_job("nonexistent") is None

    @pytest.mark.asyncio
    async def test_run_job_with_unavailable_pipeline(
        self, project_root: Path
    ):
        """run_job marks job as failed when pipeline is unavailable."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=None,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=False,
        ):
            await manager.run_job(job_id, project_root)

        job = manager.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.failed
        assert "unavailable" in (job.error or "").lower()

    def test_get_job_manager_singleton(self):
        """get_job_manager returns the same instance."""
        import pct.imagegen.job_manager as mod

        # Reset singleton
        mod._job_manager = None

        m1 = get_job_manager()
        m2 = get_job_manager()
        assert m1 is m2

        # Clean up
        mod._job_manager = None


class TestJobStatusMessage:
    @pytest.mark.asyncio
    async def test_run_job_sets_status_message_from_download(
        self, project_root: Path
    ):
        """run_job updates job.status_message via _on_status callback."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )

        captured_messages: list[str] = []

        async def fake_ensure(entry, on_status, **kw):
            await on_status("Downloading model X...")
            await on_status("Download complete.")
            return entry

        mock_entry = ModelRegistryEntry(
            id="test-model",
            name="Test",
            provider_type=ProviderType.huggingface,
            model_identifier="test/model",
            file_path="/fake/path",
        )

        mock_round = MagicMock()
        mock_round.images = []

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=mock_entry,
        ), patch(
            "pct.imagegen.job_manager.ensure_model_ready",
            side_effect=fake_ensure,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "pct.imagegen.job_manager.generate",
            new_callable=AsyncMock,
            return_value=mock_round,
        ):
            await manager.run_job(job_id, project_root)

        job = manager.get_job(job_id)
        assert job is not None
        # status_message should be the last message from the callback
        assert job.status_message == "Download complete."

    def test_job_record_status_message_default(self):
        """JobRecord.status_message defaults to None."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.status_message is None


class TestBuildSkipKwargs:
    def test_reads_optional_components_from_class(self, tmp_path: Path):
        """_build_skip_kwargs returns None for each _optional_components entry."""
        import json

        # Write a model_index.json pointing to StableDiffusionPipeline
        (tmp_path / "model_index.json").write_text(
            json.dumps({"_class_name": "StableDiffusionPipeline"})
        )

        result = _build_skip_kwargs(str(tmp_path))

        # StableDiffusionPipeline has safety_checker and feature_extractor
        assert "safety_checker" in result
        assert "feature_extractor" in result
        for v in result.values():
            assert v is None

    def test_fallback_when_no_model_index(self, tmp_path: Path):
        """Returns fallback dict when model_index.json is missing."""
        result = _build_skip_kwargs(str(tmp_path))
        assert result == {"safety_checker": None}

    def test_fallback_when_class_not_found(self, tmp_path: Path):
        """Returns fallback dict when _class_name doesn't exist in diffusers."""
        import json

        (tmp_path / "model_index.json").write_text(
            json.dumps({"_class_name": "TotallyFakePipeline"})
        )
        result = _build_skip_kwargs(str(tmp_path))
        assert result == {"safety_checker": None}

    def test_fallback_when_malformed_json(self, tmp_path: Path):
        """Returns fallback dict when model_index.json is invalid JSON."""
        (tmp_path / "model_index.json").write_text("not valid json {{{")
        result = _build_skip_kwargs(str(tmp_path))
        assert result == {"safety_checker": None}

    def test_fallback_when_no_optional_components(self, tmp_path: Path):
        """Returns fallback dict when pipeline class has empty _optional_components."""
        import json

        # Mock a pipeline class with no optional components
        with patch("diffusers.FakePipelineNoOpt", create=True) as mock_cls:
            mock_cls._optional_components = []
            (tmp_path / "model_index.json").write_text(
                json.dumps({"_class_name": "FakePipelineNoOpt"})
            )
            result = _build_skip_kwargs(str(tmp_path))

        assert result == {"safety_checker": None}


class TestDetectNativeResolution:
    def test_reads_unet_config(self, tmp_path: Path):
        """detect_native_resolution reads sample_size from unet/config.json."""
        import json

        unet_dir = tmp_path / "unet"
        unet_dir.mkdir()
        (unet_dir / "config.json").write_text(json.dumps({"sample_size": 128}))

        assert detect_native_resolution(str(tmp_path)) == 128 * 8

    def test_reads_transformer_config(self, tmp_path: Path):
        """detect_native_resolution reads from transformer/config.json when unet absent."""
        import json

        trans_dir = tmp_path / "transformer"
        trans_dir.mkdir()
        (trans_dir / "config.json").write_text(json.dumps({"sample_size": 64}))

        assert detect_native_resolution(str(tmp_path)) == 64 * 8

    def test_prefers_unet_over_transformer(self, tmp_path: Path):
        """detect_native_resolution checks unet first."""
        import json

        unet_dir = tmp_path / "unet"
        unet_dir.mkdir()
        (unet_dir / "config.json").write_text(json.dumps({"sample_size": 128}))

        trans_dir = tmp_path / "transformer"
        trans_dir.mkdir()
        (trans_dir / "config.json").write_text(json.dumps({"sample_size": 64}))

        assert detect_native_resolution(str(tmp_path)) == 128 * 8

    def test_handles_list_sample_size(self, tmp_path: Path):
        """detect_native_resolution handles sample_size as a list."""
        import json

        unet_dir = tmp_path / "unet"
        unet_dir.mkdir()
        (unet_dir / "config.json").write_text(json.dumps({"sample_size": [96, 96]}))

        assert detect_native_resolution(str(tmp_path)) == 96 * 8

    def test_fallback_when_missing(self, tmp_path: Path):
        """detect_native_resolution returns 1024 when no config found."""
        assert detect_native_resolution(str(tmp_path)) == 1024

    def test_fallback_when_no_sample_size(self, tmp_path: Path):
        """detect_native_resolution returns 1024 when sample_size key is missing."""
        import json

        unet_dir = tmp_path / "unet"
        unet_dir.mkdir()
        (unet_dir / "config.json").write_text(json.dumps({"in_channels": 4}))

        assert detect_native_resolution(str(tmp_path)) == 1024


class TestBuildResolutions:
    def test_1024_matches_sdxl_square(self):
        """build_resolutions(1024) produces 1024x1024 for 1:1."""
        res = build_resolutions(1024)
        square = res[0]
        assert square["label"] == "1:1 Square"
        assert square["width"] == 1024
        assert square["height"] == 1024

    def test_512_produces_smaller(self):
        """build_resolutions(512) produces 512x512 for 1:1."""
        res = build_resolutions(512)
        square = res[0]
        assert square["width"] == 512
        assert square["height"] == 512

    def test_all_multiples_of_8(self):
        """All generated widths and heights are multiples of 8."""
        for native in (512, 768, 1024, 1536):
            for entry in build_resolutions(native):
                assert entry["width"] % 8 == 0, f"width {entry['width']} not multiple of 8"
                assert entry["height"] % 8 == 0, f"height {entry['height']} not multiple of 8"

    def test_aspect_ratio_count(self):
        """build_resolutions returns 9 presets (matching template count)."""
        assert len(build_resolutions(1024)) == 9

    def test_pixel_count_close_to_native_squared(self):
        """Each preset's pixel count should be close to native_res^2."""
        native = 1024
        target = native * native
        for entry in build_resolutions(native):
            pixels = entry["width"] * entry["height"]
            # Allow 5% deviation due to rounding
            assert abs(pixels - target) / target < 0.05


class TestDraftMode:
    def test_draft_halves_resolution(self):
        """create_job with draft=True halves width and height."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="test",
            width=1024,
            height=1024,
            draft=True,
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.width == 512
        assert job.height == 512
        assert job.num_inference_steps == 10

    def test_draft_rounds_to_multiple_of_8(self):
        """Draft mode rounds halved dimensions to nearest multiple of 8."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="test",
            width=1344,
            height=768,
            draft=True,
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.width % 8 == 0
        assert job.height % 8 == 0
        assert job.width == 672
        assert job.height == 384

    def test_non_draft_preserves_defaults(self):
        """create_job without draft keeps 30 steps and original resolution."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="test",
            width=1024,
            height=1024,
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert job.width == 1024
        assert job.height == 1024
        assert job.num_inference_steps == 30

    def test_sync_generate_passes_num_inference_steps(self):
        """_sync_generate passes num_inference_steps to the pipeline."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_output.images = [MagicMock()]
        mock_pipeline.return_value = mock_output

        _sync_generate(
            pipeline=mock_pipeline,
            prompt="test",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=1,
            seed=42,
            num_inference_steps=10,
        )

        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["num_inference_steps"] == 10

    @pytest.mark.asyncio
    async def test_run_job_passes_num_inference_steps(self, project_root: Path):
        """run_job passes num_inference_steps through to generate()."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1",
            task_id="t1",
            prompt="draft test",
            width=1024,
            height=1024,
            draft=True,
        )

        mock_round = MagicMock()
        mock_round.images = []

        mock_entry = ModelRegistryEntry(
            id="test-model",
            name="Test",
            provider_type=ProviderType.huggingface,
            model_identifier="test/model",
            file_path="/fake/path",
        )

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=mock_entry,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "pct.imagegen.job_manager.generate",
            new_callable=AsyncMock,
            return_value=mock_round,
        ) as mock_generate, patch(
            "pct.imagegen.job_manager.ensure_model_ready",
            new_callable=AsyncMock,
            side_effect=lambda entry, *a, **kw: entry,
        ):
            await manager.run_job(job_id, project_root)

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["num_inference_steps"] == 10
        assert call_kwargs["width"] == 512
        assert call_kwargs["height"] == 512


class TestPerImageCallback:
    def test_callback_called_for_each_image(self):
        """per_image_callback is called once per image with (pil_image, seed, index)."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_pil_image = MagicMock()
        mock_output.images = [mock_pil_image]
        mock_pipeline.return_value = mock_output

        calls: list[tuple] = []

        def on_image(pil_img, seed, idx):
            calls.append((pil_img, seed, idx))

        results = _sync_generate(
            pipeline=mock_pipeline,
            prompt="test",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=3,
            seed=100,
            per_image_callback=on_image,
        )

        assert len(results) == 3
        assert len(calls) == 3
        # Verify indices are sequential
        assert [c[2] for c in calls] == [0, 1, 2]
        # Verify seeds match results
        assert [c[1] for c in calls] == [r[1] for r in results]
        # Verify PIL images match
        for call, result in zip(calls, results):
            assert call[0] is result[0]

    def test_callback_not_called_when_none(self):
        """per_image_callback=None (default) does not crash."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_output.images = [MagicMock()]
        mock_pipeline.return_value = mock_output

        results = _sync_generate(
            pipeline=mock_pipeline,
            prompt="test",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=2,
            seed=42,
        )

        assert len(results) == 2


class TestCancellation:
    def test_cancel_event_stops_sync_generate_between_images(self):
        """_sync_generate raises GenerationCancelled when cancel_event is set."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_output.images = [MagicMock()]
        mock_pipeline.return_value = mock_output

        # Set the cancel event immediately — should stop before generating
        cancel_event = threading.Event()
        cancel_event.set()

        with pytest.raises(GenerationCancelled):
            _sync_generate(
                pipeline=mock_pipeline,
                prompt="test",
                negative_prompt=None,
                guidance_scale=7.5,
                num_images=4,
                seed=42,
                cancel_event=cancel_event,
            )

        # Pipeline should never have been called
        mock_pipeline.assert_not_called()

    def test_cancel_event_stops_after_first_image(self):
        """cancel_event set after first image stops before second."""
        call_count = 0

        def fake_pipeline(**kwargs):
            nonlocal call_count
            call_count += 1
            # Set cancel after first call
            if call_count == 1:
                cancel_event.set()
            output = MagicMock()
            output.images = [MagicMock()]
            return output

        cancel_event = threading.Event()

        with pytest.raises(GenerationCancelled):
            _sync_generate(
                pipeline=fake_pipeline,
                prompt="test",
                negative_prompt=None,
                guidance_scale=7.5,
                num_images=4,
                seed=42,
                cancel_event=cancel_event,
            )

        # Only one image generated before cancel was checked
        assert call_count == 1

    def test_no_cancel_event_generates_all(self):
        """Without cancel_event, all images are generated normally."""
        mock_pipeline = MagicMock()
        mock_output = MagicMock()
        mock_output.images = [MagicMock()]
        mock_pipeline.return_value = mock_output

        results = _sync_generate(
            pipeline=mock_pipeline,
            prompt="test",
            negative_prompt=None,
            guidance_scale=7.5,
            num_images=3,
            seed=42,
            cancel_event=None,
        )

        assert len(results) == 3
        assert mock_pipeline.call_count == 3

    def test_cancel_job_sets_event_and_status(self):
        """cancel_job sets the cancel_event and marks job as failed."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )
        job = manager.get_job(job_id)
        assert job is not None
        assert not job.cancel_event.is_set()

        manager.set_running(job_id)
        ok = manager.cancel_job(job_id)

        assert ok
        assert job.cancel_event.is_set()
        assert job.status == JobStatus.failed
        assert job.error == "Cancelled"

    def test_cancel_job_cancels_registered_task(self):
        """cancel_job cancels the registered asyncio task."""
        import asyncio

        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )

        # Create a mock task
        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = False
        manager.register_task(job_id, mock_task)

        manager.set_running(job_id)
        manager.cancel_job(job_id)

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_job_skips_completed_when_cancelled(self, project_root: Path):
        """run_job does not overwrite cancelled status with completed."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )

        mock_round = MagicMock()
        mock_round.images = []

        mock_entry = ModelRegistryEntry(
            id="test-model",
            name="Test",
            provider_type=ProviderType.huggingface,
            model_identifier="test/model",
            file_path="/fake/path",
        )

        async def fake_generate(**kwargs):
            # Simulate cancel happening during generation
            job = manager.get_job(job_id)
            job.cancel_event.set()
            return mock_round

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=mock_entry,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "pct.imagegen.job_manager.generate",
            new_callable=AsyncMock,
            side_effect=fake_generate,
        ), patch(
            "pct.imagegen.job_manager.ensure_model_ready",
            new_callable=AsyncMock,
            side_effect=lambda entry, *a, **kw: entry,
        ):
            await manager.run_job(job_id, project_root)

        job = manager.get_job(job_id)
        assert job is not None
        # Should NOT be completed — cancel_event was set
        assert job.status != JobStatus.completed

    @pytest.mark.asyncio
    async def test_run_job_handles_generation_cancelled(self, project_root: Path):
        """run_job handles GenerationCancelled from the generation thread."""
        manager = JobManager()
        job_id = manager.create_job(
            feature_id="f1", task_id="t1", prompt="test"
        )

        mock_entry = ModelRegistryEntry(
            id="test-model",
            name="Test",
            provider_type=ProviderType.huggingface,
            model_identifier="test/model",
            file_path="/fake/path",
        )

        with patch(
            "pct.imagegen.job_manager._resolve_model",
            return_value=mock_entry,
        ), patch(
            "pct.imagegen.job_manager.ensure_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ), patch(
            "pct.imagegen.job_manager.generate",
            new_callable=AsyncMock,
            side_effect=GenerationCancelled(),
        ), patch(
            "pct.imagegen.job_manager.ensure_model_ready",
            new_callable=AsyncMock,
            side_effect=lambda entry, *a, **kw: entry,
        ):
            # Should not raise
            await manager.run_job(job_id, project_root)

        job = manager.get_job(job_id)
        assert job is not None
        # GenerationCancelled is caught — job not marked as completed
        assert job.status != JobStatus.completed
