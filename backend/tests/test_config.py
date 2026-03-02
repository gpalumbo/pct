"""Tests for Settings configuration."""

from pathlib import Path

from pct.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.host == "127.0.0.1"
        assert s.port == 8000
        assert s.secret_key == "change-me-in-production"
        assert s.jwt_algorithm == "HS256"
        assert s.jwt_expire_minutes == 1440
        assert s.debug is False
        assert s.log_level == "INFO"

    def test_env_prefix(self, monkeypatch):
        monkeypatch.setenv("PCT_PORT", "9000")
        monkeypatch.setenv("PCT_DEBUG", "true")
        monkeypatch.setenv("PCT_LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.port == 9000
        assert s.debug is True
        assert s.log_level == "DEBUG"

    def test_project_root_default_is_cwd(self):
        s = Settings()
        assert isinstance(s.project_root, Path)

    def test_global_config_dir_default(self):
        s = Settings()
        assert s.global_config_dir == Path.home() / ".pct"

    def test_secret_key_from_env(self, monkeypatch):
        monkeypatch.setenv("PCT_SECRET_KEY", "my-secure-key")
        s = Settings()
        assert s.secret_key == "my-secure-key"

    def test_extra_env_vars_ignored(self, monkeypatch):
        monkeypatch.setenv("PCT_NONEXISTENT_FIELD", "value")
        s = Settings()  # Should not raise
        assert s.host == "127.0.0.1"
