"""Auth service — password hashing, JWT tokens, and file-backed user store."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
import jwt

from pct.storage._atomic import atomic_write

# In-memory cache; optionally backed by a JSON file on disk.
_users: dict[str, str] = {}  # email -> hashed password
_users_file: Path | None = None  # set by init_user_store()


def init_user_store(global_config_dir: Path) -> None:
    """Load users from disk (called once at startup from lifespan)."""
    global _users, _users_file
    _users_file = global_config_dir / "users.json"
    if _users_file.exists():
        data = json.loads(_users_file.read_text(encoding="utf-8"))
        _users.clear()
        _users.update(data)
    else:
        _users.clear()


def _save_users() -> None:
    """Persist _users dict to disk (no-op when _users_file is None)."""
    if _users_file is None:
        return
    atomic_write(_users_file, json.dumps(_users, indent=2))


def set_users_file(path: Path | None) -> None:
    """Test helper — override or disable the users file path."""
    global _users_file
    _users_file = path


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(email: str, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 1440) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_token(token: str, secret_key: str, algorithm: str = "HS256") -> str | None:
    """Verify JWT and return email, or None if invalid."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def register_user(email: str, password: str) -> bool:
    """Register a new user. Returns False if email already exists."""
    if email in _users:
        return False
    _users[email] = hash_password(password)
    _save_users()
    return True


def authenticate_user(email: str, password: str) -> bool:
    """Check credentials. Returns True if valid."""
    hashed = _users.get(email)
    if hashed is None:
        return False
    return verify_password(password, hashed)


def get_users() -> dict[str, str]:
    """Get the user store (for testing)."""
    return _users


def clear_users() -> None:
    """Clear all users (for testing)."""
    _users.clear()
    _save_users()
