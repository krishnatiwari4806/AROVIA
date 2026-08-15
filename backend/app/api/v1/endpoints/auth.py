"""Authentication and session management REST API endpoints."""

from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.auth import (
    MessageResponse,
    TokenResponse,
    UserLoginRequest,
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
