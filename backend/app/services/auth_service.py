"""Authentication and session lifecycle business logic."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import UserRegisterRequest


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime object is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AuthService:
    """Service handling registration, authentication, token rotation, and sessions."""

    @staticmethod
    async def register_user(
        db: AsyncSession, register_data: UserRegisterRequest
    ) -> Tuple[User, str, str]:
        """Register a new candidate, hash password with bcrypt, and issue initial session tokens."""
        stmt = select(User).where(User.email == register_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictError(
                message="An account with this email address already exists.",
                error_code="EMAIL_ALREADY_EXISTS",
            )

        hashed_pw = hash_password(register_data.password)
        user = User(
            email=register_data.email,
            hashed_password=hashed_pw,
            full_name=register_data.full_name,
            auth_provider="local",
        )
        db.add(user)
        await db.flush()

        access_token = create_access_token(subject=user.id)
        raw_refresh_token = generate_secure_token(32)
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False,
        )
        db.add(refresh_token_record)
        await db.commit()
        await db.refresh(user)

        return user, access_token, raw_refresh_token

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Tuple[User, str, str]:
        """Authenticate user credentials with brute-force delay, 15-minute temporary lockout, and generic error responses."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        # 1. Check active lockout
        if user and user.lockout_until:
            lockout_time = ensure_utc(user.lockout_until)
            if lockout_time and now < lockout_time:
                raise UnauthorizedError(
                    message="Invalid email or password.",
                    error_code="ACCOUNT_LOCKED",
                )
            else:
                user.lockout_until = None
                user.failed_login_attempts = 0

        # 2. Verify password
        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.lockout_until = now + timedelta(minutes=15)
                await db.commit()
                if user.failed_login_attempts >= 3:
                    await asyncio.sleep(2)
            else:
                await asyncio.sleep(0.05)

            raise UnauthorizedError(
                message="Invalid email or password.",
                error_code="INVALID_CREDENTIALS",
            )

        # 3. Successful authentication: reset failure counters
        user.failed_login_attempts = 0
        user.lockout_until = None

        access_token = create_access_token(subject=user.id)
        raw_refresh_token = generate_secure_token(32)
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False,
        )
        db.add(refresh_token_record)
        await db.commit()
        await db.refresh(user)

        return user, access_token, raw_refresh_token

    @staticmethod
    async def rotate_refresh_token(
        db: AsyncSession, raw_refresh_token: str
    ) -> Tuple[User, str, str]:
        """Execute single-use token rotation: revoke used token, store new SHA-256 hash, issue fresh access token."""
        if not raw_refresh_token:
            raise UnauthorizedError(
                message="Refresh token was not provided.",
                error_code="MISSING_REFRESH_TOKEN",
            )

        token_digest = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_digest)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not token_record or token_record.revoked:
            raise UnauthorizedError(
                message="Invalid or expired refresh token. Please sign in again.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        expires_at = ensure_utc(token_record.expires_at)
        if expires_at and expires_at <= now:
            raise UnauthorizedError(
                message="Invalid or expired refresh token. Please sign in again.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        # 1. Invalidate old token
        token_record.revoked = True

        # 2. Fetch candidate user
        user_stmt = select(User).where(
            User.id == token_record.user_id, User.is_active.is_(True)
        )
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise UnauthorizedError(
                message="Candidate account not found or deactivated.",
                error_code="USER_NOT_FOUND",
            )

        # 3. Issue fresh access token and new refresh token
        new_access_token = create_access_token(subject=user.id)
        new_raw_refresh_token = generate_secure_token(32)
        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_raw_refresh_token),
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            revoked=False,
        )
        db.add(new_token_record)
        await db.commit()
        await db.refresh(user)

        return user, new_access_token, new_raw_refresh_token

    @staticmethod
    async def logout_user(
        db: AsyncSession, raw_refresh_token: Optional[str]
    ) -> None:
        """Revoke refresh token record in database upon candidate logout."""
        if not raw_refresh_token:
            return

        token_digest = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_digest)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        if token_record and not token_record.revoked:
            token_record.revoked = True
            await db.commit()
