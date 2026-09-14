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
    AnswerQualityTier,
    CompletenessLevel,
    ConceptEvidence,
    ExpectedConcept,
    ImprovementItem,
    SessionEvaluationReportResponse,
    StrengthItem,
    TurnEvaluationResponse,
)
from app.services.answer_classifier import (
    classify_answer_deterministically,
    is_short_valid_answer,
)
from app.services.evaluation_heuristics import analyze_speech_confidence
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.reference_evaluator import (
    ReferenceEvaluatorService,
    get_reference_evaluator_service,
)
from app.services.score_calibrator import (
    ScoreCalibrator,
    compute_composite_score,
    get_score_calibrator,
)
from app.services.semantic_evaluator import (
    SemanticEvaluatorEngine,
    get_semantic_evaluator_engine,
)

logger = logging.getLogger(__name__)


class EvaluationService:
    """Orchestrates multi-dimensional evaluation, score calculation, and persistence."""

    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        reference_service: Optional[ReferenceEvaluatorService] = None,
        semantic_engine: Optional[SemanticEvaluatorEngine] = None,
        score_calibrator: Optional[ScoreCalibrator] = None,
    ):
        self.gemini_service = gemini_service or get_gemini_service()
        self.reference_service = reference_service or get_reference_evaluator_service()
        self.semantic_engine = semantic_engine or get_semantic_evaluator_engine()
        self.score_calibrator = score_calibrator or get_score_calibrator()

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
            preferred_language=getattr(session, "preferred_language", "en"),
        )

        # 5. Process turn-level evaluations with local heuristic blending, reference payload resolution, and semantic evaluation
        turn_eval_map = {te.turn_index: te for te in ai_report.turns_evaluation}

        for turn in answered_turns:
            # Resolve Reference Answer & Evaluation Rubric (Independent, Zero Contamination)
            ref_payload = self.reference_service.resolve_reference_for_turn(
                turn=turn,
                parsed_jd_data=session.parsed_jd_data,
                resume_data=resume_data,
                focus_skills=session.focus_skills,
                target_role=session.target_role,
                seniority_level=session.seniority_level,
            )

            if not turn.ideal_answer and ref_payload.reference_answer:
                turn.ideal_answer = ref_payload.reference_answer

            # Deterministic & Semantic Evidence Analysis
            sem_result = self.semantic_engine.evaluate_turn_semantics(
                candidate_answer=turn.candidate_answer or "",
                reference_payload=ref_payload,
                question_text=turn.question_text,
                interview_focus=session.interview_focus,
            )

            local_nlp = analyze_speech_confidence(turn.candidate_answer or "")
            heuristic_conf = local_nlp["heuristic_confidence_score"]

            turn_ai_eval = turn_eval_map.get(turn.turn_index)
            if not turn_ai_eval and ai_report.turns_evaluation:
                # Fallback if specific turn was missing in AI map
                turn_ai_eval = ai_report.turns_evaluation[0]

            # 40% local filler-word heuristic + 60% Gemini assertiveness
            ai_conf = turn_ai_eval.confidence_score if turn_ai_eval else 50
            if sem_result.assigned_tier in (
                AnswerQualityTier.NON_ANSWER,
                AnswerQualityTier.EMPTY,
                AnswerQualityTier.PASS,
            ):
                blended_conf = 0
            else:
                blended_conf = max(
                    0,
                    min(
                        100,
                        round((0.40 * heuristic_conf) + (0.60 * ai_conf)),
                    ),
                )

            raw_ai_dict = (
                {
                    "relevance_score": turn_ai_eval.relevance_score,
                    "correctness_score": turn_ai_eval.correctness_score,
                    "keywords_score": turn_ai_eval.keywords_score,
                    "clarity_score": turn_ai_eval.clarity_score,
                    "confidence_score": blended_conf,
                    "answer_quality_tier": turn_ai_eval.answer_quality_tier,
                }
                if turn_ai_eval
                else None
            )

            # Authoritative Score Calibration (Phase 4.4)
            calibrated = self.score_calibrator.calibrate_turn(
                sem_result=sem_result,
                raw_ai_scores=raw_ai_dict,
                speech_confidence_score=blended_conf,
                interview_focus=session.interview_focus,
                is_candidate_specific=ref_payload.is_candidate_specific,
            )

            turn.relevance_score = calibrated.relevance_score
            turn.correctness_score = calibrated.correctness_score
            turn.keywords_score = calibrated.keywords_score
            turn.clarity_score = calibrated.clarity_score
            turn.confidence_score = calibrated.confidence_score
            turn.turn_score = calibrated.turn_score

            assigned_tier = calibrated.assigned_tier
            completeness = calibrated.completeness
            is_non_answer = (assigned_tier in (AnswerQualityTier.NON_ANSWER, AnswerQualityTier.PASS))
            is_empty = (assigned_tier == AnswerQualityTier.EMPTY)
            is_short_valid = (
                is_short_valid_answer(turn.candidate_answer)
                and sem_result.is_correct
                and completeness == CompletenessLevel.COMPLETE
            )
            classification_reason = sem_result.classification_reason

            covered_concepts = sem_result.covered_concepts
            missed_concepts = sem_result.missed_concepts
            concept_evidence = sem_result.concept_evidence
            contradicted_claims = sem_result.contradicted_claims
            unsupported_claims = sem_result.unsupported_claims

            tier_str = (
                assigned_tier.value
                if hasattr(assigned_tier, "value")
                else str(assigned_tier)
            )
            comp_str = (
                completeness.value
                if hasattr(completeness, "value")
                else str(completeness)
            )

            turn.evaluation_data = {
                "answer_quality_tier": tier_str,
                "classification_reason": classification_reason,
                "calibration_reason": calibrated.calibration_reason,
                "is_non_answer": is_non_answer,
                "is_empty": is_empty,
                "is_short_but_valid": is_short_valid,
                "covered_concepts": covered_concepts,
                "missed_concepts": missed_concepts,
                "expected_concepts": [ec.model_dump() for ec in ref_payload.expected_concepts],
                "concept_evidence": [ce.model_dump() for ce in concept_evidence],
                "completeness": comp_str,
                "contradicted_claims": contradicted_claims,
                "unsupported_claims": unsupported_claims,
                "reference_answer": ref_payload.reference_answer,
                "rubric": ref_payload.rubric.model_dump() if ref_payload.rubric else None,
                "reference_source": ref_payload.source,
                "is_candidate_specific": ref_payload.is_candidate_specific,
                "ideal_answer_comparison": turn_ai_eval.ideal_answer_comparison if turn_ai_eval else "",
                "turn_feedback": turn_ai_eval.turn_feedback if turn_ai_eval else "",
                "filler_word_stats": {
                    "count": local_nlp["filler_count"],
                    "density": local_nlp["filler_density"],
                    "detected": local_nlp["detected_fillers"],
                },
            }

        # 6. Calculate Session Aggregates (Radar Metrics + Overall Score)
        n = len(answered_turns)
        all_zero_turns = all((t.turn_score or 0) == 0 for t in answered_turns)
        all_non_answers = all(
            (t.evaluation_data or {}).get("answer_quality_tier") in (
                AnswerQualityTier.NON_ANSWER.value,
                AnswerQualityTier.EMPTY.value,
                AnswerQualityTier.PASS.value,
                AnswerQualityTier.IRRELEVANT.value,
            )
            for t in answered_turns
        )

        if all_zero_turns or all_non_answers:
            avg_rel = 0
            avg_corr = 0
            avg_kw = 0
            avg_cla = 0
            avg_conf = 0
            overall_score = 0
            dimension_scores = {
                "relevance": 0,
                "correctness": 0,
                "keywords": 0,
                "clarity": 0,
                "confidence": 0,
            }
            top_strengths = []
            top_improvements = [
                ImprovementItem(
                    title="Demonstrate Technical Domain Knowledge",
                    description=f"Candidate did not demonstrate substantive domain understanding during this {session.target_role} session.",
                    actionable_recommendation=f"Review fundamental engineering concepts, architectural principles, and trade-offs for {session.target_role}.",
                    evidence_turn_index=0,
                )
            ]
            exec_summary = (
                f"Candidate did not demonstrate technical knowledge for the questions asked during this {session.target_role} mock interview. "
                "Overall score is calibrated to 0 based on non-answers / lack of concept demonstration."
            )
        else:
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
            top_strengths = [s.model_dump() for s in ai_report.top_strengths]
            top_improvements = [i.model_dump() for i in ai_report.top_improvements]
            exec_summary = ai_report.executive_summary

        session.overall_score = overall_score
        session.dimension_scores = dimension_scores
        session.evaluation_report = {
            "top_strengths": [s if isinstance(s, dict) else s.model_dump() for s in top_strengths],
            "top_improvements": [i if isinstance(i, dict) else i.model_dump() for i in top_improvements],
            "executive_summary": exec_summary,
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
            tier_val = t_eval.get("answer_quality_tier")
            tier_enum = None
            if tier_val:
                try:
                    tier_enum = AnswerQualityTier(str(tier_val).lower())
                except ValueError:
                    tier_enum = None

            raw_expected = t_eval.get("expected_concepts", [])
            expected_concepts_list = []
            for item in raw_expected:
                if isinstance(item, dict):
                    expected_concepts_list.append(ExpectedConcept(**item))
                elif isinstance(item, ExpectedConcept):
                    expected_concepts_list.append(item)

            raw_evidence = t_eval.get("concept_evidence", [])
            concept_evidence_list = []
            for item in raw_evidence:
                if isinstance(item, dict):
                    concept_evidence_list.append(ConceptEvidence(**item))
                elif isinstance(item, ConceptEvidence):
                    concept_evidence_list.append(item)

            comp_val = t_eval.get("completeness")
            comp_enum = None
            if comp_val:
                try:
                    comp_enum = CompletenessLevel(str(comp_val).lower())
                except ValueError:
                    comp_enum = None

            ref_ans = t_eval.get("reference_answer") or t.ideal_answer

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
                    expected_concepts=expected_concepts_list,
                    concept_evidence=concept_evidence_list,
                    completeness=comp_enum,
                    contradicted_claims=t_eval.get("contradicted_claims", []),
                    unsupported_claims=t_eval.get("unsupported_claims", []),
                    reference_answer=ref_ans,
                    ideal_answer_comparison=t_eval.get("ideal_answer_comparison"),
                    turn_feedback=t_eval.get("turn_feedback"),
                    answer_quality_tier=tier_enum,
                    classification_reason=t_eval.get("classification_reason"),
                )
            )

        return SessionEvaluationReportResponse(
            session_id=session.id,
            target_role=session.target_role,
            seniority_level=session.seniority_level,
            interview_focus=session.interview_focus,
            practice_mode=session.practice_mode,
            preferred_language=getattr(session, "preferred_language", "en") or "en",
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
