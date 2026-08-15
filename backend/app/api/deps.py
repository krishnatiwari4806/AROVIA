"""FastAPI route dependencies and security guards."""

from typing import Annotated, Optional

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login" if settings else "/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[Optional[str], Depends(reusable_oauth2)],
) -> User:
    """Extract, decode, and validate the JWT Bearer access token, loading the active candidate User."""
    if not token:
        raise UnauthorizedError(
            detail="Authentication credentials were not provided.",
            error_code="NOT_AUTHENTICATED",
        )
    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")
        if not user_id or token_type != "access":
            raise UnauthorizedError(
                detail="Invalid token claims or token type.",
                error_code="INVALID_TOKEN",
            )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(
            detail="Access token has expired. Please refresh your session.",
            error_code="TOKEN_EXPIRED",
        )
    except jwt.PyJWTError:
        raise UnauthorizedError(
            detail="Could not validate credentials.",
            error_code="INVALID_TOKEN",
        )

    stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(
            detail="Candidate user account not found or deactivated.",
            error_code="USER_NOT_FOUND",
        )
    return user
