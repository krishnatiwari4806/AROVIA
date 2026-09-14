"""Comprehensive Unit & Integration Test Suite for Phase 4.5:
Adaptive Interview Realism, Semantic-Gap Probing, Conversational Continuity, and Multilingual Reinforcement.
"""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.schemas.evaluation import (
    AnswerQualityTier,
    CompletenessLevel,
    ConceptImportance,
    ExpectedConcept,
    ImprovementItem,
    QuestionReferencePayload,
    SemanticEvaluationResult,
    SessionEvaluationReport,
    StrengthItem,
    TurnEvaluationItem,
)
from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.candidate_context import build_candidate_context
from app.services.conversational_bridge import (
    BridgeType,
    ConversationalBridgeEngine,
    get_conversational_bridge_engine,
)
from app.services.gemini_service import (
    GeminiService,
    get_grounded_fallback_question,
    get_semantic_gap_fallback_followup,
)
from app.services.question_planner import (
    QuestionIntent,
    QuestionPlan,
    QuestionPlanner,
    get_question_planner,
)
from app.services.reference_evaluator import ReferenceEvaluatorService
from app.services.semantic_evaluator import SemanticEvaluatorEngine


# ============================================================================
# 1-4. CONVERSATIONAL BRIDGE ENGINE TESTS
# ============================================================================


def test_bridge_engine_all_types():
    """Verify bridge generation produces natural lead-ins for all defined BridgeTypes."""
    engine = get_conversational_bridge_engine()
    for b_type in BridgeType:
        bridge = engine.generate_bridge(
            bridge_type=b_type,
            candidate_answer="I used connection pooling and asyncpg to optimize database queries.",
            next_topic="Database Indexing Strategy",
            language="en",
        )
        assert isinstance(bridge, str)
        if b_type not in (BridgeType.DIRECT, BridgeType.INTRO_TO_CORE_1, BridgeType.INTRO_TO_FIRST_CORE):
            assert len(bridge) > 0


def test_bridge_grounding_no_hallucinations():
    """Verify bridge only uses provided terms and doesn't invent external technologies."""
    engine = ConversationalBridgeEngine()
    bridge = engine.generate_bridge(
        bridge_type=BridgeType.PROJECT_TO_TECHNICAL,
        candidate_answer="We built a payment gateway using FastAPI and PostgreSQL.",
        next_topic="Distributed Locking",
        language="en",
    )
    # Bridge should not hallucinate unmentioned technologies like Kubernetes, Kafka, AWS
    assert "Kubernetes" not in bridge
    assert "Kafka" not in bridge


def test_bridge_multilingual_hindi_and_hinglish():
    """Verify bridge generation in Hindi and Hinglish preserving technical terms in English."""
    engine = ConversationalBridgeEngine()

    hi_bridge = engine.generate_bridge(
        bridge_type=BridgeType.FOLLOWUP_TO_NEXT_CORE,
        next_topic="System Architecture",
        language="hi",
    )
    assert any(w in hi_bridge for w in ["dhanyawad", "shukriya", "technical", "aage", "chal"])

    hinglish_bridge = engine.generate_bridge(
        bridge_type=BridgeType.PROJECT_TO_TECHNICAL,
        next_topic="Database Optimization",
        language="hinglish",
    )
    assert any(w in hinglish_bridge for w in ["picture", "explaining", "architectural", "technical", "deeper"])


def test_bridge_intro_to_core():
    """Verify bridge for Turn 0 introduction transition."""
    engine = ConversationalBridgeEngine()
    bridge = engine.generate_bridge(
        bridge_type=BridgeType.INTRO_TO_CORE_1,
        candidate_answer="Hi, I am a backend developer with 4 years of Python and PostgreSQL experience.",
        language="en",
    )
    assert "background" in bridge.lower() or "intro" in bridge.lower() or "sharing" in bridge.lower()


# ============================================================================
# 5-13. SEMANTIC-GAP DRIVEN ADAPTIVE PROBING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_semantic_gap_followup_missing_core_concept_priority():
    """Mandatory Test: When multiple concepts are missing, follow-up strictly prioritizes missing CORE concept."""
    gemini = GeminiService()

    # Question expected connection pooling (SUPPORTING), batching (CORE), WAL tuning (SUPPORTING)
    ref_payload = QuestionReferencePayload(
        source="unit_test",
        reference_answer="Use connection pooling with asyncpg and batching queries for database performance.",
        primary_concept="Database Optimization",
        question_text="How did you optimize your database layer for high throughput?",
        expected_concepts=[
            ExpectedConcept(concept="connection pooling", importance=ConceptImportance.SUPPORTING),
            ExpectedConcept(concept="batching", importance=ConceptImportance.CORE),
            ExpectedConcept(concept="WAL tuning", importance=ConceptImportance.SUPPORTING),
        ],
    )
    # Candidate answered only connection pooling
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.PARTIAL,
        completeness=CompletenessLevel.PARTIAL,
        covered_concepts=["connection pooling"],
        missed_concepts=["batching", "WAL tuning"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Relevant to DB optimization.",
        correctness_reason="Connection pooling is technically sound.",
        completeness_reason="Omitted batching and WAL tuning.",
        classification_reason="Covered connection pooling but omitted batching and WAL tuning.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="technical",
            focus_skills=["Python", "PostgreSQL"],
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="How did you optimize your database layer for high throughput?",
            candidate_answer="I used connection pooling with asyncpg to manage persistent DB connections.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
            reference_payload=ref_payload,
        )

    assert decision.is_follow_up is True
    # The follow-up MUST target the missing CORE concept (batching), NOT the covered concept (connection pooling)
    assert "batching" in decision.question_text.lower()
    assert "connection pooling" not in decision.primary_concept.lower()


@pytest.mark.asyncio
async def test_strong_complete_advances_to_next_core():
    """Verify strong complete answer advances to next planned core question without redundant follow-up."""
    gemini = GeminiService()
    ref_payload = QuestionReferencePayload(
        source="unit_test",
        reference_answer="Complete explanation of database normalization and indexing.",
        primary_concept="Database Principles",
        question_text="Explain database normalization and indexing.",
        expected_concepts=[
            ExpectedConcept(concept="normalization", importance=ConceptImportance.CORE),
            ExpectedConcept(concept="indexing", importance=ConceptImportance.CORE),
        ],
    )
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.STRONG,
        completeness=CompletenessLevel.COMPLETE,
        covered_concepts=["normalization", "indexing"],
        missed_concepts=[],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Relevant to prompt.",
        correctness_reason="Technically accurate.",
        completeness_reason="All concepts covered.",
        classification_reason="Fully addressed all key concepts.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="technical",
            focus_skills=["PostgreSQL"],
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Explain database normalization and indexing.",
            candidate_answer="Normalization eliminates redundancy across tables while indexing creates B-trees for fast lookups.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
            reference_payload=ref_payload,
        )

    assert decision.is_follow_up is False
    assert decision.is_interview_complete is False


@pytest.mark.asyncio
async def test_non_answer_does_not_trigger_followup():
    """Verify candidate saying 'I don't know' advances to next core question without meaningless follow-up probe."""
    gemini = GeminiService()
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.NON_ANSWER,
        completeness=CompletenessLevel.INSUFFICIENT,
        covered_concepts=[],
        missed_concepts=["database replication"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=False,
        is_correct=False,
        relevance_reason="Non-answer.",
        correctness_reason="No knowledge shown.",
        completeness_reason="Zero concepts covered.",
        classification_reason="Candidate stated they do not know.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="technical",
            focus_skills=["PostgreSQL"],
            current_turn_index=1,
            remaining_core_questions=3,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Explain logical replication in PostgreSQL.",
            candidate_answer="I don't know about this topic.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
        )

    assert decision.is_follow_up is False
    assert decision.is_interview_complete is False


@pytest.mark.asyncio
async def test_answer_length_does_not_trigger_followup():
    """Verify short valid answer with complete concepts does NOT trigger follow-up probe solely due to length."""
    gemini = GeminiService()
    ref_payload = QuestionReferencePayload(
        source="unit_test",
        reference_answer="HTTPS encrypts traffic via TLS.",
        primary_concept="Transport Security",
        question_text="What security protocol does HTTPS use?",
        expected_concepts=[
            ExpectedConcept(concept="TLS encryption", importance=ConceptImportance.CORE),
        ],
    )
    # 4-word answer that is complete and correct
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.STRONG,
        completeness=CompletenessLevel.COMPLETE,
        covered_concepts=["TLS encryption"],
        missed_concepts=[],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Direct answer.",
        correctness_reason="Accurate protocol cited.",
        completeness_reason="Complete.",
        classification_reason="Accurately stated TLS encryption.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Software Engineer",
            seniority_level="junior",
            interview_focus="technical",
            focus_skills=["Security"],
            current_turn_index=1,
            remaining_core_questions=3,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="What security protocol does HTTPS use?",
            candidate_answer="HTTPS uses TLS encryption.",  # 4 words
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
            reference_payload=ref_payload,
        )

    assert decision.is_follow_up is False


@pytest.mark.asyncio
async def test_no_followup_chaining():
    """Verify that when prior turn was a follow-up, another follow-up is strictly forbidden."""
    gemini = GeminiService()
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.PARTIAL,
        completeness=CompletenessLevel.PARTIAL,
        covered_concepts=["indexing"],
        missed_concepts=["vacuuming"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Relevant to indexing.",
        correctness_reason="Accurate indexing technique.",
        completeness_reason="Omitted vacuuming.",
        classification_reason="Partial response during follow-up.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="technical",
            focus_skills=["PostgreSQL"],
            current_turn_index=2,
            remaining_core_questions=2,
            remaining_followup_budget=2,
            prior_turn_was_followup=True,  # Prior was follow-up
            previous_question="How would you configure indexing for composite keys?",
            candidate_answer="I used multi-column B-tree indexes.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
        )

    assert decision.is_follow_up is False


# ============================================================================
# 14-16. MULTILINGUAL DIALOGUE TESTS
# ============================================================================


def test_multilingual_fallback_followup_hindi():
    """Verify Hindi fallback follow-up generates valid Hindi while retaining English tech terms."""
    probe = get_semantic_gap_fallback_followup(
        role="Backend Engineer",
        seniority="senior",
        parent_concept="Database Optimization",
        target_missing_concept="Connection Pooling",
        language="hi",
    )
    assert "Connection Pooling" in probe.question_text
    assert "Aapne" in probe.question_text or "karenge" in probe.question_text


def test_multilingual_fallback_followup_hinglish():
    """Verify Hinglish fallback follow-up generates natural Hinglish."""
    probe = get_semantic_gap_fallback_followup(
        role="Backend Engineer",
        seniority="mid",
        parent_concept="System Architecture",
        target_missing_concept="Deadlock Detection",
        language="hinglish",
    )
    assert "Deadlock Detection" in probe.question_text
    assert "Building on" in probe.question_text or "approach" in probe.question_text


# ============================================================================
# 17-21. QUESTION ARC SCAFFOLDING & RESUME GROUNDING TESTS
# ============================================================================


def test_weak_or_empty_resume_scaffolding():
    """Verify candidate with no resume is scaffolded to practical scenarios without hallucinating projects."""
    planner = get_question_planner()
    context = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="mid",
        interview_focus="technical",
        preferred_language="en",
        resume_data=None,
        parsed_jd_data=None,
        focus_skills=["Python", "FastAPI", "PostgreSQL"],
    )

    plan = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=0,
    )

    # Must NOT plan resume_project or work_history when no resume exists!
    assert plan.intent in (QuestionIntent.PRACTICAL_SCENARIO, QuestionIntent.CORE_SKILL)
    assert "practical" in plan.guidance.lower() or "skill" in plan.guidance.lower() or "fundamentals" in plan.guidance.lower()


def test_strong_candidate_difficulty_escalation():
    """Verify candidate with high performance trajectory receives escalated advanced architecture scenarios."""
    planner = QuestionPlanner()
    context = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="lead",
        interview_focus="technical",
        preferred_language="en",
        resume_data={"skills": ["Distributed Systems", "Kafka", "PostgreSQL"]},
    )

    # Plan late core questions (Q5)
    plan_q5 = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=4,
        average_prior_score=92.0,  # High trajectory
    )

    assert plan_q5.is_escalated is True
    assert "scenario" in plan_q5.topic.lower() or "distributed" in plan_q5.topic.lower()


# ============================================================================
# 22-25. FOLLOW-UP REMEDIATION LINKING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_followup_remediation_linking():
    """Verify follow-up turn successfully linking to parent turn missed concept."""
    from app.services.evaluation_service import EvaluationService

    eval_service = EvaluationService()

    # Mock Session with 1 Core turn (missed batching) and 1 Follow-up turn (covered batching)
    session = InterviewSession(
        id="session-rem-1",
        user_id="user-1",
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="technical",
        status="in_progress",
        practice_mode="quick",
        planned_core_questions=3,
        max_total_turns=6,
        started_at=datetime.now(timezone.utc),
    )

    turn1 = InterviewQuestionTurn(
        id="turn-core-1",
        session_id="session-rem-1",
        turn_index=1,
        question_type="core",
        question_text="How did you optimize the database pipeline?",
        candidate_answer="I used connection pooling.",
        ideal_answer="Connection pooling and batching.",
        is_follow_up=False,
        parent_turn_id=None,
    )

    turn2 = InterviewQuestionTurn(
        id="turn-followup-1",
        session_id="session-rem-1",
        turn_index=2,
        question_type="follow_up",
        question_text="How would you approach batching?",
        candidate_answer="We batched 500 rows per transaction using executemany.",
        ideal_answer="Batching rows per transaction.",
        is_follow_up=True,
        parent_turn_id="turn-core-1",
    )

    session.turns = [turn1, turn2]

    # Mock DB session
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = session
    mock_db.execute.return_value = mock_result

    # Mock Gemini AI Report
    mock_ai_report = SessionEvaluationReport(
        turns_evaluation=[
            TurnEvaluationItem(
                turn_index=1,
                relevance_score=85,
                correctness_score=80,
                keywords_score=75,
                clarity_score=85,
                confidence_score=80,
                answer_quality_tier=AnswerQualityTier.PARTIAL,
                ideal_answer_comparison="Good on pooling, missed batching.",
                turn_feedback="Include batching.",
            ),
            TurnEvaluationItem(
                turn_index=2,
                relevance_score=95,
                correctness_score=95,
                keywords_score=90,
                clarity_score=90,
                confidence_score=85,
                answer_quality_tier=AnswerQualityTier.STRONG,
                ideal_answer_comparison="Excellent batching explanation.",
                turn_feedback="Great remediation.",
            ),
        ],
        top_strengths=[StrengthItem(title="Database Knowledge", description="Strong understanding of DB pooling.")],
        top_improvements=[ImprovementItem(title="Full Pipeline", description="Consider full pipeline upfront.", actionable_recommendation="Study batching.")],
        executive_summary="Solid performance with effective follow-up remediation.",
    )

    ref1 = QuestionReferencePayload(
        source="unit_test",
        reference_answer="Use connection pooling with asyncpg and batching queries for database performance.",
        primary_concept="Database Optimization",
        question_text=turn1.question_text,
        expected_concepts=[
            ExpectedConcept(concept="connection pooling", importance=ConceptImportance.SUPPORTING),
            ExpectedConcept(concept="batching", importance=ConceptImportance.CORE),
        ],
    )
    ref2 = QuestionReferencePayload(
        source="unit_test",
        reference_answer="Batch multiple database operations together to minimize round trips.",
        primary_concept="Database Batching",
        question_text=turn2.question_text,
        expected_concepts=[
            ExpectedConcept(concept="batching", importance=ConceptImportance.CORE),
        ],
    )

    def mock_resolve_ref(turn, **kwargs):
        if turn.id == "turn-core-1":
            return ref1
        return ref2

    with patch.object(eval_service.gemini_service, "evaluate_interview_session", return_value=mock_ai_report), \
         patch.object(eval_service.reference_service, "resolve_reference_for_turn", side_effect=mock_resolve_ref):
        mock_user = MagicMock()
        mock_user.id = "user-1"
        report = await eval_service.evaluate_session(mock_db, mock_user, session.id)

    # Check that remediation note was generated and linked to parent turn
    t2_resp = next(t for t in report.turns_evaluation if t.turn_index == 2)
    assert t2_resp.is_follow_up is True
    assert t2_resp.parent_turn_id == "turn-core-1"
    # Remediation metadata
    assert turn2.evaluation_data.get("remediated_parent_concepts") == ["batching"]
    assert "remediated_in_followup" in turn1.evaluation_data


@pytest.mark.asyncio
async def test_irrelevant_answer_does_not_trigger_followup():
    """Verify irrelevant response advances without generating meaningless technical probe."""
    gemini = GeminiService()
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.IRRELEVANT,
        completeness=CompletenessLevel.INSUFFICIENT,
        covered_concepts=[],
        missed_concepts=["database indexing"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=False,
        is_correct=False,
        relevance_reason="Answer discusses weather rather than databases.",
        correctness_reason="N/A",
        completeness_reason="Irrelevant",
        classification_reason="Off-topic answer.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="technical",
            focus_skills=["PostgreSQL"],
            current_turn_index=1,
            remaining_core_questions=3,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="How do B-tree indexes work?",
            candidate_answer="The weather is really nice in California today.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
        )

    assert decision.is_follow_up is False


def test_project_grounded_question_selection():
    """Verify candidate with resume project receives project-grounded plan."""
    planner = QuestionPlanner()
    context = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="technical",
        preferred_language="en",
        resume_data={
            "projects": [
                {
                    "title": "High-Throughput Ingestion Engine",
                    "description": "Kafka and Redis real-time event pipeline.",
                    "technologies": ["Kafka", "Redis", "Python"],
                }
            ]
        },
    )

    plan = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=0,
    )

    assert plan.intent == QuestionIntent.RESUME_PROJECT
    assert "High-Throughput Ingestion Engine" in plan.topic or "Ingestion" in plan.grounding_snippet


def test_jd_grounded_question_selection():
    """Verify missing JD skill is targeted in question plan."""
    planner = QuestionPlanner()
    context = build_candidate_context(
        target_role="DevOps Engineer",
        seniority_level="senior",
        interview_focus="technical",
        preferred_language="en",
        parsed_jd_data={
            "required_skills": ["Terraform", "Kubernetes", "AWS"],
            "responsibilities": ["Manage IaC infrastructure"],
        },
        resume_data={
            "skills": ["AWS", "Docker"],  # Missing Terraform, Kubernetes
        },
    )

    plan = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=1,
    )

    assert plan.intent == QuestionIntent.JD_REQUIREMENT
    assert plan.topic in ("Terraform", "Kubernetes")

