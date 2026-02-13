"""Integration test: full auth lifecycle with health check."""


async def test_full_auth_flow(client):
    """Test: health check -> register -> authenticated access -> login -> access."""
    # 1. Health check - server is ready
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # 2. Register a new user
    r = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "securepass123"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    # 3. Access protected endpoint with token
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"
    assert r.json()["auth_provider"] == "local"

    # 4. Unauthenticated access is rejected
    r = await client.get("/api/auth/me")
    assert r.status_code in (401, 403)

    # 5. Login with the same credentials
    r = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "securepass123"},
    )
    assert r.status_code == 200
    token2 = r.json()["access_token"]

    # 6. New token works
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"

    # 7. Duplicate registration is rejected
    r = await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "another"},
    )
    assert r.status_code == 400

    # 8. Wrong password is rejected
    r = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401

    # 9. Google auth returns 501 when not configured
    r = await client.post("/api/auth/google", json={"credential": "fake-token"})
    assert r.status_code == 501
