"""FastAPI application — entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pct.auth.dependencies import get_settings
from pct.auth.router import router as auth_router
from pct.auth.service import init_user_store
from pct.board.router import router as board_router
from pct.chat.router import router as chat_router
from pct.imagegen.router import router as imagegen_router
from pct.notifications.router import router as notifications_router
from pct.settings.router import router as settings_router
from pct.training.router import router as training_router

logger = logging.getLogger("pct")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    logger.info("PCT_PROJECT_ROOT = %s", settings.project_root.resolve())
    logger.info("PCT_GLOBAL_CONFIG_DIR = %s", settings.global_config_dir.resolve())
    init_user_store(settings.global_config_dir)
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
