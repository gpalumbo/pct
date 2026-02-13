"""PCT Backend Configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PCT_")


settings: Settings = Settings()
