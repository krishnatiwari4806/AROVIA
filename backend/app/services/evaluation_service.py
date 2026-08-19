"""Evaluation Orchestrator and Multi-Dimensional Scoring Engine."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.schemas.evaluation import (
    ImprovementItem,
    SessionEvaluationReportResponse,
    StrengthItem,
    TurnEvaluationResponse,
)
from app.services.evaluation_heuristics import analyze_speech_confidence
from app.services.gemini_service import GeminiService, get_gemini_service

logger = logging.getLogger(__name__)


def compute_composite_score(scores: Dict[str, int], interview_focus: str) -> int:
    """Calculate focus-adaptive composite 0-100 score.

    Technical Core & System Design:
        35% Correctness, 25% Relevance, 20% Key Concepts, 10% Clarity, 10% Confidence

    Behavioral:
        30% Relevance, 30% Clarity, 20% Confidence, 10% Correctness, 10% Key Concepts
    """
    rel = scores.get("relevance", 50)
    corr = scores.get("correctness", 50)
    kw = scores.get("keywords", 50)
    cla = scores.get("clarity", 50)
    conf = scores.get("confidence", 50)

    focus = (interview_focus or "").lower()

    if "behavioral" in focus:
        raw = (
            (0.30 * rel)
            + (0.30 * cla)
            + (0.20 * conf)
            + (0.10 * corr)
            + (0.10 * kw)
        )
    else:
        # Technical Core, System Design, or custom
        raw = (
            (0.35 * corr)
            + (0.25 * rel)
            + (0.20 * kw)
            + (0.10 * cla)
            + (0.10 * conf)
        )

    return max(0, min(100, round(raw)))


class EvaluationService:
    """Orchestrates multi-dimensional evaluation, score calculation, and persistence."""

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or get_gemini_service()

    async def evaluate_session(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> SessionEvaluationReportResponse:
        """Run complete evaluation pipeline, update question turns and session record."""
        # 1. Fetch session with eager loaded resume and turns
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == current_user.id,
            )
            .options(
                selectinload(InterviewSession.resume),
                selectinload(InterviewSession.turns),
            )
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise NotFoundError(
                message="Interview session not found or does not belong to you.",
                error_code="SESSION_NOT_FOUND",
            )

        # If already evaluated and completed, return existing report
        if (
            session.status == "completed"
            and session.overall_score is not None
            and session.evaluation_report is not None
        ):
            return self._build_evaluation_response(session, session.turns)

        # 2. Get answered turns
        answered_turns = [
            t for t in session.turns if t.candidate_answer and t.candidate_answer.strip()
        ]

        if not answered_turns:
            raise ValidationError(
                message="Cannot evaluate session with zero answered questions.",
                error_code="NO_ANSWERED_TURNS",
            )

        # 3. Format turns for Gemini multi-dimensional evaluation
        transcript_data = [
            {
                "turn_index": t.turn_index,
                "question_text": t.question_text,
                "candidate_answer": t.candidate_answer or "",
                "ideal_answer": t.ideal_answer or "",
            }
            for t in answered_turns
        ]

        resume_data = (
            session.resume.parsed_data
            if session.resume and session.resume.parsed_data
            else None
        )

        # 4. Invoke Gemini AI Structured Evaluation
        ai_report = await self.gemini_service.evaluate_interview_session(
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            focus_skills=session.focus_skills,
            transcript_turns=transcript_data,
            parsed_jd_data=session.parsed_jd_data,
            resume_data=resume_data,
        )

        # 5. Process turn-level evaluations with local heuristic blending
        turn_eval_map = {te.turn_index: te for te in ai_report.turns_evaluation}

        for turn in answered_turns:
            local_nlp = analyze_speech_confidence(turn.candidate_answer or "")
            heuristic_conf = local_nlp["heuristic_confidence_score"]

            turn_ai_eval = turn_eval_map.get(turn.turn_index)
            if not turn_ai_eval:
                # Fallback if specific turn was missing in AI map
                turn_ai_eval = ai_report.turns_evaluation[0]

            # 40% local filler-word heuristic + 60% Gemini assertiveness
            blended_conf = max(
                0,
                min(
                    100,
                    round((0.40 * heuristic_conf) + (0.60 * turn_ai_eval.confidence_score)),
                ),
            )

            turn.relevance_score = turn_ai_eval.relevance_score
            turn.correctness_score = turn_ai_eval.correctness_score
            turn.keywords_score = turn_ai_eval.keywords_score
            turn.clarity_score = turn_ai_eval.clarity_score
            turn.confidence_score = blended_conf

            turn_scores_dict = {
                "relevance": turn.relevance_score,
                "correctness": turn.correctness_score,
                "keywords": turn.keywords_score,
                "clarity": turn.clarity_score,
                "confidence": turn.confidence_score,
            }
            turn.turn_score = compute_composite_score(
                turn_scores_dict, session.interview_focus
            )

            turn.evaluation_data = {
                "covered_concepts": turn_ai_eval.covered_concepts,
                "missed_concepts": turn_ai_eval.missed_concepts,
                "ideal_answer_comparison": turn_ai_eval.ideal_answer_comparison,
                "turn_feedback": turn_ai_eval.turn_feedback,
                "filler_word_stats": {
                    "count": local_nlp["filler_count"],
                    "density": local_nlp["filler_density"],
                    "detected": local_nlp["detected_fillers"],
                },
            }

        # 6. Calculate Session Aggregates (Radar Metrics + Overall Score)
        n = len(answered_turns)
        avg_rel = round(sum(t.relevance_score or 0 for t in answered_turns) / n)
        avg_corr = round(sum(t.correctness_score or 0 for t in answered_turns) / n)
        avg_kw = round(sum(t.keywords_score or 0 for t in answered_turns) / n)
        avg_cla = round(sum(t.clarity_score or 0 for t in answered_turns) / n)
        avg_conf = round(sum(t.confidence_score or 0 for t in answered_turns) / n)

        dimension_scores = {
            "relevance": avg_rel,
            "correctness": avg_corr,
            "keywords": avg_kw,
            "clarity": avg_cla,
            "confidence": avg_conf,
        }

        overall_score = compute_composite_score(
            dimension_scores, session.interview_focus
        )

        session.overall_score = overall_score
        session.dimension_scores = dimension_scores
        session.evaluation_report = {
            "top_strengths": [s.model_dump() for s in ai_report.top_strengths],
            "top_improvements": [i.model_dump() for i in ai_report.top_improvements],
            "executive_summary": ai_report.executive_summary,
        }
        session.status = "completed"
        if not session.completed_at:
            session.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(session)

        return self._build_evaluation_response(session, answered_turns)

    async def get_session_evaluation(
        self, db: AsyncSession, current_user: User, session_id: str
    ) -> SessionEvaluationReportResponse:
        """Retrieve existing evaluation report, or compute it if not yet evaluated."""
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == current_user.id,
            )
            .options(
                selectinload(InterviewSession.resume),
                selectinload(InterviewSession.turns),
            )
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

        if not session:
            raise NotFoundError(
                message="Interview session not found or does not belong to you.",
                error_code="SESSION_NOT_FOUND",
            )

        if (
            session.status == "completed"
            and session.overall_score is not None
            and session.evaluation_report is not None
        ):
            return self._build_evaluation_response(session, session.turns)

        # If not evaluated yet, run evaluation pipeline
        return await self.evaluate_session(db, current_user, session_id)

    def _build_evaluation_response(
        self, session: InterviewSession, turns: List[InterviewQuestionTurn]
    ) -> SessionEvaluationReportResponse:
        """Helper to construct the unified API response DTO."""
        eval_report = session.evaluation_report or {}
        raw_strengths = eval_report.get("top_strengths", [])
        raw_improvements = eval_report.get("top_improvements", [])

        top_strengths = [StrengthItem(**s) for s in raw_strengths]
        top_improvements = [ImprovementItem(**i) for i in raw_improvements]
        exec_summary = eval_report.get(
            "executive_summary", "Evaluation complete."
        )

        turns_eval_resp = []
        for t in turns:
            t_eval = t.evaluation_data or {}
            turns_eval_resp.append(
                TurnEvaluationResponse(
                    id=t.id,
                    session_id=t.session_id,
                    turn_index=t.turn_index,
                    question_type=t.question_type,
                    question_text=t.question_text,
                    candidate_answer=t.candidate_answer,
                    ideal_answer=t.ideal_answer,
                    turn_duration_sec=t.turn_duration_sec,
                    relevance_score=t.relevance_score,
                    correctness_score=t.correctness_score,
                    keywords_score=t.keywords_score,
                    clarity_score=t.clarity_score,
                    confidence_score=t.confidence_score,
                    turn_score=t.turn_score,
                    covered_concepts=t_eval.get("covered_concepts", []),
                    missed_concepts=t_eval.get("missed_concepts", []),
                    ideal_answer_comparison=t_eval.get("ideal_answer_comparison"),
                    turn_feedback=t_eval.get("turn_feedback"),
                )
            )

        return SessionEvaluationReportResponse(
            session_id=session.id,
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            practice_mode=session.practice_mode,
            status=session.status,
            overall_score=session.overall_score or 0,
            dimension_scores=session.dimension_scores or {},
            executive_summary=exec_summary,
            top_strengths=top_strengths,
            top_improvements=top_improvements,
            turns_evaluation=turns_eval_resp,
            started_at=session.started_at,
            completed_at=session.completed_at,
        )


def get_evaluation_service() -> EvaluationService:
    """Dependency provider for EvaluationService."""
    return EvaluationService()
