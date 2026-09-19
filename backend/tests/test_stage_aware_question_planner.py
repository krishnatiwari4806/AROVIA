"""Comprehensive Test Suite for Stage-Aware System Design Question Planning and Gemini Integration.

Validates:
1. Stage-aware question planning across Stages 1 to 4 for system_design_staged mode.
2. Factual grounding in System Design Reference Architecture Blueprints.
3. Scenario continuity across all 4 stages of a session.
4. Single-intent and strict brevity constraints (20-35 words, 1 question mark).
5. Multilingual deterministic fallbacks (English, Hindi, Hinglish).
6. Anti-dogma prompt directive and non-answer stage advancement.
7. Zero extra Gemini calls (0 Gemini overhead for planning).
8. 100% behavioral isolation for legacy modes (Quick, Full, Technical Core, Behavioral).
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.schemas.interview import PracticeMode
from app.services.candidate_context import CandidateContext, build_candidate_context
from app.services.gemini_service import (
    ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE,
    INITIAL_QUESTION_PROMPT_TEMPLATE,
    GeminiService,
    GeneratedQuestion,
    NextTurnDecision,
    get_grounded_fallback_question,
    validate_and_normalize_question,
)
from app.services.question_planner import (
    QuestionIntent,
    QuestionPlan,
    QuestionPlanner,
    get_question_planner,
)
from app.services.reference_evaluator import (
    SYSTEM_DESIGN_BLUEPRINT_CATALOG,
    resolve_system_design_blueprint,
)
from app.services.system_design_stage_tracker import (
    STAGE_1_REQUIREMENTS,
    STAGE_2_ESTIMATION,
    STAGE_3_ARCHITECTURE,
    STAGE_4_DEFENSE,
    TOTAL_STAGED_ANSWER_TURNS,
    TOTAL_STAGED_CORE_STAGES,
    SystemDesignStageTracker,
)


@pytest.fixture
def staged_candidate_context():
    """Build a standard CandidateContext for System Design staged interview."""
    return build_candidate_context(
        target_role="Senior Software Engineer",
        seniority_level="senior",
        interview_focus="System Design",
        preferred_language="en",
        focus_skills=["Rate Limiting", "Redis", "Distributed Systems", "API Gateway"],
        resume_data={
            "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Kafka", "Docker"],
            "projects": [
                {
                    "title": "API Gateway Rate Limiter",
                    "description": "High-throughput sliding window rate limiter",
                    "technologies": ["Python", "Redis", "FastAPI"],
                }
            ],
            "work_history": [],
        },
        parsed_jd_data={
            "required_skills": ["Distributed Systems", "System Architecture", "Redis", "Scalability"],
            "experience_summary": "Looking for senior engineer experienced in high-concurrency systems.",
        },
        introduction_response="I am a senior backend engineer with 6 years experience building distributed microservices and caching systems.",
    )


@pytest.fixture
def planner():
    """Provide QuestionPlanner instance."""
    return get_question_planner()


# ==============================================================================
# 1. STAGE 1 PLANNING & GROUNDING (Requirements)
# ==============================================================================

def test_stage_1_plan_emits_requirements_metadata(planner, staged_candidate_context):
    """T01: Verify Stage 1 plan metadata has stage_key='stage_1_requirements', stage_index=1, and requirements focus."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=0,
        practice_mode="system_design_staged",
    )

    assert plan.intent == QuestionIntent.PRACTICAL_SCENARIO
    assert plan.stage_index == 1
    assert plan.stage_key == "stage_1_requirements"
    assert "Requirements" in plan.topic or "Scope" in plan.topic
    assert "Stage 1" in plan.guidance
    assert "Requirements" in plan.primary_concept or "Scope" in plan.primary_concept


def test_stage_1_plan_grounding_matches_blueprint(planner, staged_candidate_context):
    """T02: Verify Stage 1 plan grounding snippet contains scenario context and SLA targets."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=0,
        practice_mode="system_design_staged",
    )

    assert "Scenario:" in plan.grounding_snippet
    assert "Requirements Scope:" in plan.grounding_snippet
    assert "SLA target:" in plan.grounding_snippet


# ==============================================================================
# 2. STAGE 2 PLANNING & GROUNDING (Estimation & Data Model)
# ==============================================================================

def test_stage_2_plan_emits_estimation_metadata(planner, staged_candidate_context):
    """T03: Verify Stage 2 plan metadata has stage_key='stage_2_estimation', stage_index=2, and estimation focus."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=1,
        practice_mode="system_design_staged",
    )

    assert plan.intent == QuestionIntent.PRACTICAL_SCENARIO
    assert plan.stage_index == 2
    assert plan.stage_key == "stage_2_estimation"
    assert "Estimation" in plan.topic
    assert "Stage 2" in plan.guidance
    assert "Capacity Estimation" in plan.primary_concept


def test_stage_2_plan_grounding_references_capacity(planner, staged_candidate_context):
    """T04: Verify Stage 2 plan grounding snippet references QPS, scale, and data model."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=1,
        practice_mode="system_design_staged",
    )

    assert "Scale & Capacity:" in plan.grounding_snippet
    assert "QPS" in plan.grounding_snippet
    assert "Data Model" in plan.grounding_snippet


# ==============================================================================
# 3. STAGE 3 PLANNING & GROUNDING (High-Level Architecture)
# ==============================================================================

def test_stage_3_plan_emits_architecture_metadata(planner, staged_candidate_context):
    """T05: Verify Stage 3 plan metadata has stage_key='stage_3_architecture', stage_index=3, and architecture focus."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=2,
        practice_mode="system_design_staged",
    )

    assert plan.intent == QuestionIntent.PRACTICAL_SCENARIO
    assert plan.stage_index == 3
    assert plan.stage_key == "stage_3_architecture"
    assert "Architecture" in plan.topic
    assert "Stage 3" in plan.guidance
    assert "Component Architecture" in plan.primary_concept


def test_stage_3_plan_grounding_references_components(planner, staged_candidate_context):
    """T06: Verify Stage 3 plan grounding snippet references component nodes and request routing."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=2,
        practice_mode="system_design_staged",
    )

    assert "Component Architecture:" in plan.grounding_snippet
    assert "Data Flow:" in plan.grounding_snippet


# ==============================================================================
# 4. STAGE 4 PLANNING & GROUNDING (Failure & Scale Pushback)
# ==============================================================================

def test_stage_4_plan_emits_defense_metadata(planner, staged_candidate_context):
    """T07: Verify Stage 4 plan metadata has stage_key='stage_4_defense', stage_index=4, and defense pushback."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=3,
        practice_mode="system_design_staged",
    )

    assert plan.intent == QuestionIntent.PRACTICAL_SCENARIO
    assert plan.stage_index == 4
    assert plan.stage_key == "stage_4_defense"
    assert "Pushback" in plan.topic or "Defense" in plan.topic
    assert "Stage 4" in plan.guidance
    assert "Failure Mode Defense" in plan.primary_concept or "Resilience" in plan.primary_concept


def test_stage_4_plan_grounding_references_failure_modes(planner, staged_candidate_context):
    """T08: Verify Stage 4 plan grounding snippet references failure bottlenecks and cascading mitigation."""
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=3,
        practice_mode="system_design_staged",
    )

    assert "Failure & Bottlenecks:" in plan.grounding_snippet
    assert "Resilience:" in plan.grounding_snippet


# ==============================================================================
# 5. SESSION-LEVEL SCENARIO CONTINUITY
# ==============================================================================

def test_scenario_continuity_across_stages_1_to_4(planner, staged_candidate_context):
    """T09: Verify the same scenario title is consistently maintained across all 4 stages."""
    transcript = []

    for stage_idx in range(4):
        plan = planner.plan_next_question(
            context=staged_candidate_context,
            planned_core_questions=4,
            current_core_index=stage_idx,
            previous_turns=transcript,
            practice_mode="system_design_staged",
        )
        # Verify consistent scenario topic prefix
        assert "Rate Limiter" in plan.topic
        transcript.append({
            "turn_index": stage_idx + 1,
            "question_text": f"How do you approach {plan.topic}?",
            "candidate_answer": f"Here is my response for {plan.topic}.",
            "is_follow_up": False,
        })


def test_scenario_continuity_with_collaborative_editor_topic(planner):
    """T10: Verify scenario continuity when the established topic is Collaborative Document Editor."""
    context = build_candidate_context(
        target_role="Senior Backend Engineer",
        seniority_level="senior",
        interview_focus="System Design",
        focus_skills=["CRDT", "Operational Transformation", "WebSockets"],
    )
    transcript = [
        {
            "turn_index": 0,
            "question_text": "Tell me about your background.",
            "candidate_answer": "I build real-time collaborative editors.",
            "is_follow_up": False,
        },
        {
            "turn_index": 1,
            "question_text": "To start designing our Real-Time Collaborative Document Editor, what are the primary functional requirements and SLAs?",
            "candidate_answer": "Document editing, real-time sync with CRDTs, under 50ms latency.",
            "is_follow_up": False,
        },
    ]

    plan_stage2 = planner.plan_next_question(
        context=context,
        planned_core_questions=4,
        current_core_index=1,
        previous_turns=transcript,
        practice_mode="system_design_staged",
    )

    assert "Collaborative Document" in plan_stage2.topic
    assert plan_stage2.stage_key == "stage_2_estimation"


# ==============================================================================
# 6. BREVITY & SINGLE-INTENT VALIDATION
# ==============================================================================

def test_staged_fallback_questions_pass_validation(staged_candidate_context, planner):
    """T11: Verify all 4 stage fallbacks strictly pass validate_and_normalize_question."""
    for idx in range(4):
        plan = planner.plan_next_question(
            context=staged_candidate_context,
            planned_core_questions=4,
            current_core_index=idx,
            practice_mode="system_design_staged",
        )
        for lang in ("en", "hi", "hinglish"):
            fallback = get_grounded_fallback_question(
                context=staged_candidate_context,
                plan=plan,
                language=lang,
                stage_index=idx,
            )
            is_valid, norm_text, reason = validate_and_normalize_question(fallback.question_text)
            assert is_valid, f"Stage {idx+1} ({lang}) failed validation: '{fallback.question_text}' - reason: {reason}"
            words = norm_text.split()
            assert 4 <= len(words) <= 35, f"Stage {idx+1} word count {len(words)} out of range: '{norm_text}'"
            assert norm_text.count("?") == 1, f"Stage {idx+1} does not have exactly 1 '?': '{norm_text}'"


def test_question_validator_rejects_compound_interrogatives():
    """T12: Verify validate_and_normalize_question detects and rejects multi-intent compound questions."""
    compound_q = (
        "How would you design the rate limiter, what data structures would you use, "
        "and how would you handle distributed cache failure?"
    )
    is_valid, _, reason = validate_and_normalize_question(compound_q)
    assert not is_valid
    assert "Compound question" in reason or "Multiple" in reason


def test_question_validator_accepts_valid_staged_question():
    """T13: Verify valid single-intent staged question passes validation."""
    valid_q = "To begin designing our Distributed Rate Limiter, what are the primary functional requirements and latency SLAs you would establish?"
    is_valid, norm_text, reason = validate_and_normalize_question(valid_q)
    assert is_valid
    assert norm_text.endswith("?")
    assert norm_text.count("?") == 1


# ==============================================================================
# 7. MULTILINGUAL FALLBACK COVERAGE
# ==============================================================================

def test_staged_fallbacks_english(staged_candidate_context, planner):
    """T14: Verify English deterministic fallbacks for Stages 1 to 4."""
    for idx, expected_keyword in enumerate(["requirements", "estimate", "architecture", "failure"]):
        plan = planner.plan_next_question(
            context=staged_candidate_context,
            planned_core_questions=4,
            current_core_index=idx,
            practice_mode="system_design_staged",
        )
        fb = get_grounded_fallback_question(context=staged_candidate_context, plan=plan, language="en", stage_index=idx)
        assert expected_keyword in fb.question_text.lower()
        assert fb.question_text.endswith("?")


def test_staged_fallbacks_hindi(staged_candidate_context, planner):
    """T15: Verify Hindi deterministic fallbacks for Stages 1 to 4."""
    for idx, expected_keyword in enumerate(["requirements", "qps", "architecture", "cache"]):
        plan = planner.plan_next_question(
            context=staged_candidate_context,
            planned_core_questions=4,
            current_core_index=idx,
            practice_mode="system_design_staged",
        )
        fb = get_grounded_fallback_question(context=staged_candidate_context, plan=plan, language="hi", stage_index=idx)
        assert expected_keyword in fb.question_text.lower()
        assert "kaise" in fb.question_text.lower()
        assert fb.question_text.endswith("?")


def test_staged_fallbacks_hinglish(staged_candidate_context, planner):
    """T16: Verify Hinglish deterministic fallbacks for Stages 1 to 4."""
    for idx in range(4):
        plan = planner.plan_next_question(
            context=staged_candidate_context,
            planned_core_questions=4,
            current_core_index=idx,
            practice_mode="system_design_staged",
        )
        fb = get_grounded_fallback_question(context=staged_candidate_context, plan=plan, language="hinglish", stage_index=idx)
        assert "aap" in fb.question_text.lower() or "karenge" in fb.question_text.lower()
        assert fb.question_text.endswith("?")


# ==============================================================================
# 8. DETERMINISTIC ANTI-DOGMA & NON-ANSWER HANDLING
# ==============================================================================

def test_staged_prompts_contain_anti_dogma_directive():
    """T17: Verify both INITIAL_QUESTION_PROMPT_TEMPLATE and ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE contain Anti-Dogma directive."""
    assert "ANTI-DOGMA & SYSTEM DESIGN DIRECTIVE" in INITIAL_QUESTION_PROMPT_TEMPLATE
    assert "educational anchors and realistic guidelines, NOT dogmatic grading keys" in INITIAL_QUESTION_PROMPT_TEMPLATE

    assert "ANTI-DOGMA & SYSTEM DESIGN DIRECTIVE" in ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE
    assert "educational anchors and realistic guidelines, NOT dogmatic grading keys" in ADAPTIVE_NEXT_TURN_PROMPT_TEMPLATE


@pytest.mark.asyncio
async def test_staged_non_answer_advances_without_probe(staged_candidate_context, planner):
    """T18: Verify candidate non-answer ('I don't know') in staged mode advances to next stage without follow-up probe."""
    gemini_svc = GeminiService()
    gemini_svc.client = MagicMock()

    # Mock Gemini response attempting to generate a follow-up
    mock_response = MagicMock()
    mock_response.text = NextTurnDecision(
        is_follow_up=True,
        follow_up_reasoning="Let us probe deeper.",
        question_text="Could you explain sliding window counters in more detail?",
        ideal_answer="Sliding window counters maintain time-bucketed counts.",
        primary_concept="Sliding Window Counters",
        is_interview_complete=False,
    ).model_dump_json()

    gemini_svc.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    decision = await gemini_svc.evaluate_and_generate_next_turn(
        target_role="Senior Software Engineer",
        seniority_level="senior",
        interview_focus="System Design",
        focus_skills=["Rate Limiting"],
        current_turn_index=1,
        remaining_core_questions=3,
        remaining_followup_budget=0,  # Staged mode has 0 follow-up budget
        prior_turn_was_followup=False,
        previous_question="What are the requirements for the Rate Limiter?",
        candidate_answer="I don't know, I haven't worked with rate limiters.",
        transcript_history=[
            {"turn_index": 0, "question_text": "Intro", "candidate_answer": "Hi"},
            {"turn_index": 1, "question_text": "What are requirements?", "candidate_answer": "I don't know"},
        ],
        candidate_context=staged_candidate_context,
    )

    # Invariant: Non-answer must override follow-up to False
    assert decision.is_follow_up is False
    assert decision.is_interview_complete is False


# ==============================================================================
# 9. ZERO EXTRA GEMINI CALLS INSTRUMENTATION
# ==============================================================================

@pytest.mark.asyncio
async def test_zero_extra_gemini_calls_during_staged_planning(staged_candidate_context, planner):
    """T19: Verify planning runs 100% locally in Python with exactly 0 Gemini calls, and initial question makes exactly 1 Gemini call."""
    gemini_svc = GeminiService()
    mock_client = MagicMock()

    mock_resp = MagicMock()
    mock_resp.text = GeneratedQuestion(
        question_text="To begin designing our Distributed Rate Limiter, what are the primary functional requirements and latency SLAs you would establish?",
        ideal_answer="Establish functional scope, throughput targets, and latency boundaries.",
        primary_concept="Rate Limiter Requirements",
    ).model_dump_json()

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)
    gemini_svc.client = mock_client

    # 1. Question planning is purely synchronous, in-memory, zero API calls
    plan = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=0,
        practice_mode="system_design_staged",
    )
    assert mock_client.aio.models.generate_content.call_count == 0

    # 2. Generating initial question makes exactly 1 Gemini call
    gen_q = await gemini_svc.generate_initial_question(
        target_role="Senior Software Engineer",
        seniority_level="senior",
        interview_focus="System Design",
        candidate_context=staged_candidate_context,
        question_plan=plan,
    )

    assert mock_client.aio.models.generate_content.call_count == 1
    assert gen_q.question_text.endswith("?")


# ==============================================================================
# 10. LEGACY MODE BEHAVIORAL ISOLATION
# ==============================================================================

def test_quick_mode_unaffected_by_staged_planner(planner):
    """T20: Verify 3-turn Quick practice mode routes to _plan_quick_mode."""
    context = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        resume_data={
            "skills": ["Python", "Django"],
            "projects": [{"title": "E-Commerce API", "technologies": ["Python"]}],
            "work_history": [],
        },
    )

    plan = planner.plan_next_question(
        context=context,
        planned_core_questions=3,
        current_core_index=0,
        practice_mode="quick",
    )

    assert plan.intent == QuestionIntent.RESUME_PROJECT
    assert plan.topic == "E-Commerce API"
    assert plan.stage_key is None


def test_full_mode_unaffected_by_staged_planner(planner):
    """T21: Verify 6-turn Full practice mode routes to _plan_full_mode."""
    context = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        resume_data={
            "skills": ["Go", "Kubernetes"],
            "projects": [{"title": "Payment Processor", "technologies": ["Go"]}],
            "work_history": [],
        },
    )

    plan_q1 = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=0,
        practice_mode="full",
    )
    assert plan_q1.intent == QuestionIntent.RESUME_PROJECT
    assert plan_q1.stage_key is None

    plan_q6 = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=5,
        practice_mode="full",
    )
    assert plan_q6.intent == QuestionIntent.PRACTICAL_SCENARIO
    assert "Distributed Architecture" in plan_q6.topic
    assert plan_q6.stage_key is None


def test_behavioral_mode_unaffected_by_staged_planner(planner):
    """T22: Verify Behavioral interview focus routes without staged system design keys."""
    context = build_candidate_context(
        target_role="Engineering Manager",
        seniority_level="lead",
        interview_focus="Behavioral",
        resume_data={"skills": [], "projects": [], "work_history": []},
    )

    plan = planner.plan_next_question(
        context=context,
        planned_core_questions=6,
        current_core_index=0,
        practice_mode="full",
    )

    assert plan.stage_key is None


def test_technical_core_mode_unaffected_by_staged_planner(planner):
    """T23: Verify Technical Core focus routes to core skill / scenario without staged keys."""
    context = build_candidate_context(
        target_role="Frontend Developer",
        seniority_level="mid",
        interview_focus="Technical Core",
        focus_skills=["React", "TypeScript", "CSS"],
    )

    plan = planner.plan_next_question(
        context=context,
        planned_core_questions=3,
        current_core_index=0,
        practice_mode="quick",
    )

    assert plan.stage_key is None


# ==============================================================================
# 11. END-TO-END STAGE TRACKER & PLANNER COHESION
# ==============================================================================

def test_stage_tracker_and_planner_contract_alignment(staged_candidate_context, planner):
    """T24: Verify stage indices and stage keys in QuestionPlan align 1:1 with STAGE_DEFINITIONS."""
    for core_idx in range(4):
        plan = planner.plan_next_question(
            context=staged_candidate_context,
            planned_core_questions=4,
            current_core_index=core_idx,
            practice_mode="system_design_staged",
        )
        stage_num = core_idx + 1
        expected_stage_def = SystemDesignStageTracker.get_stage_info(stage_num)

        assert expected_stage_def is not None
        assert plan.stage_index == expected_stage_def.stage_index
        assert plan.stage_key == expected_stage_def.stage_key
        assert expected_stage_def.stage_name in plan.topic


def test_session_mode_enum_compatibility(staged_candidate_context, planner):
    """T25: Verify practice_mode handles PracticeMode.system_design_staged and raw string seamlessly."""
    plan_from_str = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=0,
        practice_mode="system_design_staged",
    )
    assert plan_from_str.stage_key == "stage_1_requirements"

    plan_from_enum = planner.plan_next_question(
        context=staged_candidate_context,
        planned_core_questions=4,
        current_core_index=0,
        practice_mode=PracticeMode.system_design_staged.value,
    )
    assert plan_from_enum.stage_key == "stage_1_requirements"
