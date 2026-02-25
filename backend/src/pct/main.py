"""PCT Backend - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pct import config
from pct.auth.router import router as auth_router
from pct.board.router import router as board_router
from pct.chat.router import router as chat_router
from pct.imagegen.router import router as imagegen_router
from pct.settings.router import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.settings.project_root:
        raise RuntimeError(
            "PCT_PROJECT_ROOT is not set. "
            "Set it to the project directory you want to work on "
            "(e.g. PCT_PROJECT_ROOT=/path/to/my-project)."
        )
    logger.info(
        "PCT server starting up  project_root={} pct_root={}",
        config.settings.project_root,
        config.settings.root,
    )
    # Auto-discover models on every startup
    from pct.settings.service import scan_and_register_models
    found = scan_and_register_models()
    if found:
        logger.info("Discovered {} new model(s): {}", len(found), [m.id for m in found])
    yield
    logger.info("PCT server shutting down")


app = FastAPI(
    title="PCT",
    description="Project Curation Tool",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(board_router, prefix="/api/board", tags=["board"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(config_router, prefix="/api/config", tags=["config"])
app.include_router(imagegen_router, prefix="/api/imagegen", tags=["imagegen"])


@app.get("/api/health")
async def health():
    """Health check endpoint. Returns when the server is ready."""
    return {"status": "ok", "version": "0.1.0"}
