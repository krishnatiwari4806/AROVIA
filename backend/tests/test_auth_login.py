"""Integration tests for Candidate Login, Account Lockout, and Enumeration Defense."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register candidate
    reg_payload = {
        "full_name": "Login User",
        "email": "login_user@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Login
    login_payload = {
        "email": "login_user@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_user@example.com"
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_enumeration_defense_and_bad_password(client: AsyncClient):
    # Register candidate
    reg_payload = {
        "full_name": "Registered User",
        "email": "registered@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # 1. Unknown email
    res_unknown = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "valid-passphrase-with-min-12-chars"},
    )
    assert res_unknown.status_code == 401
    assert res_unknown.json()["detail"] == "Invalid email or password."

    # 2. Known email + wrong password
    res_wrong_pw = await client.post(
        "/api/v1/auth/login",
        json={"email": "registered@example.com", "password": "wrong-password-here-123"},
    )
    assert res_wrong_pw.status_code == 401
    assert res_wrong_pw.json()["detail"] == "Invalid email or password."

    # Responses must be completely uniform
    assert res_unknown.json()["detail"] == res_wrong_pw.json()["detail"]


@pytest.mark.asyncio
async def test_consecutive_failed_logins_triggers_15min_lockout(client: AsyncClient):
    email = "lockout_candidate@example.com"
    reg_payload = {
        "full_name": "Lockout Candidate",
        "email": email,
        "password": "valid-passphrase-with-min-12-chars",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Trigger 5 failed logins
    for _ in range(5):
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "incorrect-password-test"},
        )
        assert res.status_code == 401

    # 6th attempt (even with CORRECT password) should be locked out
    locked_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "valid-passphrase-with-min-12-chars"},
    )
    assert locked_res.status_code == 401
    assert locked_res.json()["error_code"] == "ACCOUNT_LOCKED"
