"""Integration tests for Password Reset Flow and Session Invalidation."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token
from app.models.user import PasswordResetToken, User


@pytest.mark.asyncio
async def test_password_reset_lifecycle_and_session_revocation(
    client: AsyncClient, db_session: AsyncSession
):
    email = "reset_user@example.com"
    old_password = "initial-password-min-12-chars"
    new_password = "updated-secure-password-12345"

    # 1. Register candidate and get refresh cookie
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Reset Candidate", "email": email, "password": old_password},
    )
    assert reg_res.status_code == 201
    old_refresh_cookie = reg_res.cookies.get("refresh_token")

    # 2. Request password reset (Generates token in DB, returns generic message)
    req_res = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": email},
    )
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert "token" not in str(req_data)
    assert "If an account with that email exists" in req_data["message"]

    # 3. Retrieve raw token from test DB (by fetching the record and testing verify)
    stmt = (
        select(PasswordResetToken)
        .join(User)
        .where(User.email == email, PasswordResetToken.used.is_(False))
    )
    res_tokens = await db_session.execute(stmt)
    active_token_record = res_tokens.scalar_one_or_none()
    assert active_token_record is not None

    # Test token invalidation when requesting second reset
    req_res_2 = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": email},
    )
    assert req_res_2.status_code == 200

    # Old token record should now be marked used/invalidated
    await db_session.refresh(active_token_record)
    assert active_token_record.used is True

    # 4. Insert a known raw token into DB for confirmation testing
    raw_test_token = "test-32-byte-password-reset-token-sample"
    user_stmt = select(User).where(User.email == email)
    user_res = await db_session.execute(user_stmt)
    user = user_res.scalar_one()

    test_reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_test_token),
        used=False,
    )
    # The default expires_at is handled, but let's ensure it's set
    from datetime import datetime, timedelta, timezone
    test_reset_record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    db_session.add(test_reset_record)
    await db_session.commit()

    # 5. Confirm password reset
    confirm_res = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_test_token, "new_password": new_password},
    )
    assert confirm_res.status_code == 200
    assert "Password has been reset successfully" in confirm_res.json()["message"]

    # 6. Reusing same token should fail
    replay_confirm = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_test_token, "new_password": "another-new-password-1234"},
    )
    assert replay_confirm.status_code == 400
    assert replay_confirm.json()["error_code"] == "INVALID_RESET_TOKEN"

    # 7. Old password fails login, new password succeeds
    login_old = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login_old.status_code == 401

    login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert login_new.status_code == 200

    # 8. Old refresh token before password reset was revoked
    client.cookies.set("refresh_token", old_refresh_cookie, path="/api/v1/auth")
    ref_after_reset = await client.post("/api/v1/auth/refresh")
    assert ref_after_reset.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_unknown_email_enumeration_defense(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nonexistent_reset@example.com"},
    )
    assert response.status_code == 200
    assert "If an account with that email exists" in response.json()["message"]
