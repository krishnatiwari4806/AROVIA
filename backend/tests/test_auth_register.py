"""Integration tests for Candidate Registration endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    payload = {
        "full_name": "Alexander Hamilton",
        "email": "alex@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    assert data["user"]["email"] == "alex@example.com"
    assert data["user"]["full_name"] == "Alexander Hamilton"
    assert data["user"]["auth_provider"] == "local"

    # Verify refresh token cookie
    assert "refresh_token" in response.cookies
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header
    assert "Path=/api/v1/auth" in set_cookie_header or "path=/api/v1/auth" in set_cookie_header
    assert "SameSite=lax" in set_cookie_header or "samesite=lax" in set_cookie_header


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {
        "full_name": "First User",
        "email": "duplicate_check@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["error_code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_short_password_fails(client: AsyncClient):
    payload = {
        "full_name": "Short Password User",
        "email": "short@example.com",
        "password": "too-short",  # < 12 chars
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_common_password_fails_even_if_12_chars(client: AsyncClient):
    payload = {
        "full_name": "Common Password User",
        "email": "common@example.com",
        "password": "password123456",  # 14 chars, but in COMMON_PASSWORDS
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "Password is too common" in str(data)
