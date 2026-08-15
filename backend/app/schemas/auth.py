"""Pydantic v2 DTO schemas for authentication and user profiles."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import is_common_password


class UserRegisterRequest(BaseModel):
    """Candidate registration request payload."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Candidate's full display name.",
    )
    email: EmailStr = Field(
        ...,
        description="Normalized lowercase email address.",
    )
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description="Account passphrase (minimum 12 characters).",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email address to lowercase and strip whitespace."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate that password is not in common breach dictionary."""
        if is_common_password(v):
            raise ValueError(
                "Password is too common or easily guessable. Please choose a stronger passphrase."
            )
        return v


class UserLoginRequest(BaseModel):
    """Candidate login credential payload."""

    email: EmailStr = Field(..., description="Registered email address.")
    password: str = Field(..., description="Account passphrase.")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserResponse(BaseModel):
    """Candidate profile and user summary representation."""

    id: str
    email: str
    full_name: str
    auth_provider: str
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Authentication success token response containing in-memory access JWT."""

    access_token: str = Field(
        ..., description="Short-lived (15-minute) JWT access token."
    )
    token_type: str = "bearer"
    expires_in: int = Field(
        default=900, description="Token lifetime in seconds (15 minutes = 900s)."
    )
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic status message response."""

    message: str
    detail: Optional[str] = None
