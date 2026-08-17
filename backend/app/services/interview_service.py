"""Interview Session lifecycle, turn progression, and adaptive orchestration service."""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.resume import Resume
from app.models.user import User
from app.schemas.interview import (
    InterviewQuestionTurnResponse,
    InterviewSessionCreateRequest,
    PracticeMode,
    TurnAnswerSubmissionRequest,
    TurnAnswerSubmissionResponse,
)
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.interview_presets import ROLE_PRESETS

logger = logging.getLogger(__name__)


def sanitize_job_description(text: Optional[str]) -> Optional[str]:
    """Sanitize custom job description text by stripping null bytes and non-printable control characters."""
    if not text:
        return None
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


class InterviewService:
    """Service governing mock interview sessions, role setup, and adaptive turn progression."""

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

    async def start_interview(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> InterviewQuestionTurn:
        """Initialize interview turn loop by generating Turn 0 (Initial Question).

        Idempotent: If turn 0 already exists, returns existing turn 0.
        """
        session = await self.get_session(
            db=db, current_user=current_user, session_id=session_id
        )

        if session.status != "in_progress":
            raise ValidationError(
                message="Cannot start an interview that is not in progress."
            )

        # Check if turns already exist
        turns_query = (
            select(InterviewQuestionTurn)
            .where(InterviewQuestionTurn.session_id == session.id)
            .order_by(InterviewQuestionTurn.turn_index.asc())
        )
        turns_res = await db.execute(turns_query)
        existing_turns = turns_res.scalars().all()

        if existing_turns:
            return existing_turns[0]

        # Load resume data if attached
        resume_data = None
        if session.resume_id:
            res_query = select(Resume).where(Resume.id == session.resume_id)
            res_result = await db.execute(res_query)
            res_record = res_result.scalars().first()
            if res_record and res_record.parsed_data:
                resume_data = res_record.parsed_data

        # Generate initial core question via Gemini
        generated = await self.gemini_service.generate_initial_question(
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            focus_skills=session.focus_skills,
            parsed_jd_data=session.parsed_jd_data,
            resume_data=resume_data,
        )

        turn0 = InterviewQuestionTurn(
            session_id=session.id,
            turn_index=0,
            question_type="core",
            question_text=generated.question_text,
            ideal_answer=generated.ideal_answer,
            is_follow_up=False,
            parent_turn_id=None,
        )

        session.current_turn_index = 0
        db.add(turn0)
        await db.commit()
        await db.refresh(turn0)
        return turn0

    async def get_current_turn(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> InterviewQuestionTurn:
        """Fetch the latest active question turn for the session."""
        session = await self.get_session(
            db=db, current_user=current_user, session_id=session_id
        )

        turns_query = (
            select(InterviewQuestionTurn)
            .where(InterviewQuestionTurn.session_id == session.id)
            .order_by(InterviewQuestionTurn.turn_index.desc())
        )
        turns_res = await db.execute(turns_query)
        latest_turn = turns_res.scalars().first()

        if not latest_turn:
            raise NotFoundError(
                message="No active question turns found for this session. Start the interview first.",
                error_code="TURN_NOT_FOUND",
            )
        return latest_turn

    async def submit_turn_answer(
        self,
        db: AsyncSession,
        current_user: User,
        session_id: str,
        turn_id: str,
        request: TurnAnswerSubmissionRequest,
    ) -> TurnAnswerSubmissionResponse:
        """Submit candidate answer for a turn, evaluate depth, and generate next turn or complete session."""
        session = await self.get_session(
            db=db, current_user=current_user, session_id=session_id
        )

        if session.status != "in_progress":
            raise ValidationError(
                message="Cannot submit answer for an interview that is not in progress."
            )

        turn_query = select(InterviewQuestionTurn).where(
            InterviewQuestionTurn.id == turn_id,
            InterviewQuestionTurn.session_id == session.id,
        )
        turn_res = await db.execute(turn_query)
        turn = turn_res.scalars().first()

        if not turn:
            raise NotFoundError(
                message="Question turn not found.",
                error_code="TURN_NOT_FOUND",
            )

        if turn.candidate_answer is not None:
            raise ValidationError(
                message="This question turn has already been answered.",
                error_code="TURN_ALREADY_ANSWERED",
            )

        # 1. Update and persist candidate's answer
        turn.candidate_answer = request.candidate_answer.strip()
        turn.turn_duration_sec = request.turn_duration_sec
        await db.flush()

        # 2. Fetch all completed turns in session
        all_turns_query = (
            select(InterviewQuestionTurn)
            .where(InterviewQuestionTurn.session_id == session.id)
            .order_by(InterviewQuestionTurn.turn_index.asc())
        )
        all_turns_res = await db.execute(all_turns_query)
        all_turns = all_turns_res.scalars().all()

        core_turns = [t for t in all_turns if not t.is_follow_up]
        followup_turns = [t for t in all_turns if t.is_follow_up]

        completed_core = len(core_turns)
        completed_followups = len(followup_turns)
        total_turns = len(all_turns)

        max_followups = max(0, session.max_total_turns - session.planned_core_questions)
        remaining_core = max(0, session.planned_core_questions - completed_core)
        remaining_followup_budget = max(0, max_followups - completed_followups)

        # 3. Check hard session completion boundary
        if total_turns >= session.max_total_turns or (
            remaining_core <= 0 and (turn.is_follow_up or remaining_followup_budget <= 0)
        ):
            session.status = "evaluating"
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return TurnAnswerSubmissionResponse(
                session_id=session.id,
                current_turn_index=turn.turn_index,
                session_status=session.status,
                is_interview_complete=True,
                answered_turn_id=turn.id,
                next_turn=None,
            )

        # 4. Invoke Gemini adaptive evaluator
        transcript_history = [
            {
                "turn_index": t.turn_index,
                "question_text": t.question_text,
                "candidate_answer": t.candidate_answer,
            }
            for t in all_turns
        ]

        decision = await self.gemini_service.evaluate_and_generate_next_turn(
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            focus_skills=session.focus_skills,
            current_turn_index=turn.turn_index,
            remaining_core_questions=remaining_core,
            remaining_followup_budget=remaining_followup_budget,
            prior_turn_was_followup=turn.is_follow_up,
            previous_question=turn.question_text,
            candidate_answer=turn.candidate_answer,
            transcript_history=transcript_history,
        )

        if decision.is_interview_complete or not decision.question_text:
            session.status = "evaluating"
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return TurnAnswerSubmissionResponse(
                session_id=session.id,
                current_turn_index=turn.turn_index,
                session_status=session.status,
                is_interview_complete=True,
                answered_turn_id=turn.id,
                next_turn=None,
            )

        # 5. Create next turn
        next_turn_index = total_turns
        next_turn = InterviewQuestionTurn(
            session_id=session.id,
            turn_index=next_turn_index,
            question_type="follow_up" if decision.is_follow_up else "core",
            question_text=decision.question_text,
            ideal_answer=decision.ideal_answer,
            is_follow_up=decision.is_follow_up,
            parent_turn_id=turn.id if decision.is_follow_up else None,
        )

        session.current_turn_index = next_turn_index
        db.add(next_turn)
        await db.commit()
        await db.refresh(next_turn)

        return TurnAnswerSubmissionResponse(
            session_id=session.id,
            current_turn_index=next_turn_index,
            session_status=session.status,
            is_interview_complete=False,
            answered_turn_id=turn.id,
            next_turn=InterviewQuestionTurnResponse.model_validate(next_turn),
        )

    async def get_session_turns(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> List[InterviewQuestionTurn]:
        """Fetch all chronologically ordered turns for an interview session."""
        session = await self.get_session(
            db=db, current_user=current_user, session_id=session_id
        )

        query = (
            select(InterviewQuestionTurn)
            .where(InterviewQuestionTurn.session_id == session.id)
            .order_by(InterviewQuestionTurn.turn_index.asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())


def get_interview_service() -> InterviewService:
    """Dependency provider for InterviewService."""
    return InterviewService()
