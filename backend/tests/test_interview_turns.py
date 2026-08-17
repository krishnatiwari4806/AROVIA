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
    """Test starting an interview generates Turn 0 and get current-turn returns it."""
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
    assert turn0["question_type"] == "core"
    assert "Python backend architecture" in turn0["question_text"]
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
    """Test answering Turn 0 triggers dynamic follow-up linking and history retrieval."""
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

    # 2. Submit answer to Turn 0
    answer_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={
            "candidate_answer": "I built a Celery and Redis worker pipeline handling 10,000 tasks/min.",
            "turn_duration_sec": 45,
        },
        headers=headers,
    )
    assert answer_res.status_code == 200
    ans_data = answer_res.json()
    assert ans_data["is_interview_complete"] is False
    assert ans_data["current_turn_index"] == 1
    assert ans_data["answered_turn_id"] == turn0_id

    # Verify next turn is a follow-up linked to turn0
    next_turn = ans_data["next_turn"]
    assert next_turn is not None
    assert next_turn["turn_index"] == 1
    assert next_turn["is_follow_up"] is True
    assert next_turn["parent_turn_id"] == turn0_id
    assert "dead-letter" in next_turn["question_text"]

    # 3. Cannot answer turn 0 again
    dup_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={
            "candidate_answer": "Attempting second answer.",
            "turn_duration_sec": 10,
        },
        headers=headers,
    )
    assert dup_res.status_code == 400
    assert dup_res.json()["error_code"] == "TURN_ALREADY_ANSWERED"

    # 4. Get turns history
    history_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/turns",
        headers=headers,
    )
    assert history_res.status_code == 200
    turns = history_res.json()
    assert len(turns) == 2
    assert turns[0]["turn_index"] == 0
    assert turns[0]["candidate_answer"] is not None
    assert turns[0]["turn_duration_sec"] == 45
    assert turns[1]["turn_index"] == 1
    assert turns[1]["candidate_answer"] is None


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

    # Submit answer
    answer_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={
            "candidate_answer": "In Flutter we use BLoC for state management and streams for reactive UI updates.",
            "turn_duration_sec": 60,
        },
        headers=headers,
    )
    assert answer_res.status_code == 200
    ans_data = answer_res.json()
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
