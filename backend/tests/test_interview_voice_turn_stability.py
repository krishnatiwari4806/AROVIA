"""Regression tests for Task 6.1 — Voice / Turn Stability Hardening.

Verifies:
1. start_interview on in-progress session returns current active turn (e.g. Turn 1 or Turn 2), NOT Turn 0.
2. start_interview on newly created session with 0 turns generates Turn 0 (Introduction warm-up).
3. get_current_turn returns the active turn accurately.
4. Answering Turn 0 yields Core 1, and calling start_interview again returns Core 1.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import GeneratedQuestion, NextTurnDecision


@pytest.fixture
def mock_gemini():
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_init, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_init.return_value = GeneratedQuestion(
            question_text="Describe how you architect scalable FastAPI services.",
            ideal_answer="Async handlers, connection pooling, and Pydantic validation.",
            primary_concept="API Scalability",
        )
        mock_next.return_value = NextTurnDecision(
            is_follow_up=False,
            question_text="How do you handle database migration rollbacks in production?",
            ideal_answer="Alembic downgrade scripts with pre-migration verification.",
            primary_concept="Database Migrations",
            is_interview_complete=False,
        )
        yield mock_init, mock_next


@pytest.mark.asyncio
async def test_start_interview_returns_active_turn_on_in_progress_session(
    client: AsyncClient, mock_gemini
):
    """Test that calling start_interview on an in-progress session returns the active turn, NOT Turn 0."""
    # 1. Register candidate
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "voice_stab_1@example.com",
            "password": "StrongPassword!123",
            "full_name": "Voice Stability Tester",
        },
    )
    assert reg_res.status_code == 201
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}

    # 2. Create session
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 3. Start interview for the first time -> Generates Turn 0 (Introduction warm-up)
    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res.status_code == 200
    turn0 = start_res.json()
    assert turn0["turn_index"] == 0
    assert turn0["question_type"] == "introduction"

    # 4. Candidate answers Turn 0 -> Advances to Turn 1 (Core Question 1)
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={"candidate_answer": "I have 6 years building distributed Python microservices.", "turn_duration_sec": 25},
        headers=headers,
    )
    assert ans0_res.status_code == 200
    turn1 = ans0_res.json()["next_turn"]
    assert turn1["turn_index"] == 1
    assert turn1["question_type"] == "core"

    # 5. CRITICAL INVARIANT: Calling start_interview on this active session MUST return Turn 1, NOT Turn 0!
    start_again_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_again_res.status_code == 200
    active_turn_via_start = start_again_res.json()
    assert active_turn_via_start["id"] == turn1["id"]
    assert active_turn_via_start["turn_index"] == 1
    assert active_turn_via_start["turn_index"] != 0, "start_interview must NEVER return Turn 0 when session is at Turn 1!"

    # 6. Verify get_current_turn also returns Turn 1
    curr_turn_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/current-turn",
        headers=headers,
    )
    assert curr_turn_res.status_code == 200
    assert curr_turn_res.json()["id"] == turn1["id"]
    assert curr_turn_res.json()["turn_index"] == 1
