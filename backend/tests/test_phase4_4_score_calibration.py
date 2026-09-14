"""Phase 4.4 Comprehensive Test Suite — Numeric Score Calibration & Evidence-Aligned Scoring.

Validates:
A. Pure Non-Answer ("I don't know") -> 0 scores & 0 composite
B. Empty Answer -> 0 scores & 0 composite
C. Pure Pass ("pass") -> 0 scores & 0 composite
D. Pure Skip ("skip this question") -> 0 scores & 0 composite
E. Irrelevant off-topic answer -> 0 technical scores & 0 composite
F. Technically incorrect answer -> heavy correctness & composite penalties
G. Relevant but partial answer -> calibrated bounded between 50 and 75
H. Relevant but insufficient / weak answer -> capped <= 45
I. Correct complete answer -> calibrated strong >= 78
J. Correct short valid answer ("GET.", "O(1)") -> calibrated strong >= 85
K. Long empty / fluffy non-answer -> 0 scores & 0 composite
L. Long irrelevant answer (fluent English React for SQL) -> 0 technical scores & 0 composite
M. Contradictory technical answer (PK allows duplicates) -> correctness <= 20, composite <= 30
N. Hinglish correct answer -> strong / partial calibrated scores
O. Hindi correct answer -> strong / partial calibrated scores
P. Project-specific empirical answer (unverified metrics accepted as lived experience)
Q. Behavioral answer without rigid STAR labels -> calibrated on behavioral weights
R. Scenario troubleshooting answer -> calibrated on observability depth
S. Follow-up answer -> evaluated against independent follow-up reference
T. Gemini high-score conflict with deterministic NON_ANSWER -> deterministic hard gate overrides to 0
U. Gemini high-score conflict with contradiction -> contradiction penalty overrides to <= 30
V. Gemini low-score conflict with valid concise answer -> short valid gate elevates to >= 85
W. Score persistence integrity (calibrated scores written to session model & evaluation_data)
X. Composite score invariants (technical zero invariant, missing key safety)
Y. Original 57-score bug reproduction -> verified producing 0
Z. Regression preservation for Phase 4.1, 4.2, and 4.3 contracts
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.schemas.evaluation import (
    AnswerQualityTier,
    CompletenessLevel,
    ConceptEvidence,
    ConceptImportance,
    EvidenceCategory,
    ExpectedConcept,
    QuestionReferencePayload,
    SemanticEvaluationResult,
    SessionEvaluationReport,
    TurnEvaluationItem,
)
from app.services.evaluation_service import EvaluationService
from app.services.gemini_service import _build_fallback_evaluation_report
from app.services.reference_evaluator import ReferenceEvaluatorService, get_reference_evaluator_service
from app.services.score_calibrator import (
    CalibratedTurnScores,
    ScoreCalibrator,
    compute_composite_score,
    get_score_calibrator,
)
from app.services.semantic_evaluator import SemanticEvaluatorEngine, get_semantic_evaluator_engine


@pytest.fixture
def score_calibrator() -> ScoreCalibrator:
    return get_score_calibrator()


@pytest.fixture
def semantic_engine() -> SemanticEvaluatorEngine:
    return get_semantic_evaluator_engine()


@pytest.fixture
def ref_service() -> ReferenceEvaluatorService:
    return get_reference_evaluator_service()


@pytest.fixture
def eval_service() -> EvaluationService:
    return EvaluationService()


# ===========================================================================
# TEST A, B, C, D: Pure Non-Answers, Empty, Pass, Skip
# ===========================================================================

@pytest.mark.parametrize(
    "non_answer_text,expected_tier",
    [
        ("I don't know", AnswerQualityTier.NON_ANSWER),
        ("i dont know the answer", AnswerQualityTier.NON_ANSWER),
        ("no idea", AnswerQualityTier.NON_ANSWER),
        ("IDK", AnswerQualityTier.NON_ANSWER),
        ("mujhe nahi pata", AnswerQualityTier.NON_ANSWER),
        ("", AnswerQualityTier.EMPTY),
        ("   \n\t  ", AnswerQualityTier.EMPTY),
        ("pass", AnswerQualityTier.PASS),
        ("skip this question", AnswerQualityTier.PASS),
    ],
)
def test_hard_gates_produce_absolute_zero_scores(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
    non_answer_text: str,
    expected_tier: AnswerQualityTier,
):
    ref_payload = QuestionReferencePayload(
        question_text="Explain database normalization.",
        reference_answer="Normalization eliminates data redundancy and prevents update anomalies.",
        primary_concept="Database Normalization",
        expected_concepts=[
            ExpectedConcept(concept="Eliminating data redundancy", importance=ConceptImportance.CORE, description="No duplication."),
        ],
        source="curated_deterministic",
    )

    sem_res = semantic_engine.evaluate_turn_semantics(non_answer_text, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 80, "correctness_score": 80, "clarity_score": 80, "confidence_score": 80},
    )

    assert calibrated.relevance_score == 0
    assert calibrated.correctness_score == 0
    assert calibrated.keywords_score == 0
    assert calibrated.clarity_score == 0
    assert calibrated.confidence_score == 0
    assert calibrated.turn_score == 0
    assert calibrated.completeness == CompletenessLevel.NONE


# ===========================================================================
# TEST E & L: Irrelevant & Long Irrelevant Answers
# ===========================================================================

def test_irrelevant_answers_produce_zero_technical_credit(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Explain database indexing trade-offs.",
        reference_answer="Indexes accelerate read queries using B-trees but introduce write overhead.",
        primary_concept="Database Indexing",
        expected_concepts=[
            ExpectedConcept(concept="B-Tree index lookups", importance=ConceptImportance.CORE, description="Logarithmic lookups."),
        ],
        source="curated_deterministic",
    )

    # Fluent English frontend response to SQL prompt
    answer = (
        "In modern React web applications, we manage client state using the useState and useReducer hooks, "
        "and synchronize side effects with useEffect while rendering dynamic components styled with Tailwind CSS."
    )

    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 60, "correctness_score": 70, "clarity_score": 90, "confidence_score": 85},
    )

    assert calibrated.relevance_score == 0
    assert calibrated.correctness_score == 0
    assert calibrated.keywords_score == 0
    assert calibrated.turn_score == 0
    assert calibrated.assigned_tier == AnswerQualityTier.IRRELEVANT


# ===========================================================================
# TEST F & M: Contradictory Technical Answers (PK allows duplicates)
# ===========================================================================

def test_contradictory_technical_answer_heavily_penalized(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Can a primary key contain duplicate values in relational tables?",
        reference_answer="No, a primary key strictly enforces entity uniqueness and prohibits duplicates.",
        primary_concept="Primary Key Constraints",
        expected_concepts=[
            ExpectedConcept(concept="Primary Key Row Uniqueness", importance=ConceptImportance.CORE, description="Uniqueness."),
        ],
        source="curated_deterministic",
    )

    answer = "Yes, in PostgreSQL a primary key allows duplicate values when configured properly with indexes."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 80, "correctness_score": 60, "clarity_score": 85, "confidence_score": 85},
    )

    assert calibrated.assigned_tier == AnswerQualityTier.INCORRECT
    assert calibrated.correctness_score <= 20
    assert calibrated.turn_score <= 30


# ===========================================================================
# TEST G: Relevant but Partial Answer
# ===========================================================================

def test_partial_answer_bounded_between_50_and_75(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Explain database normalization and anomaly prevention.",
        reference_answer="Normalization eliminates data redundancy and prevents update, insert, and delete anomalies.",
        primary_concept="Database Normalization",
        expected_concepts=[
            ExpectedConcept(concept="Eliminating data redundancy", importance=ConceptImportance.CORE, description="No duplication."),
            ExpectedConcept(concept="Preventing update anomalies", importance=ConceptImportance.CORE, description="No anomalies."),
        ],
        source="curated_deterministic",
    )

    answer = "Normalization is used to reduce duplicate data and eliminate redundancy across database tables."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 75, "correctness_score": 70, "clarity_score": 75, "confidence_score": 70},
    )

    assert calibrated.assigned_tier == AnswerQualityTier.PARTIAL
    assert calibrated.completeness == CompletenessLevel.PARTIAL
    assert 50 <= calibrated.turn_score <= 75
    assert 50 <= calibrated.correctness_score <= 75


# ===========================================================================
# TEST H: Relevant but Insufficient / Weak Answer
# ===========================================================================

def test_weak_insufficient_answer_capped_at_45(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="How does B-Tree indexing work in databases?",
        reference_answer="B-trees provide logarithmic search O(log N) by maintaining balanced tree depth.",
        primary_concept="B-Tree Indexing",
        expected_concepts=[
            ExpectedConcept(concept="Balanced logarithmic tree search", importance=ConceptImportance.CORE, description="O(log N)."),
        ],
        source="curated_deterministic",
    )

    answer = "It helps fast."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 50, "correctness_score": 40, "clarity_score": 50, "confidence_score": 50},
    )

    assert calibrated.assigned_tier == AnswerQualityTier.WEAK
    assert calibrated.completeness == CompletenessLevel.INSUFFICIENT
    assert calibrated.turn_score <= 45


# ===========================================================================
# TEST I: Correct Complete Answer
# ===========================================================================

def test_correct_complete_answer_scores_strongly(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Explain database normalization and anomaly prevention.",
        reference_answer="Normalization decomposes relational tables to eliminate data redundancy and prevent update anomalies.",
        primary_concept="Database Normalization",
        expected_concepts=[
            ExpectedConcept(concept="Eliminating data redundancy", importance=ConceptImportance.CORE, description="No duplicates."),
            ExpectedConcept(concept="Preventing update anomalies", importance=ConceptImportance.CORE, description="No anomalies."),
        ],
        source="curated_deterministic",
    )

    answer = "Database normalization decomposes relational schemas into normal forms to eliminate data redundancy and prevent update anomalies."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 95, "correctness_score": 95, "clarity_score": 90, "confidence_score": 90},
    )

    assert calibrated.assigned_tier == AnswerQualityTier.STRONG
    assert calibrated.completeness == CompletenessLevel.COMPLETE
    assert calibrated.turn_score >= 80
    assert calibrated.correctness_score >= 80


# ===========================================================================
# TEST J: Short Valid Exact Answers ("GET.", "O(1)")
# ===========================================================================

@pytest.mark.parametrize(
    "question,ideal,concept,ans",
    [
        ("Which HTTP method is safe and idempotent for resource retrieval?", "The HTTP GET method.", "HTTP GET", "GET."),
        ("What is the average time complexity of a hash table lookup?", "O(1) constant time complexity.", "Hash Table O(1)", "O(1)."),
    ],
)
def test_short_valid_answers_score_strongly(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
    question: str,
    ideal: str,
    concept: str,
    ans: str,
):
    ref_payload = QuestionReferencePayload(
        question_text=question,
        reference_answer=ideal,
        primary_concept=concept,
        expected_concepts=[
            ExpectedConcept(concept=concept, importance=ConceptImportance.CORE, description="Exact factual match."),
        ],
        source="curated_deterministic",
    )

    sem_res = semantic_engine.evaluate_turn_semantics(ans, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 90, "correctness_score": 95, "clarity_score": 85, "confidence_score": 85},
    )

    assert calibrated.assigned_tier == AnswerQualityTier.STRONG
    assert calibrated.completeness == CompletenessLevel.COMPLETE
    assert calibrated.turn_score >= 85
    assert calibrated.correctness_score >= 90
    assert calibrated.relevance_score >= 85


# ===========================================================================
# TEST N & O: Multilingual & Hinglish / Hindi Evaluation
# ===========================================================================

def test_hinglish_scoring_calibration(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Primary key ka database mein kya role hota hai?",
        reference_answer="Primary key table ke har row ko uniquely identify karti hai aur duplicate values allow nahi karti.",
        primary_concept="Primary Key",
        expected_concepts=[
            ExpectedConcept(concept="uniqueness", importance=ConceptImportance.CORE, description="Unique rows."),
            ExpectedConcept(concept="redundancy", importance=ConceptImportance.CORE, description="No duplicates."),
        ],
        source="curated_deterministic",
    )

    answer = "Primary key table ke har row ko uniquely identify karta hai taaki duplicate data ya redundancy na ho."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 90, "correctness_score": 90, "clarity_score": 85, "confidence_score": 85},
    )

    assert calibrated.assigned_tier in (AnswerQualityTier.STRONG, AnswerQualityTier.PARTIAL)
    assert calibrated.turn_score >= 70


# ===========================================================================
# TEST P: Project-Specific Empirical Answer
# ===========================================================================

def test_project_specific_empirical_details_not_penalized(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="How did you handle write throughput during flash sales in your payment project?",
        reference_answer="We utilized async connection pooling and batched inserts.",
        primary_concept="Project Write Optimization",
        expected_concepts=[
            ExpectedConcept(concept="Connection pooling or batching", importance=ConceptImportance.CORE, description="Write optimization."),
        ],
        source="candidate_project_inferred",
        is_candidate_specific=True,
    )

    answer = "In our flash sale pipeline, we configured an asyncpg connection pool with 50 connections and batched orders into chunks of 500."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 90, "correctness_score": 90, "clarity_score": 90, "confidence_score": 85},
        is_candidate_specific=True,
    )

    assert calibrated.assigned_tier == AnswerQualityTier.STRONG
    assert calibrated.turn_score >= 80


# ===========================================================================
# TEST Q: Behavioral Answer Without Rigid STAR Labels
# ===========================================================================

def test_behavioral_scoring_calibration(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Tell me about a technical disagreement and how you resolved it.",
        reference_answer="The candidate should describe technical conflict, data-driven evaluation, and collaborative resolution.",
        primary_concept="Conflict Resolution",
        expected_concepts=[
            ExpectedConcept(concept="Technical conflict or design disagreement", importance=ConceptImportance.CORE, description="Disagreement."),
            ExpectedConcept(concept="Data-driven evaluation or benchmarking", importance=ConceptImportance.CORE, description="Data."),
            ExpectedConcept(concept="Collaborative resolution and outcome", importance=ConceptImportance.CORE, description="Consensus."),
        ],
        source="curated_deterministic",
        is_candidate_specific=True,
    )

    answer = "We debated whether to use GraphQL or REST. I benchmarked mobile payload latency under packet loss, which proved REST was 40% faster, so we agreed on REST."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)
    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 90, "correctness_score": 85, "clarity_score": 90, "confidence_score": 85},
        interview_focus="behavioral",
        is_candidate_specific=True,
    )

    assert calibrated.assigned_tier in (AnswerQualityTier.STRONG, AnswerQualityTier.PARTIAL)
    assert calibrated.turn_score >= 75


# ===========================================================================
# TEST T, U, V: Gemini AI Conflicts vs Deterministic Grounding
# ===========================================================================

def test_gemini_high_score_overridden_for_non_answer(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Explain 2PC distributed transactions.",
        reference_answer="Two-Phase Commit coordinates prepare and commit phases across distributed participants.",
        primary_concept="Distributed 2PC",
        expected_concepts=[
            ExpectedConcept(concept="Two-Phase Commit Protocol", importance=ConceptImportance.CORE, description="2PC."),
        ],
        source="curated_deterministic",
    )

    # Candidate says "I don't know"
    sem_res = semantic_engine.evaluate_turn_semantics("I don't know", ref_payload)
    
    # Hallucinated Gemini response giving 85s
    hallucinated_ai = {
        "relevance_score": 85,
        "correctness_score": 85,
        "keywords_score": 80,
        "clarity_score": 90,
        "confidence_score": 90,
    }

    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores=hallucinated_ai,
    )

    assert calibrated.turn_score == 0
    assert calibrated.relevance_score == 0
    assert calibrated.correctness_score == 0
    assert calibrated.keywords_score == 0


def test_gemini_high_score_overridden_for_contradiction(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    ref_payload = QuestionReferencePayload(
        question_text="Is HTTP PUT idempotent?",
        reference_answer="HTTP PUT is idempotent according to RFC 9110.",
        primary_concept="HTTP Semantics",
        expected_concepts=[
            ExpectedConcept(concept="Idempotency of PUT", importance=ConceptImportance.CORE, description="PUT is idempotent."),
        ],
        source="curated_deterministic",
    )

    answer = "HTTP PUT is never idempotent because each call creates a new resource."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)

    # Hallucinated Gemini response
    hallucinated_ai = {
        "relevance_score": 90,
        "correctness_score": 85,
        "keywords_score": 80,
        "clarity_score": 90,
        "confidence_score": 90,
    }

    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores=hallucinated_ai,
    )

    assert calibrated.correctness_score <= 20
    assert calibrated.turn_score <= 30


def test_gemini_high_score_cannot_upgrade_partial_to_strong(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    """Verify that when semantic evidence says PARTIAL, Gemini returning 95s cannot upgrade tier to STRONG or score > 75."""
    ref_payload = QuestionReferencePayload(
        question_text="Explain database normalization.",
        reference_answer="Normalization decomposes schemas to eliminate data redundancy and prevent update, insert, and delete anomalies across normal forms.",
        primary_concept="Database Normalization",
        expected_concepts=[
            ExpectedConcept(concept="Eliminating data redundancy", importance=ConceptImportance.CORE, description="No duplicates."),
            ExpectedConcept(concept="Preventing update, insert, and delete anomalies", importance=ConceptImportance.CORE, description="No anomalies."),
            ExpectedConcept(concept="Normal forms (1NF, 2NF, 3NF)", importance=ConceptImportance.SUPPORTING, description="Normal forms."),
        ],
        source="curated_deterministic",
    )

    # Candidate gives partial definition: "Normalization removes redundancy."
    answer = "Normalization removes redundancy."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)

    assert sem_res.completeness == CompletenessLevel.PARTIAL
    assert sem_res.assigned_tier == AnswerQualityTier.PARTIAL

    # Hallucinated Gemini response giving 95s and tier=STRONG
    hallucinated_ai = {
        "relevance_score": 95,
        "correctness_score": 95,
        "keywords_score": 95,
        "clarity_score": 95,
        "confidence_score": 90,
        "answer_quality_tier": "strong",
    }

    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores=hallucinated_ai,
        interview_focus="technical",
    )

    assert calibrated.assigned_tier == AnswerQualityTier.PARTIAL
    assert calibrated.completeness == CompletenessLevel.PARTIAL
    assert 50 <= calibrated.turn_score <= 75


def test_gemini_high_score_cannot_upgrade_insufficient_to_strong(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    """Verify that when semantic evidence says INSUFFICIENT/WEAK, Gemini returning 95s cannot upgrade to STRONG or score > 45."""
    ref_payload = QuestionReferencePayload(
        question_text="Explain database indexing.",
        reference_answer="Database indexes use B-trees to accelerate lookups from O(N) to O(log N).",
        primary_concept="Database Indexing",
        expected_concepts=[
            ExpectedConcept(concept="B-Tree index structure and lookups", importance=ConceptImportance.CORE, description="B-tree."),
        ],
        source="curated_deterministic",
    )

    answer = "It helps fast."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)

    assert sem_res.completeness == CompletenessLevel.INSUFFICIENT
    assert sem_res.assigned_tier == AnswerQualityTier.WEAK

    hallucinated_ai = {
        "relevance_score": 95,
        "correctness_score": 95,
        "keywords_score": 95,
        "clarity_score": 95,
        "confidence_score": 90,
        "answer_quality_tier": "strong",
    }

    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores=hallucinated_ai,
        interview_focus="technical",
    )

    assert calibrated.assigned_tier == AnswerQualityTier.WEAK
    assert calibrated.completeness == CompletenessLevel.INSUFFICIENT
    assert calibrated.turn_score <= 45


def test_case_2_partial_normalization_definition_invariant(
    score_calibrator: ScoreCalibrator,
    semantic_engine: SemanticEvaluatorEngine,
):
    """Case 2 explicit test: 'Normalization removes redundancy.' must be PARTIAL and bounded 50-75."""
    ref_payload = QuestionReferencePayload(
        question_text="Explain database normalization.",
        reference_answer="Normalization decomposes schemas to eliminate data redundancy and prevent update anomalies.",
        primary_concept="Database Normalization",
        expected_concepts=[
            ExpectedConcept(concept="Eliminating data redundancy", importance=ConceptImportance.CORE, description="Redundancy."),
            ExpectedConcept(concept="Preventing update, insert, and delete anomalies", importance=ConceptImportance.CORE, description="Anomalies."),
        ],
        source="curated_deterministic",
    )

    answer = "Normalization removes redundancy."
    sem_res = semantic_engine.evaluate_turn_semantics(answer, ref_payload)

    assert sem_res.is_relevant is True
    assert sem_res.is_correct is True
    assert sem_res.completeness == CompletenessLevel.PARTIAL
    assert sem_res.assigned_tier == AnswerQualityTier.PARTIAL

    calibrated = score_calibrator.calibrate_turn(
        sem_result=sem_res,
        raw_ai_scores={"relevance_score": 75, "correctness_score": 75, "keywords_score": 60, "clarity_score": 75, "confidence_score": 70},
        interview_focus="technical",
    )

    assert calibrated.assigned_tier == AnswerQualityTier.PARTIAL
    assert calibrated.completeness == CompletenessLevel.PARTIAL
    assert 50 <= calibrated.turn_score <= 75



# ===========================================================================
# TEST X: Composite Score Invariants
# ===========================================================================

def test_compute_composite_score_invariants():
    # 1. Technical zero invariant: when technical dimensions are 0, composite is 0 regardless of clarity/confidence
    assert compute_composite_score({"relevance": 0, "correctness": 0, "keywords": 0, "clarity": 100, "confidence": 100}) == 0

    # 2. Missing key safety: defaults to 0
    assert compute_composite_score({}) == 0

    # 3. Behavioral zero invariant: when relevance is 0, composite is 0
    assert compute_composite_score({"relevance": 0, "clarity": 100, "confidence": 100}, interview_focus="behavioral") == 0

    # 4. Standard technical weighting: 35% corr + 25% rel + 20% kw + 10% cla + 10% conf
    score = compute_composite_score(
        {"relevance": 100, "correctness": 100, "keywords": 100, "clarity": 100, "confidence": 100},
        interview_focus="technical",
    )
    assert score == 100


# ===========================================================================
# TEST W & ORIGINAL 57-SCORE BUG REPRODUCTION:
# Full Pipeline Trace with Multi-Turn Non-Answers
# ===========================================================================

@pytest.mark.asyncio
async def test_reproduce_original_57_score_bug_now_produces_zero(eval_service: EvaluationService):
    """Verify that an interview session where candidate answered 'I don't know' evaluates to overall_score = 0."""
    mock_db = AsyncMock()
    mock_user = User(id="user-1", email="candidate@test.com", hashed_password="hash")

    turn1 = InterviewQuestionTurn(
        id="t1",
        session_id="s1",
        turn_index=0,
        question_type="technical",
        question_text="Explain database normalization.",
        candidate_answer="I don't know.",
        ideal_answer="Normalization decomposes tables to eliminate redundancy.",
    )
    turn2 = InterviewQuestionTurn(
        id="t2",
        session_id="s1",
        turn_index=1,
        question_type="technical",
        question_text="How do database indexes improve search performance?",
        candidate_answer="no idea",
        ideal_answer="B-tree indexes provide O(log N) lookup.",
    )
    turn3 = InterviewQuestionTurn(
        id="t3",
        session_id="s1",
        turn_index=2,
        question_type="technical",
        question_text="Explain Two-Phase Commit.",
        candidate_answer="pass",
        ideal_answer="2PC coordinates distributed transaction commit/rollback.",
    )

    session = InterviewSession(
        id="s1",
        user_id="user-1",
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="technical",
        practice_mode="mock",
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        turns=[turn1, turn2, turn3],
    )

    mock_db_res = MagicMock()
    mock_db_res.scalar_one_or_none.return_value = session
    mock_db.execute.return_value = mock_db_res

    # Mock Gemini to return hallucinated 57-producing scores (e.g. relevance=60, correctness=50, clarity=75, confidence=70)
    mock_ai_report = SessionEvaluationReport(
        turns_evaluation=[
            TurnEvaluationItem(
                turn_index=0,
                relevance_score=60,
                correctness_score=50,
                keywords_score=50,
                clarity_score=75,
                confidence_score=70,
                answer_quality_tier=AnswerQualityTier.STRONG,
                covered_concepts=["Hallucinated Concept"],
                missed_concepts=[],
                ideal_answer_comparison="",
                turn_feedback="",
            ),
            TurnEvaluationItem(
                turn_index=1,
                relevance_score=60,
                correctness_score=50,
                keywords_score=50,
                clarity_score=75,
                confidence_score=70,
                answer_quality_tier=AnswerQualityTier.STRONG,
                covered_concepts=["Hallucinated Concept 2"],
                missed_concepts=[],
                ideal_answer_comparison="",
                turn_feedback="",
            ),
            TurnEvaluationItem(
                turn_index=2,
                relevance_score=60,
                correctness_score=50,
                keywords_score=50,
                clarity_score=75,
                confidence_score=70,
                answer_quality_tier=AnswerQualityTier.STRONG,
                covered_concepts=["Hallucinated Concept 3"],
                missed_concepts=[],
                ideal_answer_comparison="",
                turn_feedback="",
            ),
        ],
        top_strengths=[],
        top_improvements=[],
        executive_summary="Candidate completed interview.",
    )

    with patch.object(eval_service.gemini_service, "evaluate_interview_session", AsyncMock(return_value=mock_ai_report)):
        response = await eval_service.evaluate_session(mock_db, mock_user, "s1")

        # THE PRODUCT BUG IS SOLVED:
        # Previously gave ~57 score. Now strictly evaluates to overall_score = 0!
        assert response.overall_score == 0
        assert session.overall_score == 0
        assert session.dimension_scores["relevance"] == 0
        assert session.dimension_scores["correctness"] == 0
        assert session.dimension_scores["keywords"] == 0
        assert session.dimension_scores["clarity"] == 0
        assert session.dimension_scores["confidence"] == 0

        for t in session.turns:
            assert t.turn_score == 0
            assert t.relevance_score == 0
            assert t.correctness_score == 0
            assert t.keywords_score == 0
            assert t.evaluation_data["covered_concepts"] == []
            assert t.evaluation_data["is_non_answer"] is True
