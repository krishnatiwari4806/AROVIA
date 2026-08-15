"""Authentication, OAuth, Profile Management, and Password Reset REST API endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccountLinkConfirmRequest,
    GoogleAuthRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set HttpOnly, SameSite=Lax refresh cookie scoped to auth API routes."""
    is_secure = False
    if settings and settings.ENVIRONMENT not in ("development", "testing"):
        is_secure = True

    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=604800,  # 7 days in seconds
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clear HttpOnly refresh cookie upon logout."""
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new candidate account",
)
@limiter.limit("3/minute")
async def register(
    request: Request,
    register_data: UserRegisterRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a candidate with email and passphrase, returning access token and setting refresh cookie."""
    user, access_token, raw_refresh_token = await AuthService.register_user(
        db, register_data
    )
    set_refresh_cookie(response, raw_refresh_token)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate candidate credentials",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: UserLoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate candidate email and password with brute-force delay and 15-minute temporary lockout defense."""
    user, access_token, raw_refresh_token = await AuthService.authenticate_user(
        db, login_data.email, login_data.password
    )
    set_refresh_cookie(response, raw_refresh_token)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth2 ID Token sign-in/registration",
)
@limiter.limit("10/minute")
async def google_auth(
    request: Request,
    auth_data: GoogleAuthRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate or register candidate via verified Google OAuth2 ID Token."""
    user, access_token, raw_refresh_token = (
        await AuthService.authenticate_google_user(db, auth_data.id_token)
    )
    set_refresh_cookie(response, raw_refresh_token)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/google/link",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly link Google identity to active candidate account",
)
async def link_google_account(
    link_data: AccountLinkConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Link Google identity to currently logged-in account after explicit confirmation."""
    user = await AuthService.link_google_account(
        db, current_user, link_data.id_token
    )
    return UserResponse.model_validate(user)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current candidate profile",
)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the authenticated candidate user profile."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate profile details",
)
async def update_profile(
    update_data: UserProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Update career profile fields (target role, experience tier, bio)."""
    user = await AuthService.update_user_profile(db, current_user, update_data)
    return UserResponse.model_validate(user)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset instructions",
)
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Request password recovery token. Always returns generic message to prevent account enumeration."""
    await AuthService.request_password_reset(db, reset_data.email)
    return MessageResponse(
        message="If an account with that email exists, password reset instructions have been dispatched."
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset with token",
)
async def confirm_password_reset(
    confirm_data: PasswordResetConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Confirm password reset using high-entropy single-use token and update password."""
    await AuthService.confirm_password_reset(
        db, confirm_data.token, confirm_data.new_password
    )
    return MessageResponse(
        message="Password has been reset successfully. Please log in with your new password."
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
async def refresh_session(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> TokenResponse:
    """Validate HttpOnly cookie, rotate refresh token (single-use), and return fresh 15-minute access token."""
    user, access_token, new_raw_refresh = await AuthService.rotate_refresh_token(
        db, refresh_token or ""
    )
    set_refresh_cookie(response, new_raw_refresh)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke active refresh token and clear cookie",
)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> MessageResponse:
    """Revoke session refresh token in database and clear the client cookie."""
    await AuthService.logout_user(db, refresh_token)
    clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully.")
