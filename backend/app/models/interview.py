"""Interview Sessions and Question Turns SQLAlchemy 2.0 ORM Models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, CommonModelMixin

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.user import User


class InterviewSession(CommonModelMixin, Base):
    """Mock Interview Session lifecycle, role calibration, and turn limits."""

    __tablename__ = "interview_sessions"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_role: Mapped[str] = mapped_column(String(100), nullable=False)
    seniority_level: Mapped[str] = mapped_column(String(50), nullable=False)
    interview_focus: Mapped[str] = mapped_column(String(50), nullable=False)
    custom_job_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_jd_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    focus_skills: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    practice_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="full"
    )
    planned_core_questions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=6
    )
    max_total_turns: Mapped[int] = mapped_column(
        Integer, nullable=False, default=9
    )
    current_turn_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="in_progress", index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="interview_sessions"
    )
    resume: Mapped[Optional["Resume"]] = relationship(
        "Resume", back_populates="interview_sessions"
    )
    turns: Mapped[List["InterviewQuestionTurn"]] = relationship(
        "InterviewQuestionTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewQuestionTurn.turn_index",
    )


class InterviewQuestionTurn(CommonModelMixin, Base):
    """Interview question prompt, candidate response, and turn-level metadata."""

    __tablename__ = "interview_question_turns"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="core"
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_follow_up: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    parent_turn_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("interview_question_turns.id", ondelete="SET NULL"),
        nullable=True,
    )
    ideal_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    turn_duration_sec: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="turns"
    )
    parent_turn: Mapped[Optional["InterviewQuestionTurn"]] = relationship(
        "InterviewQuestionTurn",
        remote_side="InterviewQuestionTurn.id",
        back_populates="follow_up_turns",
    )
    follow_up_turns: Mapped[List["InterviewQuestionTurn"]] = relationship(
        "InterviewQuestionTurn", back_populates="parent_turn"
    )
