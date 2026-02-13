"""Test configuration - sets env vars before importing pct modules."""

import os

# Set test env vars BEFORE any pct imports
os.environ["PCT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["PCT_GOOGLE_CLIENT_ID"] = ""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _isolate_users(tmp_path):
    """Give each test its own user data directory."""
    os.environ["PCT_USER_DATA_DIR"] = str(tmp_path)
    from pct import config

    config.settings = config.Settings()
    yield


@pytest.fixture
async def client():
    from pct.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
