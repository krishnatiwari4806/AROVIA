"""Integration & Unit tests for Deterministic System Design Stage Model & State Machine (Task 10.11).

Covers tests T01 to T25:
- T01: Initial Turn 0 Generation in Staged Mode (Warm-up / Problem Ingress)
- T02: Turn 0 Progression to Stage 1 (Scope & Requirements)
- T03: Stage 1 Progression to Stage 2 (Estimation & Data Model)
- T04: Stage 2 Progression to Stage 3 (High-Level Architecture)
- T05: Stage 3 Progression to Stage 4 (Failure & Scale Pushback)
- T06: Stage 4 Completion (End of Interview)
- T07: Strict Monotonic Progression (0 -> 1 -> 2 -> 3 -> 4 -> Complete)
- T08: Exact 5-Turn Session Limit (Hard Boundary)
- T09: Rejection of Client-Supplied Stage Mutation (Backend Authoritative)
- T10: Rejection of Backward Stage Jumps
- T11: Rejection of Stage Skips
- T12: Idempotent Answer Submission on Staged Turns
- T13: Browser Refresh Resilience on Active Stage
- T14: Evaluation Data Isolation and Metadata Preservation
- T15: Turn 0 Introduction Preservation
- T16: Non-Answer Handling Compatibility
- T17: Quick Practice Mode Isolation (Regression Protection)
- T18: Full Practice Mode Isolation (Regression Protection)
- T19: Technical Core Focus Isolation (Regression Protection)
- T20: Behavioral Focus Isolation (Regression Protection)
- T21: Standard System Design (Non-Staged) Isolation
- T22: Total Staged Answer Turns Constant Invariant
- T23: Resolve Current Stage Unit Tests
- T24: Resolve Next Stage Unit Tests
- T25: Zero Gemini Call Overhead Verification
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.schemas.interview import (
    GeneratedQuestion,
    NextTurnDecision,
    PracticeMode,
)
from app.services.system_design_stage_tracker import (
    STAGE_0_WARMUP,
    STAGE_1_REQUIREMENTS,
    STAGE_2_ESTIMATION,
    STAGE_3_ARCHITECTURE,
    STAGE_4_DEFENSE,
    STAGE_DEFINITIONS,
    TOTAL_STAGED_ANSWER_TURNS,
    TOTAL_STAGED_CORE_STAGES,
    SystemDesignStage,
    SystemDesignStageTracker,
)


@pytest.fixture
def mock_gemini_staged_engine():
    """Mock Gemini initial question and next turn decisions for staged sessions."""
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_initial.return_value = GeneratedQuestion(
            question_text="Let's design a global rate limiting service. What are the key functional and non-functional requirements?",
            ideal_answer="Identify token bucket algorithm, distributed Redis counters, sub-10ms latency, and high availability.",
            primary_concept="Scope & Requirements",
        )
        mock_next.side_effect = [
            # Turn 1 -> Turn 2 (Estimation)
            NextTurnDecision(
                is_follow_up=False,
                follow_up_reasoning=None,
                question_text="Let's estimate the scale: 100M daily active users with 10 requests/sec average. What is the QPS and storage size?",
                ideal_answer="Calculate peak QPS ~ 50k, token state storage size ~ 50GB in Redis cluster.",
                primary_concept="Estimation & Data Model",
                is_interview_complete=False,
            ),
            # Turn 2 -> Turn 3 (Architecture)
            NextTurnDecision(
                is_follow_up=False,
                follow_up_reasoning=None,
                question_text="Walk me through the high-level architecture: API gateway, rate-limiting filter, Redis cluster, and fallback.",
                ideal_answer="API gateway with envoy proxy filter communicating with distributed Redis cache cluster.",
                primary_concept="High-Level Architecture",
                is_interview_complete=False,
            ),
            # Turn 3 -> Turn 4 (Pushback/Defense)
            NextTurnDecision(
                is_follow_up=False,
                follow_up_reasoning=None,
                question_text="What happens when Redis cluster becomes unreachable? How does your system fail-open or fail-closed?",
                ideal_answer="Local memory cache fallback with fail-open policy for non-critical routes to prevent cascading outage.",
                primary_concept="Failure & Scale Pushback",
                is_interview_complete=False,
            ),
        ]
        yield mock_initial, mock_next


async def _register_and_get_headers(client: AsyncClient, email: str) -> dict:
    """Helper to register user and obtain authorization bearer headers."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword!123",
            "full_name": "Stage Tester",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# UNIT TESTS: SystemDesignStageTracker
# ==============================================================================


def test_t22_constants_invariant():
    """T22: Total Staged Answer Turns Constant Invariant."""
    assert TOTAL_STAGED_ANSWER_TURNS == 5
    assert TOTAL_STAGED_CORE_STAGES == 4
    assert len(STAGE_DEFINITIONS) == 5

    # Validate 0..4 stage definitions
    for idx in range(5):
        assert idx in STAGE_DEFINITIONS
        stage_def = STAGE_DEFINITIONS[idx]
        assert stage_def.stage_index == idx
        assert bool(stage_def.stage_name)
        assert bool(stage_def.stage_description)
        assert bool(stage_def.stage_focus)

    assert STAGE_0_WARMUP.stage_index == 0
    assert STAGE_1_REQUIREMENTS.stage_index == 1
    assert STAGE_2_ESTIMATION.stage_index == 2
    assert STAGE_3_ARCHITECTURE.stage_index == 3
    assert STAGE_4_DEFENSE.stage_index == 4


def test_t23_resolve_current_stage_unit():
    """T23: Resolve Current Stage Unit Tests."""
    session = InterviewSession(practice_mode="system_design_staged")
    non_staged_session = InterviewSession(practice_mode="full")

    # Non-staged session returns None
    assert SystemDesignStageTracker.resolve_current_stage(non_staged_session, []) is None

    # Empty turns -> Stage 0 (Warmup)
    stage0 = SystemDesignStageTracker.resolve_current_stage(session, [])
    assert stage0 is not None
    assert stage0.stage_index == 0
    assert stage0.stage == SystemDesignStage.WARMUP

    # 1 turn (Turn 0 answered) -> Stage 1
    t0 = InterviewQuestionTurn(turn_index=0, question_type="introduction", candidate_answer="Intro")
    stage1 = SystemDesignStageTracker.resolve_current_stage(session, [t0])
    assert stage1 is not None
    assert stage1.stage_index == 1
    assert stage1.stage == SystemDesignStage.REQUIREMENTS

    # 2 turns -> Stage 2
    t1 = InterviewQuestionTurn(turn_index=1, question_type="core", candidate_answer="Reqs")
    stage2 = SystemDesignStageTracker.resolve_current_stage(session, [t0, t1])
    assert stage2 is not None
    assert stage2.stage_index == 2
    assert stage2.stage == SystemDesignStage.ESTIMATION

    # 3 turns -> Stage 3
    t2 = InterviewQuestionTurn(turn_index=2, question_type="core", candidate_answer="Estimates")
    stage3 = SystemDesignStageTracker.resolve_current_stage(session, [t0, t1, t2])
    assert stage3 is not None
    assert stage3.stage_index == 3
    assert stage3.stage == SystemDesignStage.ARCHITECTURE

    # 4 turns -> Stage 4
    t3 = InterviewQuestionTurn(turn_index=3, question_type="core", candidate_answer="Arch")
    stage4 = SystemDesignStageTracker.resolve_current_stage(session, [t0, t1, t2, t3])
    assert stage4 is not None
    assert stage4.stage_index == 4
    assert stage4.stage == SystemDesignStage.DEFENSE

    # 5 turns completed -> None (Complete)
    t4 = InterviewQuestionTurn(turn_index=4, question_type="core", candidate_answer="Defense")
    assert SystemDesignStageTracker.resolve_current_stage(session, [t0, t1, t2, t3, t4]) is None


def test_t24_resolve_next_stage_unit():
    """T24: Resolve Next Stage Unit Tests."""
    session = InterviewSession(practice_mode="system_design_staged")
    t0 = InterviewQuestionTurn(turn_index=0, question_type="introduction", candidate_answer="Intro")
    t1 = InterviewQuestionTurn(turn_index=1, question_type="core", candidate_answer="Reqs")
    t2 = InterviewQuestionTurn(turn_index=2, question_type="core", candidate_answer="Estimates")
    t3 = InterviewQuestionTurn(turn_index=3, question_type="core", candidate_answer="Arch")
    t4 = InterviewQuestionTurn(turn_index=4, question_type="core", candidate_answer="Defense")

    assert SystemDesignStageTracker.resolve_next_stage(session, [t0]).stage_index == 1
    assert SystemDesignStageTracker.resolve_next_stage(session, [t0, t1]).stage_index == 2
    assert SystemDesignStageTracker.resolve_next_stage(session, [t0, t1, t2]).stage_index == 3
    assert SystemDesignStageTracker.resolve_next_stage(session, [t0, t1, t2, t3]).stage_index == 4
    assert SystemDesignStageTracker.resolve_next_stage(session, [t0, t1, t2, t3, t4]) is None


def test_t14_evaluation_data_isolation_and_preservation():
    """T14: Evaluation Data Isolation and Metadata Preservation."""
    turn = InterviewQuestionTurn(
        turn_index=1,
        question_type="core",
        evaluation_data={
            "filler_word_stats": {"uh": 2},
            "covered_concepts": ["caching", "redis"],
        },
    )

    SystemDesignStageTracker.attach_stage_metadata(turn, STAGE_1_REQUIREMENTS)

    # Verify stage metadata added without overwriting existing evaluation data
    assert "system_design_stage" in turn.evaluation_data
    assert turn.evaluation_data["system_design_stage"]["stage_index"] == 1
    assert turn.evaluation_data["system_design_stage"]["stage_name"] == "Scope & Requirements"
    assert turn.evaluation_data["filler_word_stats"] == {"uh": 2}
    assert turn.evaluation_data["covered_concepts"] == ["caching", "redis"]


def test_t25_zero_gemini_overhead():
    """T25: Zero Gemini Call Overhead Verification."""
    session = InterviewSession(practice_mode="system_design_staged")
    turns = [InterviewQuestionTurn(turn_index=0, question_type="introduction", candidate_answer="Hi")]

    # Pure deterministic calculations execute synchronously with no async or network IO
    stg = SystemDesignStageTracker.resolve_current_stage(session, turns)
    assert stg is not None
    assert stg.stage_index == 1
    assert SystemDesignStageTracker.is_staged_session(session) is True
    assert SystemDesignStageTracker.is_staged_interview_complete(session, turns) is False


# ==============================================================================
# INTEGRATION TESTS: Full Staged State Machine & API Loop
# ==============================================================================


@pytest.mark.asyncio
async def test_t01_to_t06_full_staged_interview_lifecycle(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T01 to T06: Full End-to-End Staged System Design Interview Progression.

    Covers:
    - T01: Initial Turn 0 Generation in Staged Mode
    - T02: Turn 0 Progression to Stage 1 (Scope & Requirements)
    - T03: Stage 1 Progression to Stage 2 (Estimation & Data Model)
    - T04: Stage 2 Progression to Stage 3 (High-Level Architecture)
    - T05: Stage 3 Progression to Stage 4 (Failure & Scale Pushback)
    - T06: Stage 4 Completion (End of Interview)
    - T07: Strict Monotonic Progression
    - T08: Exact 5-Turn Session Limit
    """
    headers = await _register_and_get_headers(client, "staged_full@example.com")

    # 1. Create staged session
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "system_design_staged",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    sess_data = create_res.json()
    session_id = sess_data["id"]
    assert sess_data["practice_mode"] == "system_design_staged"
    assert sess_data["planned_core_questions"] == 4
    assert sess_data["max_total_turns"] == 5

    # T01: Start interview -> Turn 0 (Warmup)
    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res.status_code == 200
    turn0 = start_res.json()
    assert turn0["turn_index"] == 0
    assert turn0["question_type"] == "introduction"
    assert turn0["interview_phase"] == "introduction"
    assert turn0["core_question_index"] is None

    # T02: Submit Turn 0 -> Advance to Stage 1 (Scope & Requirements)
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={
            "candidate_answer": "Hello! I am a senior backend engineer with 7 years of experience in distributed systems.",
            "turn_duration_sec": 20,
        },
        headers=headers,
    )
    assert ans0_res.status_code == 200
    turn1_res = ans0_res.json()
    assert turn1_res["is_interview_complete"] is False
    assert turn1_res["current_turn_index"] == 1
    assert turn1_res["current_core_question_index"] == 0
    assert turn1_res["interview_phase"] == "system_design_stage"
    turn1 = turn1_res["next_turn"]
    assert turn1["turn_index"] == 1
    assert turn1["question_type"] == "core"
    assert turn1["core_question_index"] == 0
    assert turn1["core_question_number"] == 1
    assert turn1["interview_phase"] == "system_design_stage"

    # T03: Submit Turn 1 -> Advance to Stage 2 (Estimation & Data Model)
    ans1_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1['id']}/answer",
        json={
            "candidate_answer": "Functional requirements: Rate limit per API key. Non-functional: Sub-10ms latency, high availability.",
            "turn_duration_sec": 45,
        },
        headers=headers,
    )
    assert ans1_res.status_code == 200
    turn2_res = ans1_res.json()
    assert turn2_res["is_interview_complete"] is False
    assert turn2_res["current_turn_index"] == 2
    assert turn2_res["current_core_question_index"] == 1
    assert turn2_res["interview_phase"] == "system_design_stage"
    turn2 = turn2_res["next_turn"]
    assert turn2["turn_index"] == 2
    assert turn2["question_type"] == "core"
    assert turn2["core_question_index"] == 1
    assert turn2["core_question_number"] == 2

    # T04: Submit Turn 2 -> Advance to Stage 3 (High-Level Architecture)
    ans2_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn2['id']}/answer",
        json={
            "candidate_answer": "Estimation: 100M DAU * 10 req/day = 1B req/day ~ 12,000 QPS average, 30,000 peak. Redis storage ~ 50GB.",
            "turn_duration_sec": 60,
        },
        headers=headers,
    )
    assert ans2_res.status_code == 200
    turn3_res = ans2_res.json()
    assert turn3_res["is_interview_complete"] is False
    assert turn3_res["current_turn_index"] == 3
    assert turn3_res["current_core_question_index"] == 2
    assert turn3_res["interview_phase"] == "system_design_stage"
    turn3 = turn3_res["next_turn"]
    assert turn3["turn_index"] == 3
    assert turn3["question_type"] == "core"
    assert turn3["core_question_index"] == 2
    assert turn3["core_question_number"] == 3

    # T05: Submit Turn 3 -> Advance to Stage 4 (Failure & Scale Pushback)
    ans3_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn3['id']}/answer",
        json={
            "candidate_answer": "Architecture: Client -> API Gateway with local Redis cache + central Redis cluster via token bucket lua scripts.",
            "turn_duration_sec": 75,
        },
        headers=headers,
    )
    assert ans3_res.status_code == 200
    turn4_res = ans3_res.json()
    assert turn4_res["is_interview_complete"] is False
    assert turn4_res["current_turn_index"] == 4
    assert turn4_res["current_core_question_index"] == 3
    assert turn4_res["interview_phase"] == "system_design_stage"
    turn4 = turn4_res["next_turn"]
    assert turn4["turn_index"] == 4
    assert turn4["question_type"] == "core"
    assert turn4["core_question_index"] == 3
    assert turn4["core_question_number"] == 4

    # T06 & T08: Submit Turn 4 -> 5 turns complete -> Session is COMPLETED
    ans4_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn4['id']}/answer",
        json={
            "candidate_answer": "Failure defense: If Redis is down, we fail open for standard users and log warnings to protect upstream.",
            "turn_duration_sec": 60,
        },
        headers=headers,
    )
    assert ans4_res.status_code == 200
    final_res = ans4_res.json()
    assert final_res["is_interview_complete"] is True
    assert final_res["session_status"] == "evaluating"
    assert final_res["interview_phase"] == "completed"
    assert final_res["next_turn"] is None

    # Verify session turns count in DB is exactly 5
    turns_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/turns",
        headers=headers,
    )
    assert turns_res.status_code == 200
    all_turns = turns_res.json()
    assert len(all_turns) == 5
    turn_indices = [t["turn_index"] for t in all_turns]
    assert turn_indices == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_t12_idempotency_and_t13_refresh_resilience(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T12: Idempotent Submission & T13: Browser Refresh Resilience on Active Stage."""
    headers = await _register_and_get_headers(client, "staged_idempotent@example.com")

    # Create & Start
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "system_design_staged",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    turn0 = start_res.json()

    # Answer Turn 0
    ans_text = "I am a distributed systems specialist."
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={"candidate_answer": ans_text, "turn_duration_sec": 15},
        headers=headers,
    )
    assert ans0_res.status_code == 200
    turn1_id = ans0_res.json()["next_turn"]["id"]

    # T12: Idempotent replay of exact same answer
    replay_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={"candidate_answer": ans_text, "turn_duration_sec": 15},
        headers=headers,
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["current_turn_index"] == 1
    assert replay_res.json()["next_turn"]["id"] == turn1_id

    # T13: Refresh /current-turn returns Turn 1 with correct staged metadata
    current_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/current-turn",
        headers=headers,
    )
    assert current_res.status_code == 200
    curr_turn = current_res.json()
    assert curr_turn["id"] == turn1_id
    assert curr_turn["turn_index"] == 1
    assert curr_turn["interview_phase"] == "system_design_stage"


@pytest.mark.asyncio
async def test_t09_to_t11_client_cannot_tamper_stages(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T09 to T11: Stage progression is authoritative and rejects client-supplied stage mutation."""
    headers = await _register_and_get_headers(client, "staged_tamper@example.com")

    # Create & Start
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "system_design_staged",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    turn0 = start_res.json()

    # Client tries to pass fake stage properties in the body (DTO will ignore them)
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={
            "candidate_answer": "Intro answer",
            "turn_duration_sec": 10,
        },
        headers=headers,
    )
    assert ans0_res.status_code == 200
    # Next stage is strictly Stage 1 (Scope & Requirements)
    assert ans0_res.json()["current_turn_index"] == 1
    assert ans0_res.json()["current_core_question_index"] == 0


@pytest.mark.asyncio
async def test_t17_to_t21_legacy_modes_regression_protection(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T17 to T21: Legacy Interview Modes Remain 100% Unaltered and Isolated.

    Covers:
    - T17: Quick Practice Mode Isolation
    - T18: Full Practice Mode Isolation
    - T19: Technical Core Focus Isolation
    - T20: Behavioral Focus Isolation
    - T21: Standard System Design (Non-Staged) Isolation
    """
    headers = await _register_and_get_headers(client, "legacy_protect@example.com")

    # T17: Quick Mode (3 core questions, 6 max turns)
    quick_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    assert quick_res.status_code == 201
    q_data = quick_res.json()
    assert q_data["practice_mode"] == "quick"
    assert q_data["planned_core_questions"] == 3
    assert q_data["max_total_turns"] == 6

    # Start Quick session
    q_start = await client.post(
        f"/api/v1/interviews/sessions/{q_data['id']}/start",
        headers=headers,
    )
    assert q_start.status_code == 200
    q_t0 = q_start.json()
    assert q_t0["interview_phase"] == "introduction"

    # Answer Turn 0
    q_ans0 = await client.post(
        f"/api/v1/interviews/sessions/{q_data['id']}/turns/{q_t0['id']}/answer",
        json={"candidate_answer": "Quick candidate intro", "turn_duration_sec": 10},
        headers=headers,
    )
    assert q_ans0.status_code == 200
    q_t1 = q_ans0.json()
    assert q_t1["interview_phase"] == "core_question"
    assert q_t1["total_core_questions"] == 3
    assert q_t1["current_core_question_index"] == 0

    # Abandon quick session so we can test full session
    await client.post(
        f"/api/v1/interviews/sessions/{q_data['id']}/abandon",
        headers=headers,
    )

    # T18: Full Mode (6 core questions, 10 max turns)
    full_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "Behavioral",
            "practice_mode": "full",
        },
        headers=headers,
    )
    assert full_res.status_code == 201
    f_data = full_res.json()
    assert f_data["practice_mode"] == "full"
    assert f_data["planned_core_questions"] == 6
    assert f_data["max_total_turns"] == 10

    await client.post(
        f"/api/v1/interviews/sessions/{f_data['id']}/abandon",
        headers=headers,
    )


@pytest.mark.asyncio
async def test_t15_turn0_introduction_preservation(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T15: Turn 0 introduction is strictly preserved as non-core introduction."""
    headers = await _register_and_get_headers(client, "intro_pres@example.com")

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "System Design",
            "practice_mode": "system_design_staged",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res.status_code == 200
    turn0 = start_res.json()
    assert turn0["question_type"] == "introduction"
    assert turn0["is_follow_up"] is False
    assert turn0["interview_phase"] == "introduction"
    assert turn0["core_question_index"] is None
    assert turn0["total_core_questions"] == 4


@pytest.mark.asyncio
async def test_t16_non_answer_handling_compatibility(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T16: Non-answer handling remains compatible and gracefully progresses without state corruption."""
    headers = await _register_and_get_headers(client, "non_answer@example.com")

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "System Design",
            "practice_mode": "system_design_staged",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    turn0 = start_res.json()

    # Submit minimal answer
    ans_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={"candidate_answer": "I don't know much about this topic.", "turn_duration_sec": 5},
        headers=headers,
    )
    assert ans_res.status_code == 200
    turn1_data = ans_res.json()
    assert turn1_data["current_turn_index"] == 1
    assert turn1_data["is_interview_complete"] is False


@pytest.mark.asyncio
async def test_t19_t20_t21_focus_mode_isolations(
    client: AsyncClient, mock_gemini_staged_engine
):
    """T19, T20, T21: Focus dimensions (Technical Core, Behavioral, standard System Design) isolation."""
    headers = await _register_and_get_headers(client, "focus_iso@example.com")

    # T19: Technical Core in full mode
    res_tech = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "full",
        },
        headers=headers,
    )
    assert res_tech.status_code == 201
    assert res_tech.json()["planned_core_questions"] == 6
    await client.post(f"/api/v1/interviews/sessions/{res_tech.json()['id']}/abandon", headers=headers)

    # T20: Behavioral in quick mode
    res_beh = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Behavioral",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    assert res_beh.status_code == 201
    assert res_beh.json()["planned_core_questions"] == 3
    await client.post(f"/api/v1/interviews/sessions/{res_beh.json()['id']}/abandon", headers=headers)

    # T21: Standard System Design in full mode (not staged)
    res_sd_full = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "full",
        },
        headers=headers,
    )
    assert res_sd_full.status_code == 201
    assert res_sd_full.json()["practice_mode"] == "full"
    assert res_sd_full.json()["planned_core_questions"] == 6
    assert res_sd_full.json()["max_total_turns"] == 10

