"""Integration tests for Token Refresh Rotation, Cookie Attributes, and Logout."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_silent_refresh_and_cookie_attributes(client: AsyncClient):
    # Register candidate
    reg_payload = {
        "full_name": "Rotation Candidate",
        "email": "rotation@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    old_refresh_cookie = reg_res.cookies.get("refresh_token")
    assert old_refresh_cookie is not None

    # Call /refresh with cookie
    client.cookies.set("refresh_token", old_refresh_cookie, path="/api/v1/auth")
    ref_res = await client.post("/api/v1/auth/refresh")

    assert ref_res.status_code == 200
    data = ref_res.json()
    assert "access_token" in data
    new_refresh_cookie = ref_res.cookies.get("refresh_token")
    assert new_refresh_cookie is not None
    assert new_refresh_cookie != old_refresh_cookie

    # Validate cookie security attributes
    set_cookie = ref_res.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie or "path=/api/v1/auth" in set_cookie
    assert "SameSite=lax" in set_cookie or "samesite=lax" in set_cookie
    assert "Max-Age=604800" in set_cookie or "max-age=604800" in set_cookie


@pytest.mark.asyncio
async def test_replay_of_revoked_refresh_token_fails(client: AsyncClient):
    # Register candidate
    reg_payload = {
        "full_name": "Replay Candidate",
        "email": "replay@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    first_cookie = reg_res.cookies.get("refresh_token")

    # First rotation (revokes first_cookie)
    client.cookies.set("refresh_token", first_cookie, path="/api/v1/auth")
    ref1 = await client.post("/api/v1/auth/refresh")
    assert ref1.status_code == 200

    # Replay first_cookie again (should be rejected as revoked)
    client.cookies.set("refresh_token", first_cookie, path="/api/v1/auth")
    replay_res = await client.post("/api/v1/auth/refresh")
    assert replay_res.status_code == 401
    assert replay_res.json()["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_logout_revokes_token_and_clears_cookie(client: AsyncClient):
    # Register
    reg_payload = {
        "full_name": "Logout Candidate",
        "email": "logout_candidate@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    cookie = reg_res.cookies.get("refresh_token")

    # Logout
    client.cookies.set("refresh_token", cookie, path="/api/v1/auth")
    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully."

    # Verify refresh attempt fails after logout
    client.cookies.set("refresh_token", cookie, path="/api/v1/auth")
    post_logout_ref = await client.post("/api/v1/auth/refresh")
    assert post_logout_ref.status_code == 401
