"""Integration tests for Candidate Profile management."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_and_update_profile(client: AsyncClient):
    # Register candidate
    reg_payload = {
        "full_name": "Profile Candidate",
        "email": "profile@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /me (Unauthenticated fails)
    res_unauth = await client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401

    # 2. GET /me (Authenticated succeeds)
    res_auth = await client.get("/api/v1/auth/me", headers=headers)
    assert res_auth.status_code == 200
    profile = res_auth.json()
    assert profile["email"] == "profile@example.com"
    assert profile["target_role"] is None

    # 3. PUT /me (Update onboarding details)
    update_payload = {
        "full_name": "Updated Name",
        "target_role": "Backend Architect",
        "experience_level": "senior",
        "bio": "Experienced architect with 10 years in distributed systems.",
    }
    res_put = await client.put("/api/v1/auth/me", json=update_payload, headers=headers)
    assert res_put.status_code == 200
    updated = res_put.json()
    assert updated["full_name"] == "Updated Name"
    assert updated["target_role"] == "Backend Architect"
    assert updated["experience_level"] == "senior"
    assert updated["bio"] == "Experienced architect with 10 years in distributed systems."


@pytest.mark.asyncio
async def test_update_profile_invalid_experience_level_fails(client: AsyncClient):
    reg_payload = {
        "full_name": "Candidate Tier Test",
        "email": "tier@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "experience_level": "grandmaster",  # Invalid tier
    }
    res_invalid = await client.put("/api/v1/auth/me", json=update_payload, headers=headers)
    assert res_invalid.status_code == 422
