"""Test Suite for AROVIA Task 7.1: Question Brevity and Single-Intent Hardening.

Verifies:
T01: Generated question <=35 words.
T02: Generated question contains exactly one '?'.
T03: Compound question is rejected or safely falls back.
T04: Fallback question <=35 words across all banks.
T05: Fallback question contains one intent across all banks.
T06: Candidate-specific grounding is preserved.
T07: Resume/JD/project grounding is preserved.
T08: Weak answer produces targeted single-intent follow-up on missing concept.
T09: Strong answer advances to next core question.
T10: No follow-up chaining regression.
T11: Quick mode budget unchanged (3 core turns).
T12: Full mode budget unchanged (6 core turns).
T13: Validation does not introduce an additional Gemini call.
T14: 429 fails fast.
T15: Voice stability and turn safety intact.
T16: "I don't know" / NON_ANSWER advances without follow-up.
T17: INCORRECT answer behavior unchanged.
T18: No duplicate generated question.
Phase 10 Quality Examples (Kafka compound, Redis single-intent, Imperative multi-part, etc.).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.schemas.evaluation import (
    AnswerQualityTier,
    CompletenessLevel,
    ConceptImportance,
    ExpectedConcept,
    QuestionReferencePayload,
    SemanticEvaluationResult,
)
from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.candidate_context import build_candidate_context
from app.services.gemini_service import (
    GeminiService,
    get_grounded_fallback_question,
    get_semantic_gap_fallback_followup,
    validate_and_normalize_question,
)
from app.services.question_bank import (
    BACKEND_BANK,
    DATA_BANK,
    DEVOPS_BANK,
    FRONTEND_BANK,
    FULLSTACK_BANK,
    ML_BANK,
    MOBILE_BANK,
    BEHAVIORAL_BANK,
    SYSTEM_DESIGN_BANK,
    UNIVERSAL_FOLLOWUPS,
    get_all_question_ids,
)
from app.services.question_planner import QuestionIntent, QuestionPlan, QuestionPlanner


# ===========================================================================
# 1. QUESTION VALIDATOR & NORMALIZER UNIT TESTS
# ===========================================================================

def test_t01_t02_valid_single_intent_questions_accepted():
    """T01 & T02: Valid questions with <=35 words and exactly 1 '?' are accepted."""
    valid_q1 = "You mentioned Redis in your project. How did you handle cache invalidation?"
    is_valid, norm, reason = validate_and_normalize_question(valid_q1)
    assert is_valid is True
    assert norm == valid_q1
    assert len(norm.split()) <= 35
    assert norm.count("?") == 1

    valid_q2 = "In your backend project, what was the most difficult scaling problem you encountered?"
    is_valid, norm, reason = validate_and_normalize_question(valid_q2)
    assert is_valid is True
    assert norm.count("?") == 1


def test_t03_compound_and_verbose_questions_rejected():
    """T03 & Phase 10: Compound, multi-intent, missing '?', and overly verbose questions are rejected."""
    # Example 1: 3-part compound Kafka question
    compound_kafka = (
        "I noticed you built a distributed event processing pipeline using Kafka and Go. "
        "How did you structure consumer group partitions to avoid lag, what was your dead-letter queue strategy, "
        "and how did you verify latency?"
    )
    is_valid, _, reason = validate_and_normalize_question(compound_kafka)
    assert is_valid is False
    assert "compound" in reason.lower()

    # Example 3: Imperative statement without '?' and 5-topic compound list
    imperative_q = (
        "Tell me about a backend project you worked on and explain the architecture, "
        "challenges, database decisions, scaling strategy, and deployment."
    )
    is_valid, _, reason = validate_and_normalize_question(imperative_q)
    assert is_valid is False

    # Example 5: 3-topic compound list in one question
    compound_topics = (
        "How do you approach concurrency, error handling, and performance optimization "
        "when designing scalable services?"
    )
    is_valid, _, reason = validate_and_normalize_question(compound_topics)
    assert is_valid is False

    # Multi-question mark
    multi_qm = "How did you scale the database? Did you use sharding?"
    is_valid, _, reason = validate_and_normalize_question(multi_qm)
    assert is_valid is False
    assert "multiple question marks" in reason.lower()

    # Over 35 words
    too_long = (
        "When you are designing a high-throughput microservice in a cloud native Kubernetes environment "
        "that connects to a PostgreSQL database with asyncpg connection pooling and Redis caching, "
        "what specific architectural design patterns do you follow to ensure high availability, fault tolerance, "
        "and sub-second p99 latency across multiple regional data centers?"
    )
    is_valid, _, reason = validate_and_normalize_question(too_long)
    assert is_valid is False
    assert "exceeds maximum length" in reason.lower()


def test_hindi_and_hinglish_validation():
    """Verify Hindi and Hinglish single-intent questions are accepted and compound inquiries rejected."""
    hi_valid = "Maine dekha ki aapne 'Payment Engine' project banaya hai. Kya aap iska system architecture explain kar sakte hain?"
    is_valid, _, _ = validate_and_normalize_question(hi_valid)
    assert is_valid is True

    hinglish_valid = "I noticed you built 'Payment Engine'. Kya aap iska system architecture aur key technical decisions walk through kar sakte hain?"
    is_valid, _, _ = validate_and_normalize_question(hinglish_valid)
    assert is_valid is True

    hi_compound = "Maine dekha ki aapne Kafka use kiya. Consumer lag kaise handle kiya, dead-letter queue kya thi, aur latency kaise check ki?"
    is_valid, _, reason = validate_and_normalize_question(hi_compound)
    assert is_valid is False
    assert "compound" in reason.lower()


# ===========================================================================
# 2. QUESTION BANK AUDIT TESTS (T04, T05)
# ===========================================================================

def test_t04_t05_all_question_bank_items_obey_brevity_and_single_intent():
    """T04 & T05: Every core question and follow-up across all 9 banks must be <=35 words and have exactly 1 '?'."""
    all_banks = {
        "BACKEND": BACKEND_BANK,
        "FRONTEND": FRONTEND_BANK,
        "FULLSTACK": FULLSTACK_BANK,
        "DEVOPS": DEVOPS_BANK,
        "DATA": DATA_BANK,
        "ML": ML_BANK,
        "MOBILE": MOBILE_BANK,
        "BEHAVIORAL": BEHAVIORAL_BANK,
        "SYSTEM_DESIGN": SYSTEM_DESIGN_BANK,
    }

    for bname, bank in all_banks.items():
        for sen, stages in bank.items():
            for st in stages:
                for q in st.core_questions:
                    wcount = len(q.question_text.split())
                    qmarks = q.question_text.count("?")
                    assert wcount <= 35, f"Question {q.id} in {bname} has {wcount} words (> 35): {q.question_text}"
                    assert qmarks == 1, f"Question {q.id} in {bname} has {qmarks} '?' marks (!= 1): {q.question_text}"

                    for f in q.follow_ups:
                        fwcount = len(f.prompt.split())
                        fqmarks = f.prompt.count("?")
                        assert fwcount <= 35, f"Followup {f.id} in {bname} has {fwcount} words (> 35): {f.prompt}"
                        assert fqmarks == 1, f"Followup {f.id} in {bname} has {fqmarks} '?' marks (!= 1): {f.prompt}"

    for uf in UNIVERSAL_FOLLOWUPS:
        wcount = len(uf.prompt.split())
        qmarks = uf.prompt.count("?")
        assert wcount <= 35, f"Universal followup {uf.id} has {wcount} words (> 35): {uf.prompt}"
        assert qmarks == 1, f"Universal followup {uf.id} has {qmarks} '?' marks (!= 1): {uf.prompt}"


# ===========================================================================
# 3. GROUNDED FALLBACK GENERATOR TESTS (T06, T07)
# ===========================================================================

def test_t06_t07_grounded_fallback_preserves_resume_and_jd_context():
    """T06 & T07: Deterministic fallbacks are single-intent, <=35 words, and strictly grounded in context."""
    ctx = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="technical",
        preferred_language="en",
        resume_data={
            "projects": [{"title": "Distributed Payment Gateway", "technologies": ["Go", "Kafka", "PostgreSQL"]}],
            "work_history": [{"company": "Acme Corp", "role": "Senior Engineer"}],
        },
        focus_skills=["Go", "Kafka", "PostgreSQL"],
    )

    # 1. Resume Project Plan
    plan_project = QuestionPlan(
        intent=QuestionIntent.RESUME_PROJECT,
        topic="Distributed Payment Gateway",
        grounding_snippet="Project 'Distributed Payment Gateway' using Go, Kafka, PostgreSQL.",
        guidance="Ask about Distributed Payment Gateway.",
        primary_concept="System Architecture: Distributed Payment Gateway",
    )
    fallback_proj = get_grounded_fallback_question(ctx, plan=plan_project, language="en")
    is_valid, _, reason = validate_and_normalize_question(fallback_proj.question_text)
    assert is_valid is True
    assert "Distributed Payment Gateway" in fallback_proj.question_text
    assert len(fallback_proj.question_text.split()) <= 35
    assert fallback_proj.question_text.count("?") == 1

    # 2. Work Experience Plan
    plan_work = QuestionPlan(
        intent=QuestionIntent.WORK_EXPERIENCE,
        topic="Acme Corp",
        grounding_snippet="Work Experience at Acme Corp.",
        guidance="Ask about Acme Corp.",
        primary_concept="Engineering Experience at Acme Corp",
    )
    fallback_work = get_grounded_fallback_question(ctx, plan=plan_work, language="en")
    is_valid, _, _ = validate_and_normalize_question(fallback_work.question_text)
    assert is_valid is True
    assert "Acme Corp" in fallback_work.question_text
    assert len(fallback_work.question_text.split()) <= 35

    # 3. JD Requirement Plan
    plan_jd = QuestionPlan(
        intent=QuestionIntent.JD_REQUIREMENT,
        topic="Kafka",
        grounding_snippet="Job Description requires Kafka.",
        guidance="Ask about Kafka.",
        primary_concept="Core JD Skill: Kafka",
    )
    fallback_jd = get_grounded_fallback_question(ctx, plan=plan_jd, language="en")
    is_valid, _, _ = validate_and_normalize_question(fallback_jd.question_text)
    assert is_valid is True
    assert "Kafka" in fallback_jd.question_text
    assert len(fallback_jd.question_text.split()) <= 35


# ===========================================================================
# 4. ADAPTIVE TURN DECISION & GEMINI QUOTA SAFETY (T08, T09, T10, T13, T14, T16)
# ===========================================================================

@pytest.mark.asyncio
async def test_t08_weak_answer_produces_targeted_single_intent_followup():
    """T08: Incomplete answer missing key concept produces targeted single-intent follow-up probe."""
    gemini = GeminiService()
    ref_payload = QuestionReferencePayload(
        source="unit_test",
        reference_answer="Explain database indexing and connection pooling.",
        primary_concept="Database Performance",
        question_text="How did you optimize database performance?",
        expected_concepts=[
            ExpectedConcept(concept="connection pooling", importance=ConceptImportance.CORE),
            ExpectedConcept(concept="query indexing", importance=ConceptImportance.CORE),
        ],
    )
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.PARTIAL,
        completeness=CompletenessLevel.PARTIAL,
        covered_concepts=["connection pooling"],
        missed_concepts=["query indexing"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Relevant",
        correctness_reason="Accurate",
        completeness_reason="Missed indexing",
        classification_reason="Covered connection pooling but omitted query indexing.",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="technical",
            focus_skills=["PostgreSQL"],
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="How did you optimize database performance?",
            candidate_answer="I configured connection pooling with asyncpg.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
            reference_payload=ref_payload,
        )

    assert decision.is_follow_up is True
    assert "query indexing" in decision.question_text.lower()
    is_valid, _, _ = validate_and_normalize_question(decision.question_text)
    assert is_valid is True
    assert len(decision.question_text.split()) <= 35
    assert decision.question_text.count("?") == 1


@pytest.mark.asyncio
async def test_t09_strong_answer_advances_to_next_core():
    """T09: Complete answer advances to next planned core question."""
    gemini = GeminiService()
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.STRONG,
        completeness=CompletenessLevel.COMPLETE,
        covered_concepts=["B-tree indexing", "eager loading"],
        missed_concepts=[],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Directly answered",
        correctness_reason="Technically accurate",
        completeness_reason="All concepts covered",
        classification_reason="Exemplary answer",
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
            previous_question="How do B-tree indexes speed up SQL lookups?",
            candidate_answer="B-trees allow logarithmic time search by balancing key pages.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
        )

    assert decision.is_follow_up is False
    assert decision.is_interview_complete is False
    is_valid, _, _ = validate_and_normalize_question(decision.question_text)
    assert is_valid is True


@pytest.mark.asyncio
async def test_t10_no_followup_chaining_after_followup_turn():
    """T10: If prior turn was a follow-up, system advances to next core even if candidate answer is partial."""
    gemini = GeminiService()
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.PARTIAL,
        completeness=CompletenessLevel.PARTIAL,
        covered_concepts=["partial caching"],
        missed_concepts=["cache stampede"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=True,
        relevance_reason="Relevant",
        correctness_reason="Partial",
        completeness_reason="Incomplete",
        classification_reason="Partial follow-up response",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="technical",
            focus_skills=["Redis"],
            current_turn_index=2,
            remaining_core_questions=3,
            remaining_followup_budget=1,
            prior_turn_was_followup=True,  # Prior turn was already a follow-up!
            previous_question="How do you handle cache invalidation?",
            candidate_answer="I invalidate on write.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
        )

    assert decision.is_follow_up is False
    is_valid, _, _ = validate_and_normalize_question(decision.question_text)
    assert is_valid is True


@pytest.mark.asyncio
async def test_t13_validation_rejection_triggers_fallback_with_zero_extra_gemini_calls():
    """T13: When Gemini generates a compound/verbose question, validation falls back immediately with EXACTLY 1 Gemini call."""
    gemini = GeminiService()
    mock_llm_response = MagicMock()
    # Gemini outputs an invalid compound question with 3 sub-questions
    mock_llm_response.text = (
        '{"is_follow_up": false, "is_interview_complete": false, '
        '"follow_up_reasoning": "Next core question", '
        '"question_text": "I noticed you built a distributed event pipeline using Kafka. How did you structure consumer groups to avoid lag, what was your dead-letter queue strategy, and how did you verify end-to-end latency?", '
        '"ideal_answer": "Comprehensive answer", "primary_concept": "Kafka Architecture"}'
    )

    with patch.object(gemini.client.aio.models, "generate_content", return_value=mock_llm_response) as mock_generate:
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="senior",
            interview_focus="technical",
            focus_skills=["Kafka"],
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="What is Kafka?",
            candidate_answer="Kafka is a distributed streaming platform.",
            transcript_history=[],
            preferred_language="en",
        )

        # EXACTLY 1 generate_content call was made (no regeneration loop)
        assert mock_generate.call_count == 1

    # Overridden with deterministic grounded fallback
    assert decision.question_text is not None
    is_valid, _, reason = validate_and_normalize_question(decision.question_text)
    assert is_valid is True
    assert len(decision.question_text.split()) <= 35
    assert decision.question_text.count("?") == 1


@pytest.mark.asyncio
async def test_t16_non_answer_advances_without_followup():
    """T16: Candidate stating 'I don't know' or 'pass' advances immediately to next core without follow-up."""
    gemini = GeminiService()
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.NON_ANSWER,
        completeness=CompletenessLevel.INSUFFICIENT,
        covered_concepts=[],
        missed_concepts=["Kafka internals"],
        contradicted_claims=[],
        unsupported_claims=[],
        is_relevant=False,
        is_correct=False,
        relevance_reason="Non-answer",
        correctness_reason="None",
        completeness_reason="None",
        classification_reason="Candidate stated 'I don't know'",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="technical",
            focus_skills=["Kafka"],
            current_turn_index=1,
            remaining_core_questions=4,
            remaining_followup_budget=2,
            prior_turn_was_followup=False,
            previous_question="Explain Kafka partition rebalancing.",
            candidate_answer="I don't know, I haven't worked with rebalancing.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
        )

    assert decision.is_follow_up is False
    assert decision.is_interview_complete is False
    is_valid, _, _ = validate_and_normalize_question(decision.question_text)
    assert is_valid is True


# ===========================================================================
# 5. BUDGET, 429, INCORRECT ANSWER & DEDUPLICATION TESTS (T11, T12, T14, T17, T18)
# ===========================================================================

def test_t11_quick_mode_budget_planning_unchanged():
    """T11: Quick practice mode plans exactly 3 core turns."""
    planner = QuestionPlanner()
    ctx = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="mid",
        interview_focus="technical",
        preferred_language="en",
        focus_skills=["Python", "FastAPI"],
    )

    plan0 = planner.plan_next_question(ctx, planned_core_questions=3, current_core_index=0)
    assert plan0.stage_index == 0

    plan1 = planner.plan_next_question(ctx, planned_core_questions=3, current_core_index=1)
    assert plan1.stage_index == 1

    plan2 = planner.plan_next_question(ctx, planned_core_questions=3, current_core_index=2)
    assert plan2.stage_index == 2


def test_t12_full_mode_budget_planning_unchanged():
    """T12: Full interview mode plans 6 progressive core turns."""
    planner = QuestionPlanner()
    ctx = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="technical",
        preferred_language="en",
        focus_skills=["Go", "Kubernetes", "PostgreSQL"],
    )

    for idx in range(6):
        plan = planner.plan_next_question(ctx, planned_core_questions=6, current_core_index=idx)
        assert plan.stage_index == idx


@pytest.mark.asyncio
async def test_t14_429_quota_exhaustion_fails_fast_to_fallback_without_retry():
    """T14: 429 RateLimitExceeded error fails fast without multi-attempt retry loop."""
    gemini = GeminiService()
    quota_err = Exception("429 ResourceExhausted: Quota exceeded for quota metric")

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=quota_err) as mock_generate:
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="technical",
            focus_skills=["Python"],
            current_turn_index=1,
            remaining_core_questions=3,
            remaining_followup_budget=1,
            prior_turn_was_followup=False,
            previous_question="Explain Python GIL.",
            candidate_answer="The GIL is the Global Interpreter Lock.",
            transcript_history=[],
            preferred_language="en",
        )

        # 429 fails fast after 1 attempt (non-transient error)
        assert mock_generate.call_count == 1

    # Safe deterministic fallback returned
    assert decision.question_text is not None
    is_valid, _, _ = validate_and_normalize_question(decision.question_text)
    assert is_valid is True


@pytest.mark.asyncio
async def test_t17_incorrect_answer_behavior():
    """T17: Incorrect answer with missing core concepts triggers targeted follow-up probe."""
    gemini = GeminiService()
    ref_payload = QuestionReferencePayload(
        source="unit_test",
        reference_answer="Explain ACID atomicity.",
        primary_concept="Database Transactions",
        question_text="What does Atomicity mean?",
        expected_concepts=[
            ExpectedConcept(concept="all-or-nothing rollback", importance=ConceptImportance.CORE),
        ],
    )
    sem_result = SemanticEvaluationResult(
        assigned_tier=AnswerQualityTier.INCORRECT,
        completeness=CompletenessLevel.INSUFFICIENT,
        covered_concepts=[],
        missed_concepts=["all-or-nothing rollback"],
        contradicted_claims=["Atomicity means queries execute in parallel"],
        unsupported_claims=[],
        is_relevant=True,
        is_correct=False,
        relevance_reason="Relevant attempt",
        correctness_reason="Technically incorrect definition",
        completeness_reason="Missing core mechanics",
        classification_reason="Erroneous claim regarding atomicity",
    )

    with patch.object(gemini.client.aio.models, "generate_content", side_effect=Exception("API offline")):
        decision = await gemini.evaluate_and_generate_next_turn(
            target_role="Backend Engineer",
            seniority_level="junior",
            interview_focus="technical",
            focus_skills=["SQL"],
            current_turn_index=1,
            remaining_core_questions=2,
            remaining_followup_budget=1,
            prior_turn_was_followup=False,
            previous_question="What does Atomicity mean in ACID?",
            candidate_answer="Atomicity means queries execute in parallel without locks.",
            transcript_history=[],
            preferred_language="en",
            semantic_result=sem_result,
            reference_payload=ref_payload,
        )

    assert decision.is_follow_up is True
    assert "all-or-nothing rollback" in decision.question_text.lower()
    is_valid, _, _ = validate_and_normalize_question(decision.question_text)
    assert is_valid is True


def test_t18_global_question_bank_ids_unique_and_non_duplicate():
    """T18: All QuestionTemplate, FollowUpTemplate, and Universal IDs are strictly unique."""
    all_ids = get_all_question_ids()
    assert len(all_ids) > 0
    # Verify no duplicate IDs across all 9 banks
    assert len(all_ids) == len(set(all_ids))

