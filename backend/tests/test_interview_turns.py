"""Integration tests for Interview Turn Progression, Adaptive State Machine & Session Endpoints (Phase 5 Plan 02)."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import GeneratedQuestion, NextTurnDecision


@pytest.fixture
def mock_gemini_turn_engine():
    """Mock Gemini initial question and next turn decisions."""
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_initial.return_value = GeneratedQuestion(
            question_text="Could you describe a challenging Python backend architecture you designed?",
            ideal_answer="Explanation of modular architecture, DB indexing, async workers, and monitoring.",
            primary_concept="System Architecture",
        )
        mock_next.return_value = NextTurnDecision(
            is_follow_up=True,
            follow_up_reasoning="Candidate mentioned async workers but did not explain failure retry policies.",
            question_text="How specifically do you handle dead-letter queues and backoff retries in those workers?",
            ideal_answer="Exponential backoff, jitter, dead-letter exchanges, and idempotency keys.",
            primary_concept="Worker Resilience",
            is_interview_complete=False,
        )
        yield mock_initial, mock_next


@pytest.mark.asyncio
async def test_start_interview_idempotence_and_current_turn(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Test starting an interview generates Turn 0 (warm-up intro) and get current-turn returns it."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "turn1@example.com",
            "password": "StrongPassword!123",
            "full_name": "Turn User 1",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a session
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 2. Start interview
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
    assert turn0["core_question_number"] is None
    assert turn0["total_core_questions"] == 3
    assert "introduce yourself" in turn0["question_text"]
    assert turn0["candidate_answer"] is None

    # 3. Start again -> idempotent, returns same turn 0
    start_res_2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res_2.status_code == 200
    assert start_res_2.json()["id"] == turn0["id"]

    # 4. Get current turn
    curr_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/current-turn",
        headers=headers,
    )
    assert curr_res.status_code == 200
    assert curr_res.json()["id"] == turn0["id"]


@pytest.mark.asyncio
async def test_submit_answer_dynamic_follow_up_and_turns_history(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Test answering Turn 0 gives Core Q1, answering Core Q1 triggers dynamic follow-up linking and history."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "turn2@example.com",
            "password": "StrongPassword!123",
            "full_name": "Turn User 2",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create and start session
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "Technical Core",
            "practice_mode": "full",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    turn0_id = start_res.json()["id"]

    # 2. Submit answer to Turn 0 (Warm-up Introduction) -> Advances to Core Question 1 (Turn 1)
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={
            "candidate_answer": "Hi, I am Alex, Senior Backend Engineer with 7 years experience in distributed systems.",
            "turn_duration_sec": 30,
        },
        headers=headers,
    )
    assert ans0_res.status_code == 200
    ans0_data = ans0_res.json()
    assert ans0_data["is_interview_complete"] is False
    assert ans0_data["current_turn_index"] == 1
    assert ans0_data["interview_phase"] == "core_question"
    assert ans0_data["current_core_question_index"] == 0
    assert ans0_data["total_core_questions"] == 6

    turn1 = ans0_data["next_turn"]
    assert turn1 is not None
    assert turn1["turn_index"] == 1
    assert turn1["question_type"] == "core"
    assert turn1["core_question_number"] == 1
    assert "Python backend architecture" in turn1["question_text"]
    turn1_id = turn1["id"]

    # 3. Submit answer to Turn 1 (Core Q1) -> Advances to Turn 2 (Follow-up on Core Q1)
    ans1_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={
            "candidate_answer": "I built a Celery and Redis worker pipeline handling 10,000 tasks/min.",
            "turn_duration_sec": 45,
        },
        headers=headers,
    )
    assert ans1_res.status_code == 200
    ans1_data = ans1_res.json()
    assert ans1_data["is_interview_complete"] is False
    assert ans1_data["current_turn_index"] == 2
    assert ans1_data["answered_turn_id"] == turn1_id

    next_turn = ans1_data["next_turn"]
    assert next_turn is not None
    assert next_turn["turn_index"] == 2
    assert next_turn["is_follow_up"] is True
    assert next_turn["parent_turn_id"] == turn1_id
    assert next_turn["core_question_number"] == 1
    assert next_turn["follow_up_number"] == 1
    assert next_turn["interview_phase"] == "follow_up"
    assert "dead-letter" in next_turn["question_text"]

    # 4. Cannot answer turn 1 again with different answer
    dup_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={
            "candidate_answer": "Attempting second answer.",
            "turn_duration_sec": 10,
        },
        headers=headers,
    )
    assert dup_res.status_code == 400
    assert dup_res.json()["error_code"] == "TURN_ALREADY_ANSWERED"

    # 5. Get turns history
    history_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/turns",
        headers=headers,
    )
    assert history_res.status_code == 200
    turns = history_res.json()
    assert len(turns) == 3
    assert turns[0]["turn_index"] == 0
    assert turns[0]["question_type"] == "introduction"
    assert turns[1]["turn_index"] == 1
    assert turns[1]["question_type"] == "core"
    assert turns[1]["core_question_number"] == 1
    assert turns[2]["turn_index"] == 2
    assert turns[2]["is_follow_up"] is True
    assert turns[2]["core_question_number"] == 1
    assert turns[2]["follow_up_number"] == 1


@pytest.mark.asyncio
async def test_session_completion_transition(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Test session transitions to 'evaluating' and completes when all questions are answered."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "turn3@example.com",
            "password": "StrongPassword!123",
            "full_name": "Turn User 3",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_initial, mock_next = mock_gemini_turn_engine

    # Configure mock_next to return complete
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        follow_up_reasoning="All practice questions completed.",
        question_text=None,
        ideal_answer=None,
        primary_concept=None,
        is_interview_complete=True,
    )

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Mobile Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    turn0_id = start_res.json()["id"]

    # Answer Turn 0 (Intro) -> Returns Turn 1 (Core 1)
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "I am a Flutter engineer.", "turn_duration_sec": 30},
        headers=headers,
    )
    assert ans0.status_code == 200
    assert ans0.json()["is_interview_complete"] is False
    turn1_id = ans0.json()["next_turn"]["id"]

    # Answer Turn 1 (Core 1) -> Returns Turn 2 (Core 2)
    ans1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "In Flutter we use BLoC for state management.", "turn_duration_sec": 60},
        headers=headers,
    )
    assert ans1.status_code == 200
    assert ans1.json()["is_interview_complete"] is False
    turn2_id = ans1.json()["next_turn"]["id"]

    # Answer Turn 2 (Core 2) -> Returns Turn 3 (Core 3)
    ans2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn2_id}/answer",
        json={"candidate_answer": "We use SQLite and Room for local offline storage.", "turn_duration_sec": 60},
        headers=headers,
    )
    assert ans2.status_code == 200
    assert ans2.json()["is_interview_complete"] is False
    turn3_id = ans2.json()["next_turn"]["id"]

    # Answer Turn 3 (Core 3, planned_core=3 exhausted -> Legitimate completion)
    ans3 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn3_id}/answer",
        json={"candidate_answer": "We use platform channels and FFI for native interop.", "turn_duration_sec": 60},
        headers=headers,
    )
    assert ans3.status_code == 200
    ans_data = ans3.json()
    assert ans_data["is_interview_complete"] is True
    assert ans_data["session_status"] == "evaluating"
    assert ans_data["next_turn"] is None

    # Check session status
    session_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}",
        headers=headers,
    )
    assert session_res.status_code == 200
    assert session_res.json()["status"] == "evaluating"
    assert session_res.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_scenario_a_quick_no_followup_deterministic_completion(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Scenario A: 1 intro + 3 core answers, 0 follow-ups -> completes after 3rd core answer without 4th question."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "scen_a@example.com", "password": "StrongPassword!123", "full_name": "Scenario A"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Tell me more about indexing.",
        ideal_answer="B-trees and hash indexes.",
        primary_concept="Database Indexing",
        is_interview_complete=False,
    )

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    t0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Turn 0 (Intro) answered -> Returns Turn 1 (Core 1)
    ans0 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer", json={"candidate_answer": "Intro answer"}, headers=headers)
    assert ans0.status_code == 200
    assert ans0.json()["is_interview_complete"] is False
    t1_id = ans0.json()["next_turn"]["id"]
    assert ans0.json()["next_turn"]["core_question_number"] == 1

    # Turn 1 (Core 1) answered -> Returns Turn 2 (Core 2)
    ans1 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t1_id}/answer", json={"candidate_answer": "Answer 1"}, headers=headers)
    assert ans1.status_code == 200
    assert ans1.json()["is_interview_complete"] is False
    t2_id = ans1.json()["next_turn"]["id"]
    assert ans1.json()["next_turn"]["core_question_number"] == 2

    # Turn 2 (Core 2) answered -> Returns Turn 3 (Core 3)
    ans2 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t2_id}/answer", json={"candidate_answer": "Answer 2"}, headers=headers)
    assert ans2.status_code == 200
    assert ans2.json()["is_interview_complete"] is False
    t3_id = ans2.json()["next_turn"]["id"]
    assert ans2.json()["next_turn"]["core_question_number"] == 3

    # Turn 3 (Core 3) answered -> Must complete deterministically (planned_core_questions=3 exhausted)
    ans3 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t3_id}/answer", json={"candidate_answer": "Answer 3"}, headers=headers)
    assert ans3.status_code == 200
    assert ans3.json()["is_interview_complete"] is True
    assert ans3.json()["next_turn"] is None
    assert ans3.json()["session_status"] == "evaluating"


@pytest.mark.asyncio
async def test_scenario_b_and_c_followup_must_not_chain(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Scenarios B & C: Intro -> Core 1 -> Follow-up -> Follow-up cannot chain -> moves to Core 2."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "scen_bc@example.com", "password": "StrongPassword!123", "full_name": "Scenario BC"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    # Step 1: Recommend follow-up for Core 1
    mock_next.return_value = NextTurnDecision(
        is_follow_up=True,
        question_text="Probe 1: explain memory allocation.",
        ideal_answer="Heap vs stack.",
        primary_concept="Memory",
        is_interview_complete=False,
    )

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    t0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Answer Intro -> Receives Core 1 (Turn 1)
    ans0 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer", json={"candidate_answer": "Intro"}, headers=headers)
    assert ans0.status_code == 200
    t1_id = ans0.json()["next_turn"]["id"]
    assert ans0.json()["next_turn"]["core_question_number"] == 1

    # Answer Core 1 -> Receives Follow-up 1 (Turn 2, core_question_number=1)
    ans1 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t1_id}/answer", json={"candidate_answer": "Shallow answer"}, headers=headers)
    assert ans1.status_code == 200
    assert ans1.json()["next_turn"]["is_follow_up"] is True
    assert ans1.json()["next_turn"]["parent_turn_id"] == t1_id
    assert ans1.json()["next_turn"]["core_question_number"] == 1
    assert ans1.json()["next_turn"]["follow_up_number"] == 1
    t2_followup_id = ans1.json()["next_turn"]["id"]

    # Step 2: Answer Follow-up 1. Even if Gemini attempts is_follow_up=True again, backend must force Core 2!
    mock_next.return_value = NextTurnDecision(
        is_follow_up=True,
        question_text="Probe 2: explain garbage collection.",
        ideal_answer="Reference counting & cyclic GC.",
        primary_concept="GC",
        is_interview_complete=False,
    )

    ans2 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t2_followup_id}/answer", json={"candidate_answer": "Follow-up answer"}, headers=headers)
    assert ans2.status_code == 200
    assert ans2.json()["is_interview_complete"] is False
    assert ans2.json()["next_turn"]["is_follow_up"] is False  # Clamped to core question
    assert ans2.json()["next_turn"]["parent_turn_id"] is None
    assert ans2.json()["next_turn"]["core_question_number"] == 2


@pytest.mark.asyncio
async def test_scenario_d_and_e_budget_exhaustion_and_max_boundary(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Scenarios D & E: Quick mode (planned_core=3, max_turns=6). 2 follow-ups + 3 core + 1 intro = 6 turns triggers max total boundary."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "scen_de@example.com", "password": "StrongPassword!123", "full_name": "Scenario DE"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    t0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Turn 0 (Intro) -> Turn 1 (Core 1)
    t1_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer", json={"candidate_answer": "Intro"}, headers=headers)).json()["next_turn"]["id"]

    # Turn 1 (Core 1) -> Turn 2 (Follow-up 1)
    mock_next.return_value = NextTurnDecision(is_follow_up=True, question_text="Follow-up 1", ideal_answer="Ans", primary_concept="C1")
    t2_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t1_id}/answer", json={"candidate_answer": "Ans 1"}, headers=headers)).json()["next_turn"]["id"]

    # Turn 2 (Follow-up 1) -> Turn 3 (Core 2)
    mock_next.return_value = NextTurnDecision(is_follow_up=False, question_text="Core 2", ideal_answer="Ans", primary_concept="C2")
    t3_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t2_id}/answer", json={"candidate_answer": "Ans 2"}, headers=headers)).json()["next_turn"]["id"]

    # Turn 3 (Core 2) -> Turn 4 (Follow-up 2)
    mock_next.return_value = NextTurnDecision(is_follow_up=True, question_text="Follow-up 2", ideal_answer="Ans", primary_concept="C3")
    t4_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t3_id}/answer", json={"candidate_answer": "Ans 3"}, headers=headers)).json()["next_turn"]["id"]

    # Turn 4 (Follow-up 2) -> Turn 5 (Core 3)
    mock_next.return_value = NextTurnDecision(is_follow_up=False, question_text="Core 3", ideal_answer="Ans", primary_concept="C4")
    t5_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t4_id}/answer", json={"candidate_answer": "Ans 4"}, headers=headers)).json()["next_turn"]["id"]

    # Turn 5 (Core 3, total_turns=6 = max_total_turns) -> Must complete
    ans6 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{t5_id}/answer", json={"candidate_answer": "Ans 5"}, headers=headers)
    assert ans6.status_code == 200
    assert ans6.json()["is_interview_complete"] is True
    assert ans6.json()["next_turn"] is None
    assert ans6.json()["session_status"] == "evaluating"


@pytest.mark.asyncio
async def test_scenario_f_full_mode_core_budget_respected(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Scenario F: Full mode (planned_core=6). Intro + 6 core answers with 0 follow-ups complete cleanly without 7th question."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "scen_f@example.com", "password": "StrongPassword!123", "full_name": "Scenario F"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Core topic question",
        ideal_answer="Benchmark answer",
        primary_concept="Core Topic",
        is_interview_complete=False,
    )

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "senior", "interview_focus": "Technical Core", "practice_mode": "full"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    current_turn_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # 1. Answer Turn 0 (Intro) -> generates Core 1
    ans_intro = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{current_turn_id}/answer",
        json={"candidate_answer": "Intro answer"},
        headers=headers,
    )
    assert ans_intro.status_code == 200
    current_turn_id = ans_intro.json()["next_turn"]["id"]
    assert ans_intro.json()["next_turn"]["core_question_number"] == 1

    # 2. Answer Core 1 through Core 5
    for i in range(5):
        ans_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{current_turn_id}/answer",
            json={"candidate_answer": f"Core answer {i + 1}"},
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["is_interview_complete"] is False
        assert ans_res.json()["next_turn"]["core_question_number"] == i + 2
        current_turn_id = ans_res.json()["next_turn"]["id"]

    # 3. 6th Core answer (Core 6) -> Must complete
    final_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{current_turn_id}/answer",
        json={"candidate_answer": "Core answer 6"},
        headers=headers,
    )
    assert final_res.status_code == 200
    assert final_res.json()["is_interview_complete"] is True
    assert final_res.json()["next_turn"] is None
    assert final_res.json()["session_status"] == "evaluating"


@pytest.mark.asyncio
async def test_duplicate_gemini_question_rejected_and_replaced_with_fallback(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Test 2: If Gemini generates an exact normalized duplicate of a prior turn, reject and use Question Bank."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "dedup_test@example.com", "password": "StrongPassword!123", "full_name": "Dedup Test"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    # Core 1 question via initial generator
    mock_initial.return_value = GeneratedQuestion(
        question_text="What is REST and how does it work?",
        ideal_answer="REST is representational state transfer with stateless HTTP methods.",
        primary_concept="REST Fundamentals",
    )

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    turn0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Answer Intro -> Turn 1 (Core 1)
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Candidate introduction."},
        headers=headers,
    )
    turn1_id = ans0.json()["next_turn"]["id"]
    assert "What is REST" in ans0.json()["next_turn"]["question_text"]

    # Mock Gemini on Core 2 to return an exact normalized duplicate of Core 1 with different casing and whitespace
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="   what IS rest and how does it work?   ",
        ideal_answer="Duplicate ideal answer",
        primary_concept="REST Fundamentals",
        is_interview_complete=False,
    )

    ans_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "REST stands for REpresentational State Transfer."},
        headers=headers,
    )
    assert ans_res.status_code == 200
    res_data = ans_res.json()
    assert res_data["is_interview_complete"] is False
    next_turn = res_data["next_turn"]
    assert next_turn is not None

    # Verify that the duplicate text was REJECTED and replaced with a Question Bank fallback
    assert "what IS rest and how does it work?" not in next_turn["question_text"]
    assert next_turn["question_type"] == "core"
    assert next_turn["core_question_number"] == 2
    assert len(next_turn["question_text"]) > 15


@pytest.mark.asyncio
async def test_premature_completion_overridden_when_core_remains(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Test 1: If Gemini returns is_interview_complete=True on Core 1 while core remains, override with fallback."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "premature_test@example.com", "password": "StrongPassword!123", "full_name": "Premature Test"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    turn0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Answer Intro -> Turn 1 (Core 1)
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Candidate introduction."},
        headers=headers,
    )
    turn1_id = ans0.json()["next_turn"]["id"]

    # Mock Gemini to return premature completion with no question_text on Turn 1
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text=None,
        ideal_answer=None,
        primary_concept=None,
        is_interview_complete=True,
    )

    ans_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "Solid explanation of backend services."},
        headers=headers,
    )
    assert ans_res.status_code == 200
    res_data = ans_res.json()

    # Must NOT complete prematurely! 2 core questions still remain
    assert res_data["is_interview_complete"] is False
    assert res_data["session_status"] == "in_progress"
    assert res_data["next_turn"] is not None
    assert res_data["next_turn"]["core_question_number"] == 2
    assert len(res_data["next_turn"]["question_text"]) > 10


@pytest.mark.asyncio
async def test_idempotent_identical_answer_retry_returns_existing_next_turn(
    client: AsyncClient, mock_gemini_turn_engine
):
    """TEST A: Submitting identical answer retry returns existing next turn without re-running Gemini or creating turns."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "idempotent_retry@example.com", "password": "StrongPassword!123", "full_name": "Idempotent Retry"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "senior", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    turn0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Answer Intro
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Intro answer"},
        headers=headers,
    )
    turn1_id = ans0.json()["next_turn"]["id"]

    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Describe how you design distributed locks with Redis.",
        ideal_answer="Redlock algorithm with TTL and clock drift protection.",
        primary_concept="Distributed Locking",
        is_interview_complete=False,
    )

    # 1. First submission on Core 1
    ans1_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "I use Redis for distributed caching with TTL expiration policies.", "turn_duration_sec": 45},
        headers=headers,
    )
    assert ans1_res.status_code == 200
    turn2_data = ans1_res.json()
    assert turn2_data["is_interview_complete"] is False
    assert turn2_data["next_turn"]["turn_index"] == 2
    turn2_id = turn2_data["next_turn"]["id"]
    call_count_before = mock_next.call_count

    # 2. Idempotent retry with surrounding/repeated whitespace variation
    ans2_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "   I use Redis   for distributed caching with TTL expiration policies.   ", "turn_duration_sec": 45},
        headers=headers,
    )
    assert ans2_res.status_code == 200
    retry_data = ans2_res.json()
    assert retry_data["is_interview_complete"] is False
    assert retry_data["next_turn"]["id"] == turn2_id
    assert retry_data["next_turn"]["turn_index"] == 2

    # Verify Gemini was NOT called a second time
    assert mock_next.call_count == call_count_before

    # Verify session only has 3 turns total in history (Turn 0, Turn 1, Turn 2)
    history_res = await client.get(f"/api/v1/interviews/sessions/{session_id}/turns", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) == 3


@pytest.mark.asyncio
async def test_conflicting_answer_retry_rejected_with_turn_already_answered(
    client: AsyncClient, mock_gemini_turn_engine
):
    """TEST B: Re-submitting a materially different answer on an answered turn is rejected with TURN_ALREADY_ANSWERED."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "conflict_retry@example.com", "password": "StrongPassword!123", "full_name": "Conflict Retry"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    turn0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # First answer
    await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Original answer regarding intro.", "turn_duration_sec": 30},
        headers=headers,
    )

    # Conflicting second answer
    conflict_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Completely different text trying to overwrite.", "turn_duration_sec": 30},
        headers=headers,
    )
    assert conflict_res.status_code == 400
    assert conflict_res.json()["error_code"] == "TURN_ALREADY_ANSWERED"
    assert "already been answered" in conflict_res.text

    # Verify original answer is untouched in history
    history_res = await client.get(f"/api/v1/interviews/sessions/{session_id}/turns", headers=headers)
    turns = history_res.json()
    assert turns[0]["candidate_answer"] == "Original answer regarding intro."


@pytest.mark.asyncio
async def test_completed_session_idempotent_retry_returns_completed_state(
    client: AsyncClient, mock_gemini_turn_engine
):
    """TEST C: Retrying final turn submission on an already completed/evaluating session returns completed state."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "completed_retry@example.com", "password": "StrongPassword!123", "full_name": "Completed Retry"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Another question",
        ideal_answer="Ideal answer",
        primary_concept="Concept",
        is_interview_complete=False,
    )

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "mid", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    turn0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    # Turn 0 (Intro)
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Answer 0"},
        headers=headers,
    )
    turn1_id = ans0.json()["next_turn"]["id"]

    # Turn 1 (Core 1)
    ans1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "Answer 1"},
        headers=headers,
    )
    turn2_id = ans1.json()["next_turn"]["id"]

    # Turn 2 (Core 2)
    ans2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn2_id}/answer",
        json={"candidate_answer": "Answer 2"},
        headers=headers,
    )
    turn3_id = ans2.json()["next_turn"]["id"]

    # Turn 3 (Core 3 - Final core question in quick mode)
    final_ans = "Final Answer to complete the session"
    ans3 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn3_id}/answer",
        json={"candidate_answer": final_ans},
        headers=headers,
    )
    assert ans3.status_code == 200
    assert ans3.json()["is_interview_complete"] is True
    call_count_at_completion = mock_next.call_count

    # Retry final turn submission
    retry_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn3_id}/answer",
        json={"candidate_answer": final_ans},
        headers=headers,
    )
    assert retry_res.status_code == 200
    retry_data = retry_res.json()
    assert retry_data["is_interview_complete"] is True
    assert retry_data["next_turn"] is None
    assert retry_data["session_status"] == "evaluating"

    # Gemini was not invoked on retry
    assert mock_next.call_count == call_count_at_completion


@pytest.mark.asyncio
async def test_concurrent_duplicate_turn_submissions_safe(
    client: AsyncClient, mock_gemini_turn_engine
):
    """TEST E: Rapid repeated duplicate submissions of the same turn answer resolve cleanly without duplicate turns."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "concurrent_submit@example.com", "password": "StrongPassword!123", "full_name": "Concurrent Submit"},
    )
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={"target_role": "Backend Engineer", "seniority_level": "senior", "interview_focus": "Technical Core", "practice_mode": "quick"},
        headers=headers,
    )
    session_id = create_res.json()["id"]
    turn0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

    answer_payload = {"candidate_answer": "I am a senior backend developer with 8 years experience.", "turn_duration_sec": 50}

    # Execute 3 rapid successive submissions on Turn 0
    res1 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer", json=answer_payload, headers=headers)
    res2 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer", json=answer_payload, headers=headers)
    res3 = await client.post(f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer", json=answer_payload, headers=headers)

    for r in (res1, res2, res3):
        assert r.status_code == 200
        assert r.json()["is_interview_complete"] is False

    # All returned the identical next_turn ID
    next_ids = {r.json()["next_turn"]["id"] for r in (res1, res2, res3)}
    assert len(next_ids) == 1

    # Exactly 2 turns total in history (Turn 0 and Turn 1)
    history_res = await client.get(f"/api/v1/interviews/sessions/{session_id}/turns", headers=headers)
    assert len(history_res.json()) == 2


