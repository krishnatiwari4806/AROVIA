"""Score Calibration Engine — Evidence-Aligned, Intent-Calibrated Scoring.

Provides deterministic, grounded calibration of raw Gemini and heuristic evaluation scores
against authoritative semantic evidence (AnswerQualityTier, CompletenessLevel, ConceptEvidence,
factual contradictions, and unverified claims).
"""

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional

from app.schemas.evaluation import (
    AnswerQualityTier,
    CompletenessLevel,
    SemanticEvaluationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class CalibratedTurnScores:
    """Container for calibrated 5-dimensional turn scores and derived composite."""

    relevance_score: int
    correctness_score: int
    keywords_score: int
    clarity_score: int
    confidence_score: int
    turn_score: int
    assigned_tier: AnswerQualityTier
    completeness: CompletenessLevel
    calibration_reason: str


def compute_composite_score(scores: Dict[str, int], interview_focus: str = "technical") -> int:
    """Calculate focus-adaptive composite 0-100 score with strict zero-evidence gating.

    Technical Core & System Design:
        35% Correctness, 25% Relevance, 20% Key Concepts, 10% Clarity, 10% Confidence

    Behavioral:
        30% Relevance, 30% Clarity, 20% Confidence, 10% Correctness, 10% Key Concepts
    """
    rel = max(0, min(100, scores.get("relevance", 0)))
    corr = max(0, min(100, scores.get("correctness", 0)))
    kw = max(0, min(100, scores.get("keywords", 0)))
    cla = max(0, min(100, scores.get("clarity", 0)))
    conf = max(0, min(100, scores.get("confidence", 0)))

    # HARD SAFETY INVARIANT: If all substantive technical/subject matter dimensions are 0,
    # delivery fluency (clarity/confidence) CANNOT manufacture a score.
    if rel == 0 and corr == 0 and kw == 0:
        return 0

    focus = (interview_focus or "").lower()
    if "behavioral" in focus:
        # Behavioral focus: relevance + behavioral articulation
        if rel == 0:
            return 0
        raw = (
            (0.30 * rel)
            + (0.30 * cla)
            + (0.20 * conf)
            + (0.10 * corr)
            + (0.10 * kw)
        )
    else:
        # Technical Core, System Design, Scenario, etc.
        raw = (
            (0.35 * corr)
            + (0.25 * rel)
            + (0.20 * kw)
            + (0.10 * cla)
            + (0.10 * conf)
        )

    return max(0, min(100, round(raw)))


class ScoreCalibrator:
    """Authoritative score calibration engine enforcing semantic invariants across all 5 dimensions."""

    def calibrate_turn(
        self,
        sem_result: SemanticEvaluationResult,
        raw_ai_scores: Optional[Dict[str, int]] = None,
        speech_confidence_score: int = 50,
        interview_focus: str = "technical",
        is_candidate_specific: bool = False,
    ) -> CalibratedTurnScores:
        """Calibrate turn-level 5-dimensional scores against semantic evidence.

        Enforces authoritative tier bounds and prevents AI score hallucination / baseline leakage.
        """
        raw_ai = raw_ai_scores or {}
        tier = sem_result.assigned_tier
        completeness = sem_result.completeness
        contradictions = sem_result.contradicted_claims
        covered_count = len(sem_result.covered_concepts)
        missed_count = len(sem_result.missed_concepts)
        total_concepts = covered_count + missed_count or 1
        coverage_ratio = covered_count / total_concepts

        # Extract raw scores (defaulting safely to 0 if not provided)
        raw_rel = raw_ai.get("relevance_score", 0)
        raw_corr = raw_ai.get("correctness_score", 0)
        raw_kw = raw_ai.get("keywords_score", 0)
        raw_cla = raw_ai.get("clarity_score", 0)
        raw_conf = raw_ai.get("confidence_score", speech_confidence_score)

        # -------------------------------------------------------------------
        # GATE 1: Pure Non-Answer, Empty, or Pass/Skip
        # -------------------------------------------------------------------
        if tier in (AnswerQualityTier.NON_ANSWER, AnswerQualityTier.EMPTY, AnswerQualityTier.PASS):
            return CalibratedTurnScores(
                relevance_score=0,
                correctness_score=0,
                keywords_score=0,
                clarity_score=0,
                confidence_score=0,
                turn_score=0,
                assigned_tier=tier,
                completeness=CompletenessLevel.NONE,
                calibration_reason=f"Hard gate enforced: {tier.value} receives 0 across all dimensions and composite.",
            )

        # -------------------------------------------------------------------
        # GATE 2: Irrelevant / Completely Off-Topic Response
        # -------------------------------------------------------------------
        if tier == AnswerQualityTier.IRRELEVANT or not sem_result.is_relevant:
            # An off-topic answer (e.g. React for SQL) cannot receive technical credit.
            # Clarity may reflect English fluency capped at 30, but turn_score is 0.
            cal_cla = min(raw_cla, 30) if raw_cla else 20
            cal_conf = min(raw_conf, 25) if raw_conf else 20
            return CalibratedTurnScores(
                relevance_score=0,
                correctness_score=0,
                keywords_score=0,
                clarity_score=cal_cla,
                confidence_score=cal_conf,
                turn_score=0,
                assigned_tier=AnswerQualityTier.IRRELEVANT,
                completeness=CompletenessLevel.NONE,
                calibration_reason="Hard gate enforced: Irrelevant off-topic answer receives 0 relevance, correctness, keywords, and composite score.",
            )

        # -------------------------------------------------------------------
        # GATE 3: Short Valid Exact Answers (e.g. "GET.", "O(1)", "PostgreSQL.")
        # -------------------------------------------------------------------
        if (
            completeness == CompletenessLevel.COMPLETE
            and sem_result.is_correct
            and tier == AnswerQualityTier.STRONG
            and coverage_ratio >= 0.8
        ):
            cal_rel = max(85, min(100, raw_rel if raw_rel > 0 else 95))
            cal_corr = max(90, min(100, raw_corr if raw_corr > 0 else 95))
            cal_kw = max(80, min(100, raw_kw if raw_kw > 0 else 90))
            cal_cla = max(85, min(100, raw_cla if raw_cla > 0 else 90))
            cal_conf = max(75, min(100, raw_conf if raw_conf > 0 else 85))
            scores_dict = {
                "relevance": cal_rel,
                "correctness": cal_corr,
                "keywords": cal_kw,
                "clarity": cal_cla,
                "confidence": cal_conf,
            }
            comp_score = compute_composite_score(scores_dict, interview_focus)
            return CalibratedTurnScores(
                relevance_score=cal_rel,
                correctness_score=cal_corr,
                keywords_score=cal_kw,
                clarity_score=cal_cla,
                confidence_score=cal_conf,
                turn_score=max(85, comp_score),
                assigned_tier=AnswerQualityTier.STRONG,
                completeness=CompletenessLevel.COMPLETE,
                calibration_reason="Short valid answer verified: Calibrated to strong benchmark band (>= 85).",
            )

        # -------------------------------------------------------------------
        # GATE 4: Factual Contradictions & Material Technical Errors (INCORRECT)
        # -------------------------------------------------------------------
        if tier == AnswerQualityTier.INCORRECT or len(contradictions) > 0:
            # On-topic (relevance may be 40-75), but correctness is severely penalized
            cal_rel = max(40, min(75, raw_rel if raw_rel > 0 else 60))
            # Heavy penalty on correctness: max 20, minus 5 per additional contradiction
            contra_penalty = max(0, min(20, 20 - (len(contradictions) * 5)))
            cal_corr = max(0, min(contra_penalty, raw_corr if raw_corr > 0 else 15))
            cal_kw = max(20, min(45, raw_kw if raw_kw > 0 else 35))
            cal_cla = max(40, min(75, raw_cla if raw_cla > 0 else 60))
            cal_conf = max(30, min(70, raw_conf if raw_conf > 0 else 50))
            scores_dict = {
                "relevance": cal_rel,
                "correctness": cal_corr,
                "keywords": cal_kw,
                "clarity": cal_cla,
                "confidence": cal_conf,
            }
            comp_score = compute_composite_score(scores_dict, interview_focus)
            # Hard cap on incorrect answer composite score: cannot exceed 30
            final_turn_score = min(30, comp_score)
            return CalibratedTurnScores(
                relevance_score=cal_rel,
                correctness_score=cal_corr,
                keywords_score=cal_kw,
                clarity_score=cal_cla,
                confidence_score=cal_conf,
                turn_score=final_turn_score,
                assigned_tier=AnswerQualityTier.INCORRECT,
                completeness=CompletenessLevel.INSUFFICIENT,
                calibration_reason=f"Contradiction penalty enforced ({len(contradictions)} contradictions): Correctness capped <= {contra_penalty}, Composite capped <= 30.",
            )

        # -------------------------------------------------------------------
        # GATE 5: Weak / Extremely Incomplete (WEAK, INSUFFICIENT)
        # -------------------------------------------------------------------
        if tier == AnswerQualityTier.WEAK or completeness == CompletenessLevel.INSUFFICIENT:
            cal_rel = max(30, min(60, raw_rel if raw_rel > 0 else 50))
            cal_corr = max(20, min(45, raw_corr if raw_corr > 0 else 35))
            cal_kw = max(15, min(40, raw_kw if raw_kw > 0 else 30))
            cal_cla = max(40, min(70, raw_cla if raw_cla > 0 else 55))
            cal_conf = max(30, min(65, raw_conf if raw_conf > 0 else 50))
            scores_dict = {
                "relevance": cal_rel,
                "correctness": cal_corr,
                "keywords": cal_kw,
                "clarity": cal_cla,
                "confidence": cal_conf,
            }
            comp_score = compute_composite_score(scores_dict, interview_focus)
            # Weak answers cannot exceed 45
            final_turn_score = min(45, comp_score)
            return CalibratedTurnScores(
                relevance_score=cal_rel,
                correctness_score=cal_corr,
                keywords_score=cal_kw,
                clarity_score=cal_cla,
                confidence_score=cal_conf,
                turn_score=final_turn_score,
                assigned_tier=AnswerQualityTier.WEAK,
                completeness=CompletenessLevel.INSUFFICIENT,
                calibration_reason="Weak / Insufficient answer calibrated: Composite capped <= 45.",
            )

        # -------------------------------------------------------------------
        # GATE 6: Partial Concepts Covered (PARTIAL)
        # -------------------------------------------------------------------
        if tier == AnswerQualityTier.PARTIAL or completeness == CompletenessLevel.PARTIAL:
            # Scaled proportionally between 50 and 75 based on concept coverage ratio
            base_corr = round(70 + (10 * coverage_ratio)) if sem_result.is_correct else round(50 + (15 * coverage_ratio))
            base_kw = round(45 + (30 * coverage_ratio))
            cal_rel = max(65, min(85, raw_rel if raw_rel > 0 else 75))
            cal_corr = max(50, min(80, raw_corr if raw_corr > 0 else base_corr))
            cal_kw = max(45, min(75, raw_kw if raw_kw > 0 else base_kw))
            cal_cla = max(55, min(85, raw_cla if raw_cla > 0 else 75))
            cal_conf = max(50, min(85, raw_conf if raw_conf > 0 else speech_confidence_score))
            scores_dict = {
                "relevance": cal_rel,
                "correctness": cal_corr,
                "keywords": cal_kw,
                "clarity": cal_cla,
                "confidence": cal_conf,
            }
            comp_score = compute_composite_score(scores_dict, interview_focus)
            # Hard Invariant: Partial answers bounded strictly to 50 - 75 (cannot equal complete strong answer)
            final_turn_score = max(50, min(75, comp_score))
            return CalibratedTurnScores(
                relevance_score=cal_rel,
                correctness_score=cal_corr,
                keywords_score=cal_kw,
                clarity_score=cal_cla,
                confidence_score=cal_conf,
                turn_score=final_turn_score,
                assigned_tier=AnswerQualityTier.PARTIAL,
                completeness=CompletenessLevel.PARTIAL,
                calibration_reason="Partial coverage calibrated: Composite bounded between 50 and 75.",
            )

        # -------------------------------------------------------------------
        # GATE 7: Strong & Complete (STRONG, COMPLETE)
        # -------------------------------------------------------------------
        cal_rel = max(80, min(100, raw_rel if raw_rel > 0 else 90))
        cal_corr = max(80, min(100, raw_corr if raw_corr > 0 else 90))
        cal_kw = max(75, min(100, raw_kw if raw_kw > 0 else 85))
        cal_cla = max(75, min(100, raw_cla if raw_cla > 0 else 85))
        cal_conf = max(70, min(100, raw_conf if raw_conf > 0 else speech_confidence_score))
        scores_dict = {
            "relevance": cal_rel,
            "correctness": cal_corr,
            "keywords": cal_kw,
            "clarity": cal_cla,
            "confidence": cal_conf,
        }
        comp_score = compute_composite_score(scores_dict, interview_focus)
        final_turn_score = max(78, min(100, comp_score))
        return CalibratedTurnScores(
            relevance_score=cal_rel,
            correctness_score=cal_corr,
            keywords_score=cal_kw,
            clarity_score=cal_cla,
            confidence_score=cal_conf,
            turn_score=final_turn_score,
            assigned_tier=AnswerQualityTier.STRONG,
            completeness=CompletenessLevel.COMPLETE,
            calibration_reason="Strong & complete response calibrated to >= 78.",
        )


def get_score_calibrator() -> ScoreCalibrator:
    """Dependency provider for ScoreCalibrator."""
    return ScoreCalibrator()
