"""Interview Session lifecycle and configuration service."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.interview import InterviewSession
from app.models.resume import Resume
from app.models.user import User
from app.schemas.interview import (
    InterviewSessionCreateRequest,
    PracticeMode,
)
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.interview_presets import ROLE_PRESETS

logger = logging.getLogger(__name__)


def sanitize_job_description(text: Optional[str]) -> Optional[str]:
    """Sanitize custom job description text by stripping null bytes and non-printable control characters."""
    if not text:
        return None
    # Strip null bytes and non-printable control characters (keep standard whitespace: space, \n, \r, \t)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


class InterviewService:
    """Service governing mock interview sessions, role setup, and turn calibration."""

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or get_gemini_service()

    async def create_session(
        self,
        db: AsyncSession,
        current_user: User,
        request: InterviewSessionCreateRequest,
    ) -> InterviewSession:
        """Initialize and persist a new interview session.

        Enforces single active session policy (HTTP 409 if an active session exists).
        """
        # 1. Single active session check
        query = select(InterviewSession).where(
            InterviewSession.user_id == current_user.id,
            InterviewSession.status == "in_progress",
        )
        result = await db.execute(query)
        active_session = result.scalars().first()

        if active_session:
            raise ConflictError(
                message="An active interview session is already in progress.",
                error_code="ACTIVE_SESSION_EXISTS",
                details={"active_session_id": active_session.id},
            )

        # 2. Practice mode turn calibration
        if request.practice_mode == PracticeMode.quick:
            planned_core = 3
            max_turns = 5
        else:
            planned_core = 6
            max_turns = 9

        # 3. Sanitize and parse Job Description if provided
        sanitized_jd = sanitize_job_description(request.custom_job_desc)
        parsed_jd_data = None
        if sanitized_jd:
            parsed_jd = await self.gemini_service.parse_job_description(
                sanitized_jd
            )
            parsed_jd_data = parsed_jd.model_dump()

        # 4. Resolve focus skills (use provided, or fallback to preset defaults)
        focus_skills = list(request.focus_skills) if request.focus_skills else []
        if not focus_skills:
            # Check if target_role matches any preset
            norm_role = request.target_role.strip().lower()
            for preset in ROLE_PRESETS:
                if preset.title.lower() == norm_role or preset.role_id == norm_role:
                    focus_skills = list(preset.default_skills)
                    break

        # 5. Link latest active candidate resume if available
        resume_query = select(Resume).where(Resume.user_id == current_user.id)
        resume_res = await db.execute(resume_query)
        resume = resume_res.scalars().first()
        resume_id = resume.id if resume else None

        # 6. Instantiate and persist session
        session = InterviewSession(
            user_id=current_user.id,
            resume_id=resume_id,
            target_role=request.target_role.strip(),
            seniority_level=request.seniority_level.value,
            interview_focus=request.interview_focus.value,
            custom_job_desc=sanitized_jd,
            parsed_jd_data=parsed_jd_data,
            focus_skills=focus_skills,
            practice_mode=request.practice_mode.value,
            planned_core_questions=planned_core,
            max_total_turns=max_turns,
            current_turn_index=0,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_active_session(
        self, db: AsyncSession, current_user: User
    ) -> InterviewSession:
        """Fetch candidate's active in-progress session."""
        query = select(InterviewSession).where(
            InterviewSession.user_id == current_user.id,
            InterviewSession.status == "in_progress",
        )
        result = await db.execute(query)
        session = result.scalars().first()

        if not session:
            raise NotFoundError(
                message="No active interview session found.",
                error_code="NO_ACTIVE_SESSION",
            )
        return session

    async def get_session(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> InterviewSession:
        """Fetch session by ID with user isolation."""
        query = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
        result = await db.execute(query)
        session = result.scalars().first()

        if not session:
            raise NotFoundError(
                message="Interview session not found.",
                error_code="SESSION_NOT_FOUND",
            )
        return session

    async def abandon_session(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> InterviewSession:
        """Explicitly abandon an active in-progress interview session."""
        session = await self.get_session(
            db=db, current_user=current_user, session_id=session_id
        )

        if session.status != "in_progress":
            raise ValidationError(
                message="Only in-progress interview sessions can be abandoned."
            )

        session.status = "abandoned"
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)
        return session


def get_interview_service() -> InterviewService:
    """Dependency provider for InterviewService."""
    return InterviewService()
