"""Application configuration — pydantic-settings, .env, PCT_ prefix."""

import secrets
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings loaded from environment / .env file."""

    model_config = {"env_prefix": "PCT_", "env_file": ".env", "extra": "ignore"}

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Auth
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Project root — where pct.yaml lives
    project_root: Path = Field(default_factory=lambda: Path.cwd())

    # PCT deployment directory ($PCT_ROOT) — product install root (backend/..)
    root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent)

    # Global registry dir (~/.pct)
    global_config_dir: Path = Field(default_factory=lambda: Path.home() / ".pct")

    # Debug
    debug: bool = False
    log_level: str = "DEBUG"


# Module-level singleton — lazily instantiated
settings = Settings()


def set_settings(new_settings: Settings) -> None:
    """Replace the global settings instance (used by tests)."""
    global settings
    settings = new_settings
