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
from app.services.candidate_context import CandidateContext, build_candidate_context
from app.services.gemini_service import (
    GeminiService,
    get_fallback_followup,
    get_gemini_service,
    get_grounded_fallback_question,
)
from app.services.interview_presets import ROLE_PRESETS
from app.services.question_bank import (
    get_competency_stages,
    get_fallback_question,
)
from app.services.question_planner import (
    QuestionIntent,
    QuestionPlan,
    QuestionPlanner,
    get_question_planner,
)

logger = logging.getLogger(__name__)


def get_introduction_prompt(
    preferred_language: str = "en",
    target_role: str = "Software Engineer",
    seniority_level: str = "mid",
) -> str:
    """Generate conversational Turn 0 introduction warm-up prompt respecting preferred language."""
    lang = (preferred_language or "en").lower().strip()
    role = target_role or "Software Engineer"
    seniority = seniority_level.capitalize() if seniority_level else "Mid-level"

    if lang == "hi":
        return (
            f"Namaste! AROVIA mock interview platform par aapka swagat hai. Hum {seniority} {role} "
            f"position ke liye technical assessment shuru karenge. Technical discussion shuru karne se pehle, "
            f"kya aap briefly apna introduction de sakte hain aur apne engineering background ke baare mein bata sakte hain?"
        )
    elif lang == "hinglish":
        return (
            f"Hi, welcome to AROVIA! We are setting up your mock interview for the {seniority} {role} "
            f"position. Technical discussion start karne se pehle, could you briefly introduce yourself "
            f"and share a quick overview of your engineering background and key technical focus?"
        )
    else:
        return (
            f"Hi, welcome to AROVIA! We are getting ready for your mock interview for the {seniority} {role} "
            f"position. Before we dive into the technical discussion, could you briefly introduce yourself "
            f"and share a quick overview of your background and core technical focus?"
        )


def compute_turn_metadata(
    session: InterviewSession,
    turn: InterviewQuestionTurn,
    all_turns: List[InterviewQuestionTurn],
) -> dict:
    """Compute authoritative turn progression metadata distinguishing Turn 0, core questions, and follow-ups."""
    total_core = session.planned_core_questions or 6

    # 1. Turn 0 / Introduction
    if turn.question_type == "introduction" or (turn.turn_index == 0 and turn.question_type == "introduction"):
        return {
            "core_question_index": None,
            "core_question_number": None,
            "total_core_questions": total_core,
            "follow_up_number": 0,
            "interview_phase": "introduction",
        }

    # Identify all core questions in chronological order
    core_turns = [
        t for t in all_turns
        if t.question_type == "core" or (not t.is_follow_up and t.question_type != "introduction")
    ]

    # 2. Follow-up Turn
    if turn.is_follow_up or turn.question_type == "follow_up":
        parent_core = None
        if turn.parent_turn_id:
            parent_core = next((t for t in all_turns if t.id == turn.parent_turn_id), None)
        if not parent_core:
            parent_core = next(
                (
                    t for t in reversed(all_turns)
                    if t.turn_index < turn.turn_index
                    and (t.question_type == "core" or (not t.is_follow_up and t.question_type != "introduction"))
                ),
                None,
            )

        if parent_core:
            parent_core_k = next(
                (i + 1 for i, t in enumerate(core_turns) if t.id == parent_core.id or t.turn_index == parent_core.turn_index),
                1,
            )
            followups_for_parent = [
                t for t in all_turns
                if (t.is_follow_up or t.question_type == "follow_up")
                and (
                    t.parent_turn_id == parent_core.id
                    or (not t.parent_turn_id and t.turn_index > parent_core.turn_index)
                )
            ]
            fu_num = next(
                (i + 1 for i, t in enumerate(followups_for_parent) if t.id == turn.id or t.turn_index == turn.turn_index),
                1,
            )
        else:
            parent_core_k = 1
            fu_num = 1

        return {
            "core_question_index": parent_core_k - 1,
            "core_question_number": parent_core_k,
            "total_core_questions": total_core,
            "follow_up_number": fu_num,
            "interview_phase": "follow_up",
        }

    # 3. Core Question Turn
    core_k = next(
        (i + 1 for i, t in enumerate(core_turns) if t.id == turn.id or t.turn_index == turn.turn_index),
        len(core_turns) if core_turns else 1,
    )
    return {
        "core_question_index": core_k - 1,
        "core_question_number": core_k,
        "total_core_questions": total_core,
        "follow_up_number": 0,
        "interview_phase": "core_question",
    }


def build_turn_response(
    turn: InterviewQuestionTurn,
    session: InterviewSession,
    all_turns: Optional[List[InterviewQuestionTurn]] = None,
) -> InterviewQuestionTurnResponse:
    """Build an InterviewQuestionTurnResponse enriched with authoritative progression metadata."""
    if all_turns is None:
        all_turns = [turn]

    meta = compute_turn_metadata(session, turn, all_turns)

    return InterviewQuestionTurnResponse(
        id=turn.id,
        session_id=turn.session_id,
        turn_index=turn.turn_index,
        question_type=turn.question_type,
        question_text=turn.question_text,
        candidate_answer=turn.candidate_answer,
        is_follow_up=turn.is_follow_up,
        parent_turn_id=turn.parent_turn_id,
        ideal_answer=turn.ideal_answer,
        turn_duration_sec=turn.turn_duration_sec,
        core_question_index=meta["core_question_index"],
        core_question_number=meta["core_question_number"],
        total_core_questions=meta["total_core_questions"],
        follow_up_number=meta["follow_up_number"],
        interview_phase=meta["interview_phase"],
        created_at=turn.created_at,
    )


def _normalize_question_text(text: Optional[str]) -> str:
    """Normalize question text for duplicate detection: strip punctuation, collapse whitespace, lowercase."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())


def _normalize_answer_text(text: Optional[str]) -> str:
    """Normalize candidate answer text for idempotent comparison: strip and collapse whitespace."""
    if not text:
        return ""
    return " ".join(text.strip().split())


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
        # Turn 0 is intro + planned_core core questions + follow-ups
        if request.practice_mode == PracticeMode.quick:
            planned_core = 3
            max_turns = 6  # 1 intro + 3 core + up to 2 follow-ups
        else:
            planned_core = 6
            max_turns = 10  # 1 intro + 6 core + up to 3 follow-ups

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
        preferred_lang = (
            request.preferred_language.value
            if hasattr(request.preferred_language, "value")
            else str(request.preferred_language or "en")
        )

        session = InterviewSession(
            user_id=current_user.id,
            resume_id=resume_id,
            target_role=request.target_role.strip(),
            seniority_level=request.seniority_level.value,
            interview_focus=request.interview_focus.value,
            preferred_language=preferred_lang,
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
        """Initialize interview turn loop by generating Turn 0 (Introduction / Warm-up).

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

        # Generate Turn 0 conversational introduction warm-up prompt respecting preferred_language
        pref_lang = getattr(session, "preferred_language", "en") or "en"
        intro_text = get_introduction_prompt(
            preferred_language=pref_lang,
            target_role=session.target_role,
            seniority_level=session.seniority_level,
        )

        turn0 = InterviewQuestionTurn(
            session_id=session.id,
            turn_index=0,
            question_type="introduction",
            question_text=intro_text,
            ideal_answer="Candidate conversational background and engineering introduction overview.",
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

        # 1. Fetch all existing turns in session
        all_turns_query = (
            select(InterviewQuestionTurn)
            .where(InterviewQuestionTurn.session_id == session.id)
            .order_by(InterviewQuestionTurn.turn_index.asc())
        )
        all_turns_res = await db.execute(all_turns_query)
        all_turns = list(all_turns_res.scalars().all())

        if turn.candidate_answer is not None:
            submitted_norm = _normalize_answer_text(request.candidate_answer)
            existing_norm = _normalize_answer_text(turn.candidate_answer)

            if submitted_norm != existing_norm:
                raise ValidationError(
                    message="This question turn has already been answered.",
                    error_code="TURN_ALREADY_ANSWERED",
                )

            # Idempotent retry with identical answer: determine existing state without re-running LLM or generating turns
            turn_meta = compute_turn_metadata(session, turn, all_turns)
            if session.status in ("evaluating", "completed"):
                return TurnAnswerSubmissionResponse(
                    session_id=session.id,
                    current_turn_index=turn.turn_index,
                    session_status=session.status,
                    is_interview_complete=True,
                    answered_turn_id=turn.id,
                    current_core_question_index=turn_meta["core_question_index"],
                    total_core_questions=session.planned_core_questions,
                    interview_phase="completed",
                    next_turn=None,
                )

            next_turns = [t for t in all_turns if t.turn_index > turn.turn_index]
            if next_turns:
                next_turn = next_turns[0]
                next_meta = compute_turn_metadata(session, next_turn, all_turns)
                return TurnAnswerSubmissionResponse(
                    session_id=session.id,
                    current_turn_index=next_turn.turn_index,
                    session_status=session.status,
                    is_interview_complete=False,
                    answered_turn_id=turn.id,
                    current_core_question_index=next_meta["core_question_index"],
                    total_core_questions=session.planned_core_questions,
                    interview_phase=next_meta["interview_phase"],
                    next_turn=build_turn_response(next_turn, session, all_turns),
                )
        else:
            if session.status != "in_progress":
                raise ValidationError(
                    message="Cannot submit answer for an interview that is not in progress."
                )

            # Persist candidate's answer on the active turn
            turn.candidate_answer = request.candidate_answer.strip()
            turn.turn_duration_sec = request.turn_duration_sec
            await db.flush()

        # Update turn in local all_turns snapshot
        for idx, t in enumerate(all_turns):
            if t.id == turn.id:
                all_turns[idx] = turn
                break

        # 2. Check if the answered turn was Turn 0 (Introduction warm-up)
        if turn.question_type == "introduction" or (turn.turn_index == 0 and turn.question_type == "introduction"):
            # Load resume data if attached
            resume_data = None
            if session.resume_id:
                res_query = select(Resume).where(Resume.id == session.resume_id)
                res_result = await db.execute(res_query)
                res_record = res_result.scalars().first()
                if res_record and res_record.parsed_data:
                    resume_data = res_record.parsed_data
            else:
                res_query = select(Resume).where(Resume.user_id == current_user.id)
                res_result = await db.execute(res_query)
                res_record = res_result.scalars().first()
                if res_record and res_record.parsed_data:
                    resume_data = res_record.parsed_data

            # Build structured candidate context with Turn 0 intro response
            candidate_context = build_candidate_context(
                target_role=session.target_role,
                seniority_level=session.seniority_level,
                interview_focus=session.interview_focus,
                preferred_language=getattr(session, "preferred_language", "en") or "en",
                resume_data=resume_data,
                parsed_jd_data=session.parsed_jd_data,
                focus_skills=session.focus_skills,
                introduction_response=turn.candidate_answer,
            )

            planner = get_question_planner()
            q1_plan = planner.plan_next_question(
                context=candidate_context,
                planned_core_questions=session.planned_core_questions,
                current_core_index=0,
            )

            # Generate Core Question 1 via Gemini (grounded in candidate context and plan)
            generated = await self.gemini_service.generate_initial_question(
                target_role=session.target_role,
                seniority_level=session.seniority_level,
                interview_focus=session.interview_focus,
                focus_skills=session.focus_skills,
                parsed_jd_data=session.parsed_jd_data,
                resume_data=resume_data,
                preferred_language=getattr(session, "preferred_language", "en") or "en",
                candidate_context=candidate_context,
                question_plan=q1_plan,
            )

            q_text = (generated.question_text or "").strip()
            ideal_ans = generated.ideal_answer or ""
            if not q_text:
                fallback_q0 = get_grounded_fallback_question(
                    context=candidate_context,
                    plan=q1_plan,
                    language=getattr(session, "preferred_language", "en") or "en",
                    stage_index=0,
                )
                q_text = fallback_q0.question_text
                ideal_ans = fallback_q0.ideal_answer

            turn1 = InterviewQuestionTurn(
                session_id=session.id,
                turn_index=1,
                question_type="core",
                question_text=q_text,
                ideal_answer=ideal_ans,
                is_follow_up=False,
                parent_turn_id=None,
            )

            session.current_turn_index = 1
            db.add(turn1)
            await db.commit()
            await db.refresh(turn1)

            updated_turns = all_turns + [turn1]
            return TurnAnswerSubmissionResponse(
                session_id=session.id,
                current_turn_index=1,
                session_status=session.status,
                is_interview_complete=False,
                answered_turn_id=turn.id,
                current_core_question_index=0,
                total_core_questions=session.planned_core_questions,
                interview_phase="core_question",
                next_turn=build_turn_response(turn1, session, updated_turns),
            )

        # 3. Categorize completed core and follow-up turns
        core_turns = [
            t for t in all_turns
            if t.question_type == "core" or (not t.is_follow_up and t.question_type != "introduction")
        ]
        followup_turns = [
            t for t in all_turns
            if t.is_follow_up or t.question_type == "follow_up"
        ]

        completed_core = len(core_turns)
        completed_followups = len(followup_turns)
        total_turns = len(all_turns)

        max_followups = max(0, session.max_total_turns - session.planned_core_questions - 1)
        remaining_core = max(0, session.planned_core_questions - completed_core)
        remaining_followup_budget = max(0, max_followups - completed_followups)

        # 4. Check hard maximum total turn boundary
        if total_turns >= session.max_total_turns:
            session.status = "evaluating"
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return TurnAnswerSubmissionResponse(
                session_id=session.id,
                current_turn_index=turn.turn_index,
                session_status=session.status,
                is_interview_complete=True,
                answered_turn_id=turn.id,
                current_core_question_index=max(0, completed_core - 1),
                total_core_questions=session.planned_core_questions,
                interview_phase="completed",
                next_turn=None,
            )

        # 5. Determine follow-up eligibility for the just-answered turn
        # A follow-up is ONLY allowed if:
        # - The current answered turn is a core turn (not a follow-up, and not intro)
        # - The current core turn has not already received a follow-up
        # - Global follow-up budget remains (> 0)
        # - Total turns has not reached max_total_turns
        already_has_followup = any(t.parent_turn_id == turn.id for t in followup_turns)
        is_current_core = (turn.question_type == "core" or (not turn.is_follow_up and turn.question_type != "introduction"))

        followup_eligible = (
            is_current_core
            and not already_has_followup
            and remaining_followup_budget > 0
            and total_turns < session.max_total_turns
        )

        # 6. Check if any next turn is possible:
        # If no follow-up is eligible AND no core questions remain, the interview is complete!
        if not followup_eligible and remaining_core <= 0:
            session.status = "evaluating"
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return TurnAnswerSubmissionResponse(
                session_id=session.id,
                current_turn_index=turn.turn_index,
                session_status=session.status,
                is_interview_complete=True,
                answered_turn_id=turn.id,
                current_core_question_index=max(0, completed_core - 1),
                total_core_questions=session.planned_core_questions,
                interview_phase="completed",
                next_turn=None,
            )

        # Collect prior normalized questions and known Question Bank IDs
        prior_normalized_questions = {
            _normalize_question_text(t.question_text)
            for t in all_turns
            if t.question_text
        }
        excluded_question_ids: set[str] = set()
        stages = get_competency_stages(
            role=session.target_role,
            seniority=session.seniority_level,
            focus=session.interview_focus,
        )
        for t in all_turns:
            norm_t = _normalize_question_text(t.question_text)
            for stage in stages:
                for q in stage.core_questions:
                    if _normalize_question_text(q.question_text) == norm_t:
                        excluded_question_ids.add(q.id)
                    for f in q.follow_ups:
                        if _normalize_question_text(f.prompt) == norm_t:
                            excluded_question_ids.add(f.id)

        # 7. Construct Candidate Context and Question Plan for upcoming turns
        resume_data = None
        if session.resume_id:
            res_query = select(Resume).where(Resume.id == session.resume_id)
            res_result = await db.execute(res_query)
            res_record = res_result.scalars().first()
            if res_record and res_record.parsed_data:
                resume_data = res_record.parsed_data
        else:
            res_query = select(Resume).where(Resume.user_id == current_user.id)
            res_result = await db.execute(res_query)
            res_record = res_result.scalars().first()
            if res_record and res_record.parsed_data:
                resume_data = res_record.parsed_data

        intro_turn = next((t for t in all_turns if t.question_type == "introduction" or t.turn_index == 0), None)
        intro_ans = intro_turn.candidate_answer if intro_turn else None

        candidate_context = build_candidate_context(
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            preferred_language=getattr(session, "preferred_language", "en") or "en",
            resume_data=resume_data,
            parsed_jd_data=session.parsed_jd_data,
            focus_skills=session.focus_skills,
            introduction_response=intro_ans,
        )

        covered_topics = [t.question_text for t in all_turns if t.question_text]
        transcript_history = [
            {
                "turn_index": t.turn_index,
                "question_text": t.question_text,
                "candidate_answer": t.candidate_answer,
                "is_follow_up": t.is_follow_up,
            }
            for t in all_turns
        ]

        planner = get_question_planner()
        next_core_plan = planner.plan_next_question(
            context=candidate_context,
            planned_core_questions=session.planned_core_questions,
            current_core_index=completed_core,
            covered_topics=covered_topics,
            previous_turns=transcript_history,
        )

        # Invoke Gemini adaptive evaluator with Candidate Context, Planner, and authoritative state bounds
        decision = await self.gemini_service.evaluate_and_generate_next_turn(
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            focus_skills=session.focus_skills,
            current_turn_index=turn.turn_index,
            remaining_core_questions=remaining_core,
            remaining_followup_budget=remaining_followup_budget if followup_eligible else 0,
            prior_turn_was_followup=turn.is_follow_up,
            previous_question=turn.question_text,
            candidate_answer=turn.candidate_answer,
            transcript_history=transcript_history,
            excluded_question_ids=excluded_question_ids,
            preferred_language=getattr(session, "preferred_language", "en") or "en",
            parsed_jd_data=session.parsed_jd_data,
            resume_data=resume_data,
            candidate_context=candidate_context,
            question_plan=next_core_plan,
        )

        # 8. Validate and enforce deterministic next-turn state
        allow_followup = followup_eligible and bool(decision.is_follow_up)
        raw_q_text = (decision.question_text or "").strip()
        is_duplicate = bool(raw_q_text and _normalize_question_text(raw_q_text) in prior_normalized_questions)

        if allow_followup and raw_q_text and not is_duplicate:
            next_is_followup = True
            next_parent_turn_id = turn.id
            next_question_type = "follow_up"
            next_question_text = raw_q_text
            next_ideal_answer = decision.ideal_answer
        elif remaining_core > 0 and raw_q_text and not is_duplicate:
            next_is_followup = False
            next_parent_turn_id = None
            next_question_type = "core"
            next_question_text = raw_q_text
            next_ideal_answer = decision.ideal_answer
        elif remaining_core > 0:
            # Fallback triggered by: premature completion, empty question text, or duplicate question text
            logger.warning(
                f"Session {session.id} Turn {turn.turn_index + 1}: Overriding Gemini output (duplicate={is_duplicate}, empty={not raw_q_text}) with grounded fallback."
            )
            fallback_core = get_grounded_fallback_question(
                context=candidate_context,
                plan=next_core_plan,
                language=getattr(session, "preferred_language", "en") or "en",
                stage_index=completed_core,
                excluded_question_ids=excluded_question_ids,
            )
            next_is_followup = False
            next_parent_turn_id = None
            next_question_type = "core"
            next_question_text = fallback_core.question_text
            next_ideal_answer = fallback_core.ideal_answer
        else:
            # Core budget exhausted or missing question text -> complete interview
            session.status = "evaluating"
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return TurnAnswerSubmissionResponse(
                session_id=session.id,
                current_turn_index=turn.turn_index,
                session_status=session.status,
                is_interview_complete=True,
                answered_turn_id=turn.id,
                current_core_question_index=max(0, completed_core - 1),
                total_core_questions=session.planned_core_questions,
                interview_phase="completed",
                next_turn=None,
            )

        # 9. Create and persist the authoritative next turn
        next_turn_index = total_turns
        next_turn = InterviewQuestionTurn(
            session_id=session.id,
            turn_index=next_turn_index,
            question_type=next_question_type,
            question_text=next_question_text,
            ideal_answer=next_ideal_answer,
            is_follow_up=next_is_followup,
            parent_turn_id=next_parent_turn_id,
        )

        session.current_turn_index = next_turn_index
        db.add(next_turn)
        await db.commit()
        await db.refresh(next_turn)

        updated_turns = all_turns + [next_turn]
        next_meta = compute_turn_metadata(session, next_turn, updated_turns)

        return TurnAnswerSubmissionResponse(
            session_id=session.id,
            current_turn_index=next_turn_index,
            session_status=session.status,
            is_interview_complete=False,
            answered_turn_id=turn.id,
            current_core_question_index=next_meta["core_question_index"],
            total_core_questions=session.planned_core_questions,
            interview_phase=next_meta["interview_phase"],
            next_turn=build_turn_response(next_turn, session, updated_turns),
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

    async def list_user_sessions(
        self,
        db: AsyncSession,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InterviewSession]:
        """Fetch all interview sessions belonging to the current user, ordered newest first."""
        query = (
            select(InterviewSession)
            .where(InterviewSession.user_id == current_user.id)
            .order_by(InterviewSession.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


def get_interview_service() -> InterviewService:
    """Dependency provider for InterviewService."""
    return InterviewService()

