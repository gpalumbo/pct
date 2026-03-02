"""Tests for auth service — hashing, JWT, user management."""

from pct.auth.service import (
    authenticate_user,
    clear_users,
    create_token,
    get_users,
    hash_password,
    init_user_store,
    register_user,
    set_users_file,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False


class TestJWT:
    def test_create_and_verify(self):
        token = create_token("test@example.com", "secret")
        email = verify_token(token, "secret")
        assert email == "test@example.com"

    def test_invalid_token(self):
        assert verify_token("not.a.token", "secret") is None

    def test_wrong_secret(self):
        token = create_token("test@example.com", "secret1")
        assert verify_token(token, "secret2") is None


class TestUserRegistration:
    def setup_method(self):
        set_users_file(None)
        clear_users()

    def test_register_and_authenticate(self):
        assert register_user("user@test.com", "pass123") is True
        assert authenticate_user("user@test.com", "pass123") is True

    def test_register_duplicate(self):
        register_user("dup@test.com", "pass")
        assert register_user("dup@test.com", "pass2") is False

    def test_authenticate_nonexistent(self):
        assert authenticate_user("nobody@test.com", "pass") is False

    def test_authenticate_wrong_password(self):
        register_user("user@test.com", "correct")
        assert authenticate_user("user@test.com", "wrong") is False


class TestUserPersistence:
    def setup_method(self):
        set_users_file(None)
        clear_users()

    def test_users_survive_reinit(self, tmp_path):
        """Register a user, re-init from same dir, verify login still works."""
        init_user_store(tmp_path)
        register_user("persist@test.com", "secret123")

        # Simulate server restart: clear in-memory only (don't persist the clear)
        get_users().clear()
        init_user_store(tmp_path)

        assert authenticate_user("persist@test.com", "secret123") is True

    def test_users_file_created(self, tmp_path):
        """Verify users.json is written to disk after registration."""
        init_user_store(tmp_path)
        register_user("file@test.com", "pw")

        users_file = tmp_path / "users.json"
        assert users_file.exists()

        import json

        data = json.loads(users_file.read_text(encoding="utf-8"))
        assert "file@test.com" in data

    def teardown_method(self):
        set_users_file(None)
        clear_users()
