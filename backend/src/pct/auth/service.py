"""Auth service - JWT, password hashing, user storage."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
import jwt

from pct import config

ALGORITHM = "HS256"


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=config.settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, config.settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def _get_users_file() -> Path:
    base = Path(config.settings.user_data_dir) if config.settings.user_data_dir else Path.home() / ".pct" / "users"
    base.mkdir(parents=True, exist_ok=True)
    return base / "users.json"


def _load_users() -> dict:
    users_file = _get_users_file()
    if not users_file.exists():
        return {}
    with open(users_file) as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    users_file = _get_users_file()
    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)


def get_user(email: str) -> dict | None:
    users = _load_users()
    return users.get(email)


def create_user(email: str, hashed_password: str, auth_provider: str = "local") -> dict:
    users = _load_users()
    user = {
        "email": email,
        "hashed_password": hashed_password,
        "auth_provider": auth_provider,
        "created_at": datetime.now(UTC).isoformat(),
    }
    users[email] = user
    _save_users(users)
    return user
