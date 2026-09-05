"""Coach Conversation and Message SQLAlchemy 2.0 ORM Models."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CommonModelMixin

if TYPE_CHECKING:
    from app.models.interview import InterviewSession
    from app.models.user import User


class CoachConversation(CommonModelMixin, Base):
    """Personal AI Coach persistent conversation session."""

    __tablename__ = "coach_conversations"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="coach_conversations"
    )
    session: Mapped[Optional["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="coach_conversations"
    )
    messages: Mapped[List["CoachMessage"]] = relationship(
        "CoachMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CoachMessage.created_at.asc()",
    )


class CoachMessage(CommonModelMixin, Base):
    """Individual message in a Personal AI Coach conversation."""

    __tablename__ = "coach_messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("coach_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user" | "coach"
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_turn_index: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    conversation: Mapped["CoachConversation"] = relationship(
        "CoachConversation", back_populates="messages"
    )
