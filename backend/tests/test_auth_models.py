"""Integration tests for User and Authentication ORM models."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserOAuthIdentity, RefreshToken, PasswordResetToken


@pytest.mark.asyncio
async def test_create_user_model(db_session: AsyncSession):
    user = User(
        email="candidate@example.com",
        hashed_password="bcrypt-hashed-string",
        full_name="Jane Doe",
        auth_provider="local",
        target_role="Full Stack Engineer",
        experience_level="mid",
        bio="Experienced engineer preparing for mock interviews",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "candidate@example.com"
    assert user.failed_login_attempts == 0
    assert user.is_active is True
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_user_unique_email(db_session: AsyncSession):
    user1 = User(
        email="duplicate@example.com",
        full_name="User One",
    )
    user2 = User(
        email="duplicate@example.com",
        full_name="User Two",
    )
    db_session.add(user1)
    await db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_user_cascade_deletes_child_tokens(db_session: AsyncSession):
    user = User(
        email="cascade_test@example.com",
        full_name="Cascade Candidate",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    oauth_id = UserOAuthIdentity(
        user_id=user.id,
        provider="google",
        provider_user_id="google-sub-9999",
        provider_email="cascade_test@example.com",
    )
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="sha256-dummy-hash-123456",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash="sha256-reset-hash-654321",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db_session.add_all([oauth_id, refresh_token, reset_token])
    await db_session.commit()

    # Verify children exist
    q_oauth = await db_session.execute(
        select(UserOAuthIdentity).where(UserOAuthIdentity.user_id == user.id)
    )
    assert q_oauth.scalar_one_or_none() is not None

    # Delete parent user
    await db_session.delete(user)
    await db_session.commit()

    # Verify children are cascaded
    q_oauth_after = await db_session.execute(
        select(UserOAuthIdentity).where(UserOAuthIdentity.user_id == user.id)
    )
    assert q_oauth_after.scalar_one_or_none() is None

    q_refresh_after = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    assert q_refresh_after.scalar_one_or_none() is None

    q_reset_after = await db_session.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    assert q_reset_after.scalar_one_or_none() is None
