"""FastAPI application — entry point."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pct.agent.model_downloader import sync_hf_download_status
from pct.auth.dependencies import get_settings
from pct.auth.router import router as auth_router
from pct.auth.service import init_user_store
from pct.board.router import router as board_router
from pct.chat.router import router as chat_router
from pct.imagegen.registry_scan import rescan_imagegen_metadata
from pct.imagegen.router import router as imagegen_router
from pct.notifications.router import router as notifications_router
from pct.settings.router import router as settings_router
from pct.training.router import router as training_router


class InterceptHandler(logging.Handler):
    """Route stdlib logging (uvicorn, fastapi) into loguru."""

    def emit(self, record):
        level = logger.level(record.levelname).name
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(log_level: str):
    pass  # TODO: re-enable loguru once we have a better solution for the logging configuration (e.g. via settings file or env vars)
    # logger.remove()
    # logger.add(
    #     sys.stderr,
    #     level=log_level,
    #     format="{time:YYYY-MM-DD HH:mm:ss} {name} {level} {message}",
    # )
    # logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("PCT_ROOT = {}", settings.root.resolve())
    logger.info("PCT_PROJECT_ROOT = {}", settings.project_root.resolve())
    logger.info("PCT_GLOBAL_CONFIG_DIR = {}", settings.global_config_dir.resolve())
    if settings.hf_token:
        logger.info("PCT_HF_TOKEN = configured")
    else:
        logger.warning(
            "PCT_HF_TOKEN not set — HuggingFace downloads will be anonymous. "
            "This is fine for public models, but gated models (e.g. Stable Diffusion) "
            "require a token. Set PCT_HF_TOKEN in .env or your environment."
        )
    init_user_store(settings.global_config_dir)

    # Sync model registry with disk: file presence (download_status) and
    # imagegen metadata (architecture, native_resolution). Both are cheap
    # — they only rewrite the YAML when something actually changes.
    try:
        sync_hf_download_status(settings.global_config_dir)
    except Exception as e:
        logger.warning("Failed to sync HF download status: {}", e)
    try:
        changed = rescan_imagegen_metadata(settings.global_config_dir)
        if changed:
            logger.info(
                "Rescanned imagegen registry: {} entries updated", changed,
            )
    except Exception as e:
        logger.warning("Failed to rescan imagegen registry: {}", e)

    yield
    # Shutdown


app = FastAPI(title="PCT", version="0.1.0", lifespan=lifespan)

# CORS — permissive for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(board_router)
app.include_router(chat_router)
app.include_router(imagegen_router)
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(training_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
