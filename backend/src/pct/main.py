"""PCT Backend - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pct import config
from pct.auth.router import router as auth_router
from pct.chat.router import router as chat_router
from pct.settings.router import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PCT server starting up")
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
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(config_router, prefix="/api/config", tags=["config"])


@app.get("/api/health")
async def health():
    """Health check endpoint. Returns when the server is ready."""
    return {"status": "ok", "version": "0.1.0"}
