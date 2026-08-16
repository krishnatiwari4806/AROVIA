"""Resume SQLAlchemy 2.0 ORM Model."""

from typing import Any, Dict, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, CommonModelMixin


class Resume(CommonModelMixin, Base):
    """Candidate Resume metadata, storage reference, and parsed JSON career data."""

    __tablename__ = "resumes"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="resume")  # type: ignore[name-defined]
