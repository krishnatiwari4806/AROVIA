"""Database Base and Common Mixins."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative Base class for all SQLAlchemy ORM models."""


class CommonModelMixin:
    """Reusable model mixin providing UUID primary key and UTC audit timestamps."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )


# Import all models to ensure metadata registration for Alembic
from app.models.resume import Resume  # noqa: E402
from app.models.user import (  # noqa: E402
    PasswordResetToken,
    RefreshToken,
    User,
    UserOAuthIdentity,
)
