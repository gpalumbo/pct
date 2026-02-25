"""PCT Backend Configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The backend package lives at backend/src/pct/; two parents up from this
# file's directory gives us the backend/ dir, one more gives the repo root.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/src/pct → backend/
_DEFAULT_ROOT = str(_BACKEND_DIR.parent)  # backend/ → repo root


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origin: str = "http://localhost:5173"

    # Auth
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    google_client_id: str = ""

    # Storage
    user_data_dir: str = ""

    # Project
    project_root: str = ""
    registries_dir: str = ""
    root: str = _DEFAULT_ROOT

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PCT_")


settings: Settings = Settings()
