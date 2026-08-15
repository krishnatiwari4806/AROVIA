"""Integration tests for Google OAuth2 ID Token Verification and Explicit Account Linking."""

from unittest.mock import patch
import pytest
from httpx import AsyncClient
from google.oauth2 import id_token as google_id_token

from app.core.config import settings


@pytest.mark.asyncio
async def test_google_auth_missing_client_id_fails(client: AsyncClient):
    with patch.object(settings, "GOOGLE_CLIENT_ID", None):
        response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "dummy-token"},
        )
        assert response.status_code == 500
        assert response.json()["error_code"] == "GOOGLE_AUTH_UNCONFIGURED"


@pytest.mark.asyncio
async def test_google_auth_invalid_signature(client: AsyncClient):
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        with patch.object(
            google_id_token,
            "verify_oauth2_token",
            side_effect=ValueError("Invalid token signature"),
        ):
            response = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "invalid-signature-token"},
            )
            assert response.status_code == 400
            assert response.json()["error_code"] == "INVALID_GOOGLE_TOKEN"


@pytest.mark.asyncio
async def test_google_auth_invalid_issuer(client: AsyncClient):
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        with patch.object(
            google_id_token,
            "verify_oauth2_token",
            return_value={
                "iss": "invalid-issuer.com",
                "sub": "12345",
                "email": "user@example.com",
                "email_verified": True,
            },
        ):
            response = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "bad-issuer-token"},
            )
            assert response.status_code == 400
            assert response.json()["error_code"] == "INVALID_GOOGLE_ISSUER"


@pytest.mark.asyncio
async def test_google_auth_unverified_email(client: AsyncClient):
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        with patch.object(
            google_id_token,
            "verify_oauth2_token",
            return_value={
                "iss": "accounts.google.com",
                "sub": "12345",
                "email": "unverified@example.com",
                "email_verified": False,
            },
        ):
            response = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "unverified-token"},
            )
            assert response.status_code == 400
            assert response.json()["error_code"] == "UNVERIFIED_GOOGLE_EMAIL"


@pytest.mark.asyncio
async def test_google_auth_successful_signup_and_subsequent_login(client: AsyncClient):
    mock_payload = {
        "iss": "https://accounts.google.com",
        "sub": "google-unique-sub-1001",
        "email": "google_candidate@example.com",
        "name": "Google Candidate",
        "email_verified": True,
    }

    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        with patch.object(
            google_id_token, "verify_oauth2_token", return_value=mock_payload
        ):
            # 1. First Sign-In (Creates account)
            res1 = await client.post(
                "/api/v1/auth/google", json={"id_token": "valid-google-jwt-token"}
            )
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["user"]["email"] == "google_candidate@example.com"
            assert data1["user"]["auth_provider"] == "google"
            assert "access_token" in data1
            assert "refresh_token" in res1.cookies

            # 2. Subsequent Sign-In (Authenticates existing account)
            res2 = await client.post(
                "/api/v1/auth/google", json={"id_token": "valid-google-jwt-token"}
            )
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["user"]["id"] == data1["user"]["id"]


@pytest.mark.asyncio
async def test_google_auth_account_collision_requires_linking(client: AsyncClient):
    # 1. Register with email/password
    reg_payload = {
        "full_name": "Local Account User",
        "email": "collision_candidate@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # 2. Attempt Google Sign-In with same email (without prior linking)
    mock_payload = {
        "iss": "accounts.google.com",
        "sub": "google-sub-2002",
        "email": "collision_candidate@example.com",
        "name": "Collision User",
        "email_verified": True,
    }
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        with patch.object(
            google_id_token, "verify_oauth2_token", return_value=mock_payload
        ):
            google_res = await client.post(
                "/api/v1/auth/google", json={"id_token": "token-with-collision"}
            )
            assert google_res.status_code == 400
            assert google_res.json()["error_code"] == "ACCOUNT_LINKING_REQUIRED"


@pytest.mark.asyncio
async def test_google_auth_explicit_authenticated_linking(client: AsyncClient):
    # 1. Register and get token
    reg_payload = {
        "full_name": "Link Candidate",
        "email": "link_candidate@example.com",
        "password": "valid-passphrase-with-min-12-chars",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    access_token = reg_res.json()["access_token"]

    # 2. Explicitly link Google identity
    mock_payload = {
        "iss": "accounts.google.com",
        "sub": "google-sub-3003",
        "email": "link_candidate@example.com",
        "name": "Link Candidate",
        "email_verified": True,
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id.apps.googleusercontent.com"):
        with patch.object(
            google_id_token, "verify_oauth2_token", return_value=mock_payload
        ):
            link_res = await client.post(
                "/api/v1/auth/google/link",
                json={"id_token": "valid-link-token"},
                headers=headers,
            )
            assert link_res.status_code == 200
            assert link_res.json()["email"] == "link_candidate@example.com"

            # 3. Now Google Sign-In succeeds directly
            subsequent_google = await client.post(
                "/api/v1/auth/google", json={"id_token": "valid-link-token"}
            )
            assert subsequent_google.status_code == 200
            assert subsequent_google.json()["user"]["email"] == "link_candidate@example.com"
