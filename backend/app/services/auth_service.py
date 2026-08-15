"""Authentication and session lifecycle business logic."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    UnauthorizedError,
    ValidationError,
)
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import (
    PasswordResetToken,
    RefreshToken,
    User,
    UserOAuthIdentity,
)
from app.schemas.auth import UserProfileUpdateRequest, UserRegisterRequest


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime object is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AuthService:
    """Service handling registration, authentication, token rotation, OAuth, profile, and password reset."""

    @staticmethod
    def verify_google_id_token(token: str) -> dict:
        """Verify Google Identity Services ID token signature, audience, issuer, and claims."""
        if not settings or not settings.GOOGLE_CLIENT_ID:
            raise AppError(
                message="Google Sign-In is not configured on this server.",
                status_code=500,
                error_code="GOOGLE_AUTH_UNCONFIGURED",
            )

        try:
            id_info = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except Exception as e:
            raise ValidationError(
                message=f"Invalid Google ID token signature or expired: {e}",
                error_code="INVALID_GOOGLE_TOKEN",
            )

        issuer = id_info.get("iss")
        if issuer not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValidationError(
                message="Invalid Google token issuer.",
                error_code="INVALID_GOOGLE_ISSUER",
            )

        if not id_info.get("sub"):
            raise ValidationError(
                message="Google ID token missing subject claim.",
                error_code="INVALID_GOOGLE_SUB",
            )

        if not id_info.get("email"):
            raise ValidationError(
                message="Google ID token missing email address.",
                error_code="INVALID_GOOGLE_EMAIL",
            )

        if not id_info.get("email_verified", False):
            raise ValidationError(
                message="Google email address has not been verified.",
                error_code="UNVERIFIED_GOOGLE_EMAIL",
            )

        return id_info

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
    async def authenticate_google_user(
        db: AsyncSession, id_token: str
    ) -> Tuple[User, str, str]:
        """Authenticate or register candidate via Google OAuth2 ID Token with anti-silent account linking."""
        id_info = AuthService.verify_google_id_token(id_token)
        provider_sub = str(id_info["sub"])
        provider_email = str(id_info["email"]).lower()
        provider_name = id_info.get("name") or provider_email.split("@")[0]

        now = datetime.now(timezone.utc)

        # 1. Check if OAuth identity is already linked
        stmt = select(UserOAuthIdentity).where(
            UserOAuthIdentity.provider == "google",
            UserOAuthIdentity.provider_user_id == provider_sub,
        )
        result = await db.execute(stmt)
        oauth_identity = result.scalar_one_or_none()

        if oauth_identity:
            user_stmt = select(User).where(
                User.id == oauth_identity.user_id, User.is_active.is_(True)
            )
            user_res = await db.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            if not user:
                raise UnauthorizedError(
                    message="Candidate account not found or deactivated.",
                    error_code="USER_NOT_FOUND",
                )
        else:
            # 2. Check collision with existing password account
            user_stmt = select(User).where(User.email == provider_email)
            user_res = await db.execute(user_stmt)
            existing_user = user_res.scalar_one_or_none()

            if existing_user:
                raise ValidationError(
                    message="This email is already registered with a password. Please sign in with your password first to link your Google account.",
                    error_code="ACCOUNT_LINKING_REQUIRED",
                )

            # 3. Create new user and OAuth identity
            user = User(
                email=provider_email,
                full_name=provider_name,
                auth_provider="google",
            )
            db.add(user)
            await db.flush()

            oauth_record = UserOAuthIdentity(
                user_id=user.id,
                provider="google",
                provider_user_id=provider_sub,
                provider_email=provider_email,
            )
            db.add(oauth_record)

        # Issue session tokens
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
    async def link_google_account(
        db: AsyncSession, current_user: User, id_token: str
    ) -> User:
        """Explicitly link a Google OAuth identity to an authenticated candidate account."""
        id_info = AuthService.verify_google_id_token(id_token)
        provider_sub = str(id_info["sub"])
        provider_email = str(id_info["email"]).lower()

        stmt = select(UserOAuthIdentity).where(
            UserOAuthIdentity.provider == "google",
            UserOAuthIdentity.provider_user_id == provider_sub,
        )
        result = await db.execute(stmt)
        existing_identity = result.scalar_one_or_none()

        if existing_identity:
            if existing_identity.user_id == current_user.id:
                return current_user
            raise ConflictError(
                message="This Google identity is already linked to another candidate account.",
                error_code="OAUTH_IDENTITY_ALREADY_LINKED",
            )

        new_identity = UserOAuthIdentity(
            user_id=current_user.id,
            provider="google",
            provider_user_id=provider_sub,
            provider_email=provider_email,
        )
        db.add(new_identity)
        await db.commit()
        await db.refresh(current_user)
        return current_user

    @staticmethod
    async def update_user_profile(
        db: AsyncSession, current_user: User, update_data: UserProfileUpdateRequest
    ) -> User:
        """Update candidate career profile details."""
        if update_data.full_name is not None:
            current_user.full_name = update_data.full_name
        if update_data.target_role is not None:
            current_user.target_role = update_data.target_role
        if update_data.experience_level is not None:
            current_user.experience_level = update_data.experience_level
        if update_data.bio is not None:
            current_user.bio = update_data.bio

        await db.commit()
        await db.refresh(current_user)
        return current_user

    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> None:
        """Dispatch password reset token: invalidate previous tokens and log reset link in development."""
        stmt = select(User).where(User.email == email, User.is_active.is_(True))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # 1. Invalidate any prior active reset tokens for this user
            prev_stmt = select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used.is_(False),
            )
            prev_result = await db.execute(prev_stmt)
            for prev_token in prev_result.scalars().all():
                prev_token.used = True

            # 2. Issue new high-entropy reset token
            raw_token = generate_secure_token(32)
            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                used=False,
            )
            db.add(reset_record)
            await db.commit()

            # 3. Log dev link
            if settings and settings.ENVIRONMENT in ("development", "testing"):
                logger.info(
                    "PASSWORD RESET LINK (DEV): http://localhost:5173/reset-password?token=%s",
                    raw_token,
                )

    @staticmethod
    async def confirm_password_reset(
        db: AsyncSession, token: str, new_password: str
    ) -> None:
        """Verify reset token hash, update bcrypt password, revoke refresh tokens, and mark token used."""
        token_digest = hash_token(token)
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_digest
        )
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not token_record or token_record.used:
            raise ValidationError(
                message="Invalid or expired password reset token.",
                error_code="INVALID_RESET_TOKEN",
            )

        expires_at = ensure_utc(token_record.expires_at)
        if expires_at and expires_at <= now:
            raise ValidationError(
                message="Invalid or expired password reset token.",
                error_code="INVALID_RESET_TOKEN",
            )

        # 1. Mark reset token as used
        token_record.used = True

        # 2. Update user password
        user_stmt = select(User).where(User.id == token_record.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise ValidationError(
                message="Candidate user account not found.",
                error_code="USER_NOT_FOUND",
            )

        user.hashed_password = hash_password(new_password)
        user.failed_login_attempts = 0
        user.lockout_until = None

        # 3. Revoke all existing refresh sessions for this user
        ref_stmt = select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
        )
        ref_result = await db.execute(ref_stmt)
        for ref_tok in ref_result.scalars().all():
            ref_tok.revoked = True

        await db.commit()

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
