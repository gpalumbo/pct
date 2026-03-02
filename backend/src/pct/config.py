"""Application configuration — pydantic-settings, .env, PCT_ prefix."""

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
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Project root — where pct.yaml lives
    project_root: Path = Field(default_factory=lambda: Path.cwd())

    # Global registry dir
    global_config_dir: Path = Field(default_factory=lambda: Path.home() / ".pct")

    # Debug
    debug: bool = False
    log_level: str = "INFO"
