"""PCT Backend - FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pct import config
from pct.auth.router import router as auth_router


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


@app.get("/api/health")
async def health():
    """Health check endpoint. Returns when the server is ready."""
    return {"status": "ok", "version": "0.1.0"}
