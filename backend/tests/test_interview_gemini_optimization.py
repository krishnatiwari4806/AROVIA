"""Comprehensive verification tests for Interview Gemini Optimization & Free-Tier Quota Protection (Task 2).

Verifies all 13 critical safety and optimization criteria:
1. Initial question invokes Gemini only when required (Turn 0 is deterministic template).
2. Normal answer submission invokes Gemini exactly once per turn.
3. Identical answer retry is strictly idempotent with 0 additional Gemini calls.
4. Conflicting answer retry returns 400 with 0 Gemini calls.
5. Completed session retry does not invoke Gemini again.
6. Gemini HTTP 429 / RESOURCE_EXHAUSTED fails fast with 0 retries.
7. Gemini transient HTTP 503 / timeout uses only bounded retry (max 2 attempts).
8. Refresh / resume / GET endpoints make 0 Gemini calls.
9. Final evaluation is idempotent (persisted report reused on duplicate requests).
10. Quick mode maximum remains 3 core + 2 follow-ups (max 6 turns total).
11. Full mode maximum remains 6 core + 3 follow-ups (max 10 turns total).
12. No impossible counter states or progression drift.
13. No duplicate question generation where persisted state already exists.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.evaluation import SessionEvaluationReport, TurnEvaluationItem
from app.schemas.interview import GeneratedQuestion, NextTurnDecision


@pytest.fixture
def mock_gemini_pipeline():
    """Mock Gemini interview pipeline methods to count exact invocations."""
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next, patch(
        "app.services.gemini_service.GeminiService.evaluate_interview_session",
        new_callable=AsyncMock,
    ) as mock_eval:
        mock_initial.return_value = GeneratedQuestion(
            question_text="Explain Python asyncio event loop mechanics.",
            ideal_answer="Explanation of event loops, coroutines, tasks, and non-blocking I/O multiplexing.",
            primary_concept="Async IO",
        )
        mock_next.return_value = NextTurnDecision(
            is_follow_up=False,
            question_text="How do you handle database connection pooling under high concurrency?",
            ideal_answer="Pool sizing, connection reuse, backpressure, and timeout management.",
            primary_concept="Database Concurrency",
            is_interview_complete=False,
        )
        mock_eval.return_value = SessionEvaluationReport(
            turns_evaluation=[],
            top_strengths=[],
            top_improvements=[],
            executive_summary="Solid demonstration of technical competencies.",
        )
        yield mock_initial, mock_next, mock_eval


async def _create_test_user_and_session(
    client: AsyncClient, email: str, practice_mode: str = "quick"
) -> tuple[dict, str]:
    """Helper to register user and create an interview session."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword!123",
            "full_name": "Test Candidate",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sess_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": practice_mode,
        },
        headers=headers,
    )
    assert sess_res.status_code == 201
    return headers, sess_res.json()["id"]


# ==============================================================================
# 1. Initial question invokes Gemini only when required (Turn 0 is deterministic)
# ==============================================================================
@pytest.mark.asyncio
async def test_initial_question_invokes_gemini_only_when_required(
    client: AsyncClient, mock_gemini_pipeline
):
    """Turn 0 start uses deterministic template (0 Gemini calls); answering Turn 0 triggers generate_initial_question once."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_init_q@example.com"
    )

    # 1. Start interview (Generates Turn 0)
    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
    )
    assert start_res.status_code == 200
    turn0 = start_res.json()
    assert turn0["turn_index"] == 0
    assert turn0["question_type"] == "introduction"

    # ZERO Gemini calls on Turn 0 start
    assert mock_initial.call_count == 0
    assert mock_next.call_count == 0

    # 2. Candidate answers Turn 0 (Intro response)
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0['id']}/answer",
        json={"candidate_answer": "I have 4 years experience with Python and FastAPI."},
        headers=headers,
    )
    assert ans0_res.status_code == 200
    assert ans0_res.json()["next_turn"]["turn_index"] == 1

    # Exactly ONE initial question Gemini call triggered to generate Core Question 1
    assert mock_initial.call_count == 1
    assert mock_next.call_count == 0


# ==============================================================================
# 2. Normal answer submission does not duplicate Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_normal_answer_submission_single_gemini_call(
    client: AsyncClient, mock_gemini_pipeline
):
    """Submitting answer to Core Q1 triggers evaluate_and_generate_next_turn exactly once."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_normal_turn@example.com"
    )

    turn0_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    turn1_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Intro background details."},
        headers=headers,
    )
    turn1_id = turn1_res.json()["next_turn"]["id"]

    initial_next_calls = mock_next.call_count

    # Submit answer for Turn 1
    ans1_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={"candidate_answer": "Event loop handles asynchronous I/O multiplexing via selectors."},
        headers=headers,
    )
    assert ans1_res.status_code == 200
    assert ans1_res.json()["next_turn"]["turn_index"] == 2

    # Exactly ONE next-turn Gemini call triggered
    assert mock_next.call_count == initial_next_calls + 1


# ==============================================================================
# 3. Identical answer retry is idempotent (0 additional Gemini calls)
# ==============================================================================
@pytest.mark.asyncio
async def test_identical_answer_retry_idempotent_zero_additional_gemini_calls(
    client: AsyncClient, mock_gemini_pipeline
):
    """Resending the exact same answer payload on an already answered turn returns existing next turn with 0 Gemini calls."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_idempotent_retry@example.com"
    )

    turn0_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    intro_answer = "Hello, I am a software engineer with 5 years backend experience."
    ans0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": intro_answer},
        headers=headers,
    )
    assert ans0_res.status_code == 200
    turn1_id = ans0_res.json()["next_turn"]["id"]
    assert mock_initial.call_count == 1

    # Duplicate submission 1 (Network retry / double click)
    retry1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": intro_answer},
        headers=headers,
    )
    assert retry1.status_code == 200
    assert retry1.json()["next_turn"]["id"] == turn1_id

    # Duplicate submission 2 (Whitespace variation)
    retry2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": f"  {intro_answer}   \n"},
        headers=headers,
    )
    assert retry2.status_code == 200
    assert retry2.json()["next_turn"]["id"] == turn1_id

    # ZERO additional Gemini calls
    assert mock_initial.call_count == 1
    assert mock_next.call_count == 0


# ==============================================================================
# 4. Conflicting answer retry does not invoke Gemini again
# ==============================================================================
@pytest.mark.asyncio
async def test_conflicting_answer_retry_zero_gemini_calls(
    client: AsyncClient, mock_gemini_pipeline
):
    """Submitting a conflicting answer to an already answered turn returns 400 with 0 Gemini calls."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_conflict_retry@example.com"
    )

    turn0_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Original introduction."},
        headers=headers,
    )
    assert mock_initial.call_count == 1

    # Conflicting submission with different text
    conflict_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Completely different text."},
        headers=headers,
    )
    assert conflict_res.status_code == 400
    assert conflict_res.json()["error_code"] == "TURN_ALREADY_ANSWERED"

    # Call count remains unchanged
    assert mock_initial.call_count == 1


# ==============================================================================
# 5. Completed session retry does not invoke Gemini again
# ==============================================================================
@pytest.mark.asyncio
async def test_completed_session_retry_zero_gemini_calls(
    client: AsyncClient, mock_gemini_pipeline
):
    """Submitting answers to a completed session returns completion status with 0 Gemini calls."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_completed_retry@example.com"
    )

    # Fast-forward through Quick mode (3 core questions)
    turn0_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    res1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Intro answer"},
        headers=headers,
    )
    t1_id = res1.json()["next_turn"]["id"]

    res2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t1_id}/answer",
        json={"candidate_answer": "Core 1 answer"},
        headers=headers,
    )
    t2_id = res2.json()["next_turn"]["id"]

    res3 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t2_id}/answer",
        json={"candidate_answer": "Core 2 answer"},
        headers=headers,
    )
    t3_id = res3.json()["next_turn"]["id"]

    final_ans = "Core 3 answer finishing session"
    res4 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t3_id}/answer",
        json={"candidate_answer": final_ans},
        headers=headers,
    )
    assert res4.json()["is_interview_complete"] is True

    next_count_at_completion = mock_next.call_count

    # Resubmit final turn
    retry_final = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t3_id}/answer",
        json={"candidate_answer": final_ans},
        headers=headers,
    )
    assert retry_final.status_code == 200
    assert retry_final.json()["is_interview_complete"] is True
    assert mock_next.call_count == next_count_at_completion


# ==============================================================================
# 6. Gemini 429 does not retry (Fail-Fast Quota Protection)
# ==============================================================================
@pytest.mark.asyncio
async def test_gemini_429_fails_fast_with_zero_retries():
    """GeminiService must never retry HTTP 429 / RESOURCE_EXHAUSTED errors (fail fast on attempt 1)."""
    from app.services.gemini_service import GeminiService
    from app.services.candidate_context import build_candidate_context

    service = GeminiService()

    # Simulate Google GenAI 429 RESOURCE_EXHAUSTED error
    error_429 = Exception("429 RESOURCE_EXHAUSTED: Free tier quota exceeded")
    service.client.aio.models.generate_content = AsyncMock(side_effect=error_429)

    context = build_candidate_context(
        target_role="Software Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        preferred_language="en",
    )

    # Initial question generation with 429 fails fast and returns deterministic grounded fallback
    result = await service.generate_initial_question(
        target_role="Software Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        candidate_context=context,
    )

    # Verifies generate_content was called EXACTLY ONCE (no retry on 429)
    assert service.client.aio.models.generate_content.call_count == 1
    assert result.question_text is not None
    assert len(result.question_text) > 10


# ==============================================================================
# 7. Gemini transient 503 / timeout uses bounded retry (max 2 attempts)
# ==============================================================================
@pytest.mark.asyncio
async def test_gemini_transient_503_bounded_retry():
    """Transient HTTP 503 UNAVAILABLE or Timeout retries at most once (total 2 attempts) before falling back."""
    from app.services.gemini_service import GeminiService
    from app.services.candidate_context import build_candidate_context

    service = GeminiService()

    error_503 = Exception("503 UNAVAILABLE: The service is currently overloaded")
    service.client.aio.models.generate_content = AsyncMock(side_effect=error_503)

    context = build_candidate_context(
        target_role="Software Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        preferred_language="en",
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.generate_initial_question(
            target_role="Software Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            candidate_context=context,
        )

    # Bounded retry: exactly 2 attempts
    assert service.client.aio.models.generate_content.call_count == 2
    assert result.question_text is not None


# ==============================================================================
# 8. Refresh / resume does not regenerate an already persisted question/result
# ==============================================================================
@pytest.mark.asyncio
async def test_refresh_and_polling_makes_zero_gemini_calls(
    client: AsyncClient, mock_gemini_pipeline
):
    """GET /sessions/{id}, GET /sessions/{id}/turns, and GET /sessions/{id}/current-turn never invoke Gemini."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_refresh_test@example.com"
    )

    await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
    )

    # Simulate multiple page refreshes, tab switches, and polling requests
    for _ in range(5):
        s_res = await client.get(
            f"/api/v1/interviews/sessions/{session_id}", headers=headers
        )
        assert s_res.status_code == 200

        t_res = await client.get(
            f"/api/v1/interviews/sessions/{session_id}/turns", headers=headers
        )
        assert t_res.status_code == 200

        curr_res = await client.get(
            f"/api/v1/interviews/sessions/{session_id}/current-turn", headers=headers
        )
        assert curr_res.status_code == 200

    # ZERO Gemini calls across all 15 read operations
    assert mock_initial.call_count == 0
    assert mock_next.call_count == 0
    assert mock_eval.call_count == 0


# ==============================================================================
# 9. Final evaluation is idempotent
# ==============================================================================
@pytest.mark.asyncio
async def test_final_evaluation_is_idempotent(
    client: AsyncClient, mock_gemini_pipeline
):
    """Calling POST /evaluate or GET /evaluation multiple times invokes Gemini evaluation exactly once."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_eval_idempotent@example.com"
    )

    turn0_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    # Submit at least 1 turn so evaluation has answered turns
    await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={"candidate_answer": "Valid engineering introduction."},
        headers=headers,
    )

    # 1. Trigger initial evaluation
    eval1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers
    )
    assert eval1.status_code == 200
    assert mock_eval.call_count == 1

    # 2. Trigger evaluation again via POST -> Returns saved report
    eval2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers
    )
    assert eval2.status_code == 200
    assert eval2.json()["overall_score"] == eval1.json()["overall_score"]

    # 3. Retrieve evaluation via GET
    eval3 = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/evaluation", headers=headers
    )
    assert eval3.status_code == 200

    # ZERO additional Gemini calls
    assert mock_eval.call_count == 1


# ==============================================================================
# 10. Quick mode maximum remains 3 core + 2 follow-ups
# ==============================================================================
@pytest.mark.asyncio
async def test_quick_mode_maximum_budget_and_bounds(
    client: AsyncClient, mock_gemini_pipeline
):
    """Quick mode session cannot exceed planned_core=3, max_total_turns=6, and bounded Gemini calls."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    mock_next.return_value = NextTurnDecision(
        is_follow_up=True,
        follow_up_reasoning="Probing deeper into technical mechanics.",
        question_text="Follow-up probe question text.",
        ideal_answer="Ideal answer.",
        is_interview_complete=False,
    )

    headers, session_id = await _create_test_user_and_session(
        client, "opt_quick_bounds@example.com", practice_mode="quick"
    )

    # Start
    curr_turn_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    turns_count = 1
    for turn_step in range(10):  # Try to answer up to 10 times
        ans_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{curr_turn_id}/answer",
            json={"candidate_answer": f"Answer for turn {turn_step}"},
            headers=headers,
        )
        data = ans_res.json()
        if data["is_interview_complete"]:
            break
        curr_turn_id = data["next_turn"]["id"]
        turns_count += 1

    # Quick mode hard ceiling: total turns <= 6 (1 intro + 3 core + 2 follow-ups)
    assert turns_count <= 6
    # Total turn generation Gemini calls <= 5
    assert (mock_initial.call_count + mock_next.call_count) <= 5


# ==============================================================================
# 11. Full mode maximum remains 6 core + 3 follow-ups
# ==============================================================================
@pytest.mark.asyncio
async def test_full_mode_maximum_budget_and_bounds(
    client: AsyncClient, mock_gemini_pipeline
):
    """Full mode session cannot exceed planned_core=6, max_total_turns=10, and bounded Gemini calls."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    mock_next.return_value = NextTurnDecision(
        is_follow_up=True,
        follow_up_reasoning="Probing deeper into technical architecture.",
        question_text="Follow-up probe question.",
        ideal_answer="Ideal answer.",
        is_interview_complete=False,
    )

    headers, session_id = await _create_test_user_and_session(
        client, "opt_full_bounds@example.com", practice_mode="full"
    )

    curr_turn_id = (
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
    ).json()["id"]

    turns_count = 1
    for turn_step in range(15):
        ans_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{curr_turn_id}/answer",
            json={"candidate_answer": f"Full mode answer {turn_step}"},
            headers=headers,
        )
        data = ans_res.json()
        if data["is_interview_complete"]:
            break
        curr_turn_id = data["next_turn"]["id"]
        turns_count += 1

    # Full mode hard ceiling: total turns <= 10 (1 intro + 6 core + 3 follow-ups)
    assert turns_count <= 10
    assert (mock_initial.call_count + mock_next.call_count) <= 9


# ==============================================================================
# 12. No impossible counter states
# ==============================================================================
@pytest.mark.asyncio
async def test_no_impossible_counter_states(
    client: AsyncClient, mock_gemini_pipeline
):
    """Every turn response returns consistent core question numbers within [0, planned_core_questions]."""
    headers, session_id = await _create_test_user_and_session(
        client, "opt_counter_states@example.com", practice_mode="quick"
    )

    t0_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
    )
    t0_data = t0_res.json()
    assert t0_data["core_question_index"] is None
    assert t0_data["core_question_number"] is None
    assert t0_data["total_core_questions"] == 3

    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t0_data['id']}/answer",
        json={"candidate_answer": "Intro answer"},
        headers=headers,
    )
    t1_data = ans0.json()["next_turn"]
    assert t1_data["core_question_index"] == 0
    assert t1_data["core_question_number"] == 1
    assert t1_data["total_core_questions"] == 3


# ==============================================================================
# 13. No duplicate question generation where persisted state already exists
# ==============================================================================
@pytest.mark.asyncio
async def test_no_duplicate_question_generation_on_existing_turns(
    client: AsyncClient, mock_gemini_pipeline
):
    """Calling start_interview on an already initialized session returns existing Turn 0 without calling Gemini."""
    mock_initial, mock_next, mock_eval = mock_gemini_pipeline
    headers, session_id = await _create_test_user_and_session(
        client, "opt_duplicate_gen@example.com"
    )

    res1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
    )
    turn_id = res1.json()["id"]

    # Re-call start 3 times
    for _ in range(3):
        res_re = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start", headers=headers
        )
        assert res_re.status_code == 200
        assert res_re.json()["id"] == turn_id

    assert mock_initial.call_count == 0
    assert mock_next.call_count == 0
