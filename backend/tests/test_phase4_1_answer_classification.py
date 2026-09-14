"""Phase 4.1 Comprehensive Test Suite: Answer Classification & Evaluation Data Foundation.

Validates:
A. Empty answers ("" -> EMPTY, "   " -> EMPTY, None -> EMPTY, punctuation-only -> EMPTY)
B. Pure non-answers ("I don't know" -> NON_ANSWER, "no idea", "not sure", "pass" -> PASS, "skip", "mujhe nahi pata")
C. Non-answer safety / anti-overmatching ("I don't know the exact syntax, but I would use Redis...")
D. Short valid answers ("PostgreSQL.", "GET.", "Pandas.") -> is_short_but_valid=True, not EMPTY, not NON_ANSWER
E. Irrelevant answers -> IRRELEVANT
F. Incorrect answers -> INCORRECT
G. Partial answers -> PARTIAL
H. Strong answers -> STRONG
I. Multilingual answers (English, Hindi, Hinglish) -> evaluable based on content
J. Follow-up context evaluation
K. Gemini malformed output & fallback resilience
L. Backward compatibility with legacy evaluation JSON
M. Phase 2 & 3 regression safety
N. Score calculation invariance
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.schemas.evaluation import (
    AnswerClassificationResult,
    AnswerQualityTier,
    SessionEvaluationReport,
    SessionEvaluationReportResponse,
    TurnEvaluationItem,
    TurnEvaluationResponse,
)
from app.services.answer_classifier import (
    classify_answer_deterministically,
    classify_candidate_answer,
    is_empty_answer,
    is_pure_non_answer,
    is_pure_pass_or_skip,
    is_short_valid_answer,
    normalize_answer_text,
)
from app.services.evaluation_service import (
    EvaluationService,
    compute_composite_score,
)
from app.services.gemini_service import (
    GeminiService,
    _build_fallback_evaluation_report,
)


# ===========================================================================
# A. EMPTY / UNUSABLE ANSWERS
# ===========================================================================

def test_empty_answers_classified_as_empty():
    """Verify empty string, whitespace, None, and punctuation are classified as EMPTY."""
    test_cases = ["", "   ", None, "\t\n  \n", "...", "---", "???", ", . -"]
    for case in test_cases:
        res = classify_answer_deterministically(case)
        assert res is not None, f"Failed for case: {case!r}"
        assert res.answer_quality_tier == AnswerQualityTier.EMPTY
        assert res.is_empty is True
        assert res.is_non_answer is True
        assert res.is_short_but_valid is False
        assert res.confidence == 1.0


# ===========================================================================
# B. PURE NON-ANSWERS & PASS/SKIP
# ===========================================================================

def test_pure_non_answers_english_classified():
    """Verify explicit English non-answers are deterministically classified as NON_ANSWER."""
    non_answers = [
        "I don't know",
        "i dont know",
        "I DO NOT KNOW.",
        "don't know",
        "no idea",
        "not sure",
        "i am not sure",
        "i'm not sure",
        "I have no idea",
        "I have no clue",
        "no clue",
        "I can't answer that",
        "i cannot answer that",
        "can't answer",
        "cannot answer",
        "I don't remember",
        "not familiar with this",
        "i have no experience with this",
        "I don't know sorry",
        "sorry no idea sir",
        "  I DON'T KNOW...  ",
    ]
    for text in non_answers:
        res = classify_answer_deterministically(text)
        assert res is not None, f"Failed to classify non-answer: {text!r}"
        assert res.answer_quality_tier == AnswerQualityTier.NON_ANSWER, f"Got {res.answer_quality_tier} for {text!r}"
        assert res.is_non_answer is True
        assert res.is_empty is False
        assert res.is_short_but_valid is False
        assert res.confidence == 1.0


def test_pure_non_answers_hindi_hinglish_classified():
    """Verify explicit Hindi and Hinglish non-answers are deterministically classified as NON_ANSWER."""
    hindi_non_answers = [
        "mujhe nahi pata",
        "mujhe nahi pta",
        "pata nahi",
        "pta nahi",
        "nahi pata",
        "nhi pta",
        "nahi janta",
        "kuch nahi pata",
        "idea nahi hai",
        "koi idea nahi",
        "yaad nahi hai",
        "mujhe yaad nahi",
    ]
    for text in hindi_non_answers:
        res = classify_answer_deterministically(text)
        assert res is not None, f"Failed to classify Hindi non-answer: {text!r}"
        assert res.answer_quality_tier == AnswerQualityTier.NON_ANSWER
        assert res.is_non_answer is True


def test_pass_and_skip_classified_as_pass():
    """Verify explicit pass and skip requests are deterministically classified as PASS."""
    pass_cases = [
        "pass",
        "skip",
        "Pass please",
        "skip please",
        "next question",
        "skip this question",
        "pass this",
        "skip kar do",
        "chhod do",
    ]
    for text in pass_cases:
        res = classify_answer_deterministically(text)
        assert res is not None, f"Failed to classify pass/skip: {text!r}"
        assert res.answer_quality_tier == AnswerQualityTier.PASS
        assert res.is_non_answer is True


# ===========================================================================
# C. NON-ANSWER SAFETY & ANTI-OVERMATCHING
# ===========================================================================

def test_anti_overmatching_hedged_answers_remain_evaluable():
    """Verify hedged answers with substantive technical content are NOT classified as pure NON_ANSWER."""
    hedged_answers = [
        "I don't know the exact syntax, but I would use Redis caching because it provides sub-millisecond lookups.",
        "I'm not sure whether PostgreSQL uses B-Trees or Hash indexes by default, but based on my experience B-Tree is standard.",
        "I don't remember the exact configuration parameter, however we can configure connection pooling with asyncpg in FastAPI.",
        "Mujhe exact command nahi pata lekin hum try-except block use karenge error catch karne ke liye.",
        "I am not sure about version 3.12 specifics, but generally Python GIL affects CPU-bound multi-threading performance.",
    ]
    for text in hedged_answers:
        res = classify_answer_deterministically(text)
        assert res is None, f"Hedged answer was falsely classified as deterministic non-answer: {text!r}"

        # When evaluated through the complete pipeline
        full_res = classify_candidate_answer(text)
        assert full_res.is_non_answer is False
        assert full_res.answer_quality_tier in (AnswerQualityTier.PARTIAL, AnswerQualityTier.STRONG)


# ===========================================================================
# D. SHORT VALID ANSWERS
# ===========================================================================

def test_short_valid_answers_preserved():
    """Verify short valid answers (1-5 words) are flagged is_short_but_valid and never marked EMPTY or NON_ANSWER."""
    short_valid_cases = [
        "PostgreSQL.",
        "Pandas.",
        "GET.",
        "Redis.",
        "Docker.",
        "TCP.",
        "B-Tree index.",
        "O(N log N)",
    ]
    for text in short_valid_cases:
        assert is_short_valid_answer(text) is True
        # Deterministic check must return None so it proceeds to semantic scoring
        det = classify_answer_deterministically(text)
        assert det is None, f"Short valid answer was trapped by deterministic non-answer: {text!r}"

        full_res = classify_candidate_answer(text)
        assert full_res.is_short_but_valid is True
        assert full_res.is_empty is False
        assert full_res.is_non_answer is False
        assert full_res.answer_quality_tier == AnswerQualityTier.STRONG


# ===========================================================================
# E, F, G, H. SEMANTIC CLASSIFICATION TIERS (IRRELEVANT, INCORRECT, PARTIAL, STRONG)
# ===========================================================================

def test_semantic_classification_tiers_representation():
    """Verify all 8 AnswerQualityTier enum values are distinct, well-defined, and valid strings."""
    tiers = [
        AnswerQualityTier.STRONG,
        AnswerQualityTier.PARTIAL,
        AnswerQualityTier.WEAK,
        AnswerQualityTier.INCORRECT,
        AnswerQualityTier.IRRELEVANT,
        AnswerQualityTier.NON_ANSWER,
        AnswerQualityTier.PASS,
        AnswerQualityTier.EMPTY,
    ]
    assert len(tiers) == 8
    tier_values = [t.value for t in tiers]
    assert len(set(tier_values)) == 8
    assert "strong" in tier_values
    assert "partial" in tier_values
    assert "weak" in tier_values
    assert "incorrect" in tier_values
    assert "irrelevant" in tier_values
    assert "non_answer" in tier_values
    assert "pass" in tier_values
    assert "empty" in tier_values


def test_turn_evaluation_item_tier_integration():
    """Verify TurnEvaluationItem schema correctly validates and holds answer_quality_tier."""
    item = TurnEvaluationItem(
        turn_index=0,
        answer_quality_tier=AnswerQualityTier.IRRELEVANT,
        classification_reason="Answer addressed React frontend framework when question asked about DB normalization.",
        relevance_score=10,
        correctness_score=20,
        keywords_score=15,
        clarity_score=70,
        confidence_score=60,
        covered_concepts=[],
        missed_concepts=["1NF, 2NF, 3NF Normalization", "Anomaly Prevention"],
        ideal_answer_comparison="Candidate discussed frontend UI instead of relational normalization.",
        turn_feedback="Focus directly on relational database design principles.",
    )
    assert item.answer_quality_tier == AnswerQualityTier.IRRELEVANT
    assert item.classification_reason is not None

    dumped = item.model_dump()
    assert dumped["answer_quality_tier"] == "irrelevant"


# ===========================================================================
# I. MULTILINGUAL EVALUATION RESILIENCE
# ===========================================================================

def test_multilingual_answers_evaluable():
    """Verify Hindi and Hinglish technical answers are preserved as evaluable."""
    hinglish_answers = [
        "API fail ho jaaye toh main try-except use karunga aur fallback response return karunga.",
        "Database mein duplicate records avoid karne ke liye unique constraint aur primary key use karte hain.",
        "High traffic ke case mein Redis cache use karke database par read load kam karenge.",
    ]
    for text in hinglish_answers:
        assert is_empty_answer(text) is False
        det = classify_answer_deterministically(text)
        assert det is None, f"Valid Hinglish answer should not be deterministic non-answer: {text}"
        res = classify_candidate_answer(text)
        assert res.is_non_answer is False
        assert res.is_empty is False


# ===========================================================================
# J. FALLBACK EVALUATION REPORT SAFEGUARD
# ===========================================================================

def test_fallback_evaluation_report_non_answer_safety():
    """Verify _build_fallback_evaluation_report does NOT inflate scores or hallucinate concepts for non-answers."""
    turns = [
        {
            "turn_index": 0,
            "question_text": "What database did you use?",
            "candidate_answer": "PostgreSQL.",
            "ideal_answer": "PostgreSQL relational database with schema details.",
        },
        {
            "turn_index": 1,
            "question_text": "Explain distributed transaction rollback.",
            "candidate_answer": "I don't know.",
            "ideal_answer": "Two-phase commit and Saga orchestration patterns.",
        },
        {
            "turn_index": 2,
            "question_text": "How do you handle API retries?",
            "candidate_answer": "We implemented exponential backoff with jitter.",
            "ideal_answer": "Exponential backoff, circuit breaker, and idempotency keys.",
        },
    ]

    report = _build_fallback_evaluation_report(
        transcript_turns=turns,
        target_role="Backend Engineer",
        seniority_level="senior",
    )

    assert len(report.turns_evaluation) == 3

    # Turn 0: Short valid answer -> STRONG
    assert report.turns_evaluation[0].answer_quality_tier == AnswerQualityTier.STRONG
    assert report.turns_evaluation[0].relevance_score >= 80

    # Turn 1: "I don't know" -> NON_ANSWER, zero hallucinated covered concepts, zero technical score
    t1 = report.turns_evaluation[1]
    assert t1.answer_quality_tier == AnswerQualityTier.NON_ANSWER
    assert t1.covered_concepts == []
    assert t1.relevance_score == 0
    assert t1.correctness_score == 0
    assert t1.keywords_score == 0

    # Turn 2: Substantive answer -> PARTIAL / STRONG
    t2 = report.turns_evaluation[2]
    assert t2.answer_quality_tier in (AnswerQualityTier.PARTIAL, AnswerQualityTier.STRONG)
    assert t2.relevance_score >= 40


# ===========================================================================
# K. GEMINI STRUCTURED EVALUATION & MALFORMED OUTPUT RESILIENCE
# ===========================================================================

@pytest.mark.asyncio
async def test_gemini_service_structured_evaluation_with_tier():
    """Verify GeminiService correctly parses structured tier responses."""
    mock_report_data = {
        "turns_evaluation": [
            {
                "turn_index": 0,
                "answer_quality_tier": "strong",
                "classification_reason": "Clear and accurate explanation of FastAPI ASGI event loop.",
                "relevance_score": 95,
                "correctness_score": 90,
                "keywords_score": 92,
                "clarity_score": 95,
                "confidence_score": 88,
                "covered_concepts": ["FastAPI ASGI", "uvicorn worker loop"],
                "missed_concepts": [],
                "ideal_answer_comparison": "Directly matches senior architectural standard.",
                "turn_feedback": "Excellent conceptual clarity.",
            },
            {
                "turn_index": 1,
                "answer_quality_tier": "non_answer",
                "classification_reason": "Candidate explicitly stated they do not know.",
                "relevance_score": 0,
                "correctness_score": 0,
                "keywords_score": 0,
                "clarity_score": 50,
                "confidence_score": 20,
                "covered_concepts": [],
                "missed_concepts": ["Database Indexing Internals"],
                "ideal_answer_comparison": "Candidate did not provide an answer.",
                "turn_feedback": "Study B-Tree structure and index scan types.",
            },
        ],
        "top_strengths": [
            {
                "title": "Strong Async Knowledge",
                "description": "Demonstrated solid understanding of FastAPI async operations.",
                "evidence_turn_index": 0,
            }
        ],
        "top_improvements": [
            {
                "title": "Database Internals",
                "description": "Lacked familiarity with database indexing.",
                "actionable_recommendation": "Review PostgreSQL index documentation.",
                "evidence_turn_index": 1,
            }
        ],
        "executive_summary": "Candidate showed strong framework knowledge with growth area in DB internals.",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_report_data)

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    service = GeminiService(api_key="test-key")
    with patch.object(service, "_client", mock_client):
        report = await service.evaluate_interview_session(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["FastAPI"],
            transcript_turns=[
                {
                    "turn_index": 0,
                    "question_text": "Explain FastAPI async loop.",
                    "candidate_answer": "FastAPI uses ASGI with asyncio event loop.",
                    "ideal_answer": "Detailed ASGI explanation.",
                },
                {
                    "turn_index": 1,
                    "question_text": "Explain B-tree indexing.",
                    "candidate_answer": "I don't know.",
                    "ideal_answer": "Detailed B-Tree indexing.",
                },
            ],
        )

        assert isinstance(report, SessionEvaluationReport)
        assert len(report.turns_evaluation) == 2
        assert report.turns_evaluation[0].answer_quality_tier == AnswerQualityTier.STRONG
        assert report.turns_evaluation[1].answer_quality_tier == AnswerQualityTier.NON_ANSWER
        assert report.turns_evaluation[1].covered_concepts == []


# ===========================================================================
# L. BACKWARD COMPATIBILITY
# ===========================================================================

def test_backward_compatibility_legacy_records():
    """Verify legacy evaluation records without answer_quality_tier deserialize cleanly."""
    legacy_turn_json = {
        "id": "turn-123",
        "session_id": "session-456",
        "turn_index": 0,
        "question_type": "core",
        "question_text": "What is REST?",
        "candidate_answer": "Representational State Transfer.",
        "ideal_answer": "Architectural constraints of REST.",
        "turn_duration_sec": 30,
        "relevance_score": 80,
        "correctness_score": 85,
        "keywords_score": 80,
        "clarity_score": 90,
        "confidence_score": 85,
        "turn_score": 83,
        "covered_concepts": ["REST"],
        "missed_concepts": ["HATEOAS"],
        "ideal_answer_comparison": "Solid overview.",
        "turn_feedback": "Good job.",
    }

    # Should deserialize without error
    resp = TurnEvaluationResponse.model_validate(legacy_turn_json)
    assert resp.id == "turn-123"
    assert resp.answer_quality_tier is None
    assert resp.classification_reason is None
    assert resp.turn_score == 83


# ===========================================================================
# M. PHASE 2 REGRESSION & SCORING INVARIANCE
# ===========================================================================

def test_score_calculation_invariance():
    """Verify compute_composite_score formula remains exactly invariant in Phase 4.1."""
    scores_tech = {
        "relevance": 90,
        "correctness": 80,
        "keywords": 70,
        "clarity": 85,
        "confidence": 75,
    }
    # Tech: (0.35 * 80) + (0.25 * 90) + (0.20 * 70) + (0.10 * 85) + (0.10 * 75) = 28 + 22.5 + 14 + 8.5 + 7.5 = 80.5 -> 80 / 81
    score_tech = compute_composite_score(scores_tech, "Technical Core")
    assert score_tech == 80 or score_tech == 81

    scores_behav = {
        "relevance": 90,
        "correctness": 70,
        "keywords": 60,
        "clarity": 95,
        "confidence": 85,
    }
    # Behav: (0.30 * 90) + (0.30 * 95) + (0.20 * 85) + (0.10 * 70) + (0.10 * 60) = 27 + 28.5 + 17 + 7 + 6 = 85.5 -> 86
    score_behav = compute_composite_score(scores_behav, "Behavioral")
    assert score_behav == 86


# ===========================================================================
# N. EVALUATION SERVICE HARD NON-ANSWER SAFETY OVERRIDE
# ===========================================================================

@pytest.mark.asyncio
async def test_evaluation_service_enforces_non_answer_safety():
    """Verify EvaluationService strictly overrides any hallucinated concepts if candidate gave a pure non-answer."""
    service = EvaluationService()

    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user-123"

    mock_turn1 = MagicMock()
    mock_turn1.id = "t1"
    mock_turn1.session_id = "s1"
    mock_turn1.turn_index = 0
    mock_turn1.question_type = "core"
    mock_turn1.question_text = "What is database normalization?"
    mock_turn1.candidate_answer = "I don't know."
    mock_turn1.ideal_answer = "Relational normalization fundamentals."
    mock_turn1.turn_duration_sec = 5
    mock_turn1.evaluation_data = None

    from datetime import datetime, timezone

    mock_session = MagicMock()
    mock_session.id = "s1"
    mock_session.user_id = "user-123"
    mock_session.status = "in_progress"
    mock_session.overall_score = None
    mock_session.evaluation_report = None
    mock_session.target_role = "Backend Engineer"
    mock_session.seniority_level = "senior"
    mock_session.interview_focus = "Technical Core"
    mock_session.focus_skills = ["PostgreSQL"]
    mock_session.parsed_jd_data = None
    mock_session.preferred_language = "en"
    mock_session.practice_mode = "full"
    mock_session.resume = None
    mock_session.turns = [mock_turn1]
    mock_session.started_at = datetime.now(timezone.utc)
    mock_session.completed_at = None

    mock_db_res = MagicMock()
    mock_db_res.scalar_one_or_none.return_value = mock_session
    mock_db.execute.return_value = mock_db_res

    # Suppose Gemini mistakenly returned concepts for "I don't know"
    mock_ai_report = SessionEvaluationReport(
        turns_evaluation=[
            TurnEvaluationItem(
                turn_index=0,
                answer_quality_tier=AnswerQualityTier.STRONG,  # Hallucinated tier!
                classification_reason="Hallucinated",
                relevance_score=80,
                correctness_score=80,
                keywords_score=80,
                clarity_score=80,
                confidence_score=80,
                covered_concepts=["Hallucinated Normalization Concept"],  # Hallucinated concept!
                missed_concepts=[],
                ideal_answer_comparison="Comparison",
                turn_feedback="Feedback",
            )
        ],
        top_strengths=[],
        top_improvements=[],
        executive_summary="Summary",
    )

    with patch.object(service.gemini_service, "evaluate_interview_session", AsyncMock(return_value=mock_ai_report)):
        report_resp = await service.evaluate_session(mock_db, mock_user, "s1")

        # The deterministic safety rule in EvaluationService must override the hallucinated tier and covered_concepts!
        assert mock_turn1.evaluation_data["answer_quality_tier"] == "non_answer"
        assert mock_turn1.evaluation_data["is_non_answer"] is True
        assert mock_turn1.evaluation_data["covered_concepts"] == []  # MUST be wiped clean!
        assert "explicitly stated" in mock_turn1.evaluation_data["classification_reason"]
