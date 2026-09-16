"""Comprehensive verification tests for AI Coach Gemini Optimization & Quota Safety (Task 4).

Verifies all 14 critical test matrix requirements:
1. First Coach visit -> exactly one initial debrief Gemini call.
2. Existing debrief -> zero Gemini calls (persisted debrief reused).
3. Refresh/reopen coach view -> zero Gemini calls.
4. Repeated initialization -> no duplicate debrief generated.
5. One chat message -> exactly one Gemini call.
6. Duplicate / sequential chat submission -> handles messages cleanly.
7. Empty message -> rejected with 400 and zero Gemini calls.
8. Unauthorized conversation access -> rejected with 404/401 and zero Gemini calls.
9. Coach Gemini 429 / RESOURCE_EXHAUSTED -> fails fast on attempt 1 with zero retries.
10. Coach Gemini transient 503 / timeout -> bounded retry only (max 2 attempts).
11. Strict User and Session Isolation: User A cannot access User B's coach conversation.
12. Grounded ActionableCoachingPlan remains present in response DTO.
13. Historical progress intelligence & weakness resolutions remain present.
14. Persisted assistant response survives page reload / history fetch with zero Gemini calls.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.services.coach_ai_service import CoachAIService, CoachChatStructuredResponse
from app.services.coach_context_builder import CoachContextPayload


@pytest.fixture
def mock_coach_gemini_pipeline():
    """Mock Coach Gemini methods to verify call boundaries and counts."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### AI Coach Debrief\n\nSolid demonstration of distributed systems principles."
        )
        mock_chat.return_value = {
            "coach_response": "To improve, discuss exponential backoff and jitter algorithms.",
            "suggested_followups": [
                "How does jitter prevent thundering herds?",
                "Give me a model answer for Turn 1.",
            ],
        }
        yield mock_debrief, mock_chat


async def _register_user(client: AsyncClient, email: str) -> dict:
    """Helper to register user and return auth headers."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword!123",
            "full_name": "Test Coach User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_completed_session(client: AsyncClient, headers: dict) -> str:
    """Helper to create a completed interview session."""
    sess_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # Start and answer Turn 0
    t0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]
    await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
        json={"candidate_answer": "Intro answer"},
        headers=headers,
    )

    # Evaluate session
    with patch(
        "app.services.gemini_service.GeminiService.evaluate_interview_session",
        new_callable=AsyncMock,
    ) as mock_eval:
        from app.schemas.evaluation import SessionEvaluationReport
        mock_eval.return_value = SessionEvaluationReport(
            turns_evaluation=[],
            top_strengths=[],
            top_improvements=[],
            executive_summary="Interview evaluation complete.",
        )
        await client.post(f"/api/v1/interviews/sessions/{session_id}/evaluate", headers=headers)

    return session_id


# ==============================================================================
# 1. First Coach visit -> exactly one initial debrief Gemini call
# ==============================================================================
@pytest.mark.asyncio
async def test_first_coach_visit_invokes_debrief_once(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """First POST /coach/conversation with auto_debrief=True invokes generate_initial_debrief exactly once."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_first_visit@example.com")
    session_id = await _create_completed_session(client, headers)

    res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 1
    assert data["messages"][0]["sender"] == "coach"
    assert "AI Coach Debrief" in data["messages"][0]["message_text"]
    assert mock_debrief.call_count == 1
    assert mock_chat.call_count == 0


# ==============================================================================
# 2. Existing debrief -> zero Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_existing_debrief_zero_gemini_calls(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """Subsequent POST /coach/conversation calls reuse the saved debrief with 0 Gemini calls."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_existing_debrief@example.com")
    session_id = await _create_completed_session(client, headers)

    # First call initializes
    await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert mock_debrief.call_count == 1

    # Second and third calls
    for _ in range(3):
        res = await client.post(
            "/api/v1/coach/conversation",
            json={"session_id": session_id, "auto_debrief": True},
            headers=headers,
        )
        assert res.status_code == 200
        assert len(res.json()["messages"]) == 1

    # ZERO additional Gemini debrief calls
    assert mock_debrief.call_count == 1
    assert mock_chat.call_count == 0


# ==============================================================================
# 3. Refresh / reopen coach view -> zero Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_refresh_and_history_fetch_zero_gemini_calls(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """GET /coach/history/{session_id} loads conversation from DB with 0 Gemini calls."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_refresh_zero@example.com")
    session_id = await _create_completed_session(client, headers)

    # Initialize
    await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert mock_debrief.call_count == 1

    # Simulate 5 page refreshes
    for _ in range(5):
        hist_res = await client.get(
            f"/api/v1/coach/history/{session_id}", headers=headers
        )
        assert hist_res.status_code == 200
        assert hist_res.json()["total_messages"] == 1

    assert mock_debrief.call_count == 1
    assert mock_chat.call_count == 0


# ==============================================================================
# 4. Repeated initialization -> no duplicate debrief
# ==============================================================================
@pytest.mark.asyncio
async def test_repeated_initialization_no_duplicate_debrief(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """Multiple sequential calls to /coach/conversation safely return one conversation with at most 1 debrief."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_repeated_init@example.com")
    session_id = await _create_completed_session(client, headers)

    res1 = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    res2 = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    res3 = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res3.status_code == 200

    # All returned the exact same conversation ID
    assert res1.json()["id"] == res2.json()["id"] == res3.json()["id"]

    # Verify history has exactly 1 debrief message
    hist = await client.get(f"/api/v1/coach/history/{session_id}", headers=headers)
    assert hist.status_code == 200
    coach_msgs = [m for m in hist.json()["messages"] if m["sender"] == "coach"]
    assert len(coach_msgs) == 1
    assert mock_debrief.call_count == 1


# ==============================================================================
# 5. One chat message -> exactly one Gemini call
# ==============================================================================
@pytest.mark.asyncio
async def test_single_chat_message_invokes_gemini_once(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """POST /coach/chat calls generate_chat_reply exactly once per submitted user message."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_chat_single@example.com")
    session_id = await _create_completed_session(client, headers)

    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    conv_id = conv_res.json()["id"]

    chat_res = await client.post(
        "/api/v1/coach/chat",
        json={
            "conversation_id": conv_id,
            "message": "How do I optimize database connection pooling?",
            "context_turn_index": 0,
        },
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["user_message"]["message_text"] == "How do I optimize database connection pooling?"
    assert "exponential backoff" in chat_data["coach_message"]["message_text"]
    assert mock_chat.call_count == 1


# ==============================================================================
# 6. Duplicate / sequential chat messages are persisted cleanly
# ==============================================================================
@pytest.mark.asyncio
async def test_sequential_chat_messages_persisted(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """Sending 3 distinct inquiries persists 3 user messages and 3 coach replies (3 Gemini calls)."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_seq_chat@example.com")
    session_id = await _create_completed_session(client, headers)

    conv_id = (
        await client.post(
            "/api/v1/coach/conversation",
            json={"session_id": session_id, "auto_debrief": True},
            headers=headers,
        )
    ).json()["id"]

    for i in range(3):
        await client.post(
            "/api/v1/coach/chat",
            json={"conversation_id": conv_id, "message": f"Inquiry number {i+1}"},
            headers=headers,
        )

    assert mock_chat.call_count == 3

    # History contains 1 initial debrief + 3 user msgs + 3 coach replies = 7 total messages
    hist = await client.get(f"/api/v1/coach/history/{session_id}", headers=headers)
    assert hist.json()["total_messages"] == 7


# ==============================================================================
# 7. Empty message -> zero Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_empty_chat_message_rejected_zero_gemini_calls(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """POST /coach/chat with empty or whitespace message returns 400 with 0 Gemini calls."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_empty_msg@example.com")
    session_id = await _create_completed_session(client, headers)

    conv_id = (
        await client.post(
            "/api/v1/coach/conversation",
            json={"session_id": session_id, "auto_debrief": True},
            headers=headers,
        )
    ).json()["id"]

    initial_chat_calls = mock_chat.call_count

    res = await client.post(
        "/api/v1/coach/chat",
        json={"conversation_id": conv_id, "message": "   \n  \t  "},
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["error_code"] == "EMPTY_MESSAGE"
    assert mock_chat.call_count == initial_chat_calls


# ==============================================================================
# 8. Unauthorized conversation -> zero Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_unauthorized_chat_rejected_zero_gemini_calls(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """User B cannot send a chat message to User A's coach conversation."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers_a = await _register_user(client, "user_a_chat@example.com")
    headers_b = await _register_user(client, "user_b_chat@example.com")

    session_a_id = await _create_completed_session(client, headers_a)
    conv_a_id = (
        await client.post(
            "/api/v1/coach/conversation",
            json={"session_id": session_a_id, "auto_debrief": True},
            headers=headers_a,
        )
    ).json()["id"]

    initial_chat_calls = mock_chat.call_count

    # User B tries to chat on User A's conversation
    res = await client.post(
        "/api/v1/coach/chat",
        json={"conversation_id": conv_a_id, "message": "Unauthorized message"},
        headers=headers_b,
    )
    assert res.status_code == 404
    assert mock_chat.call_count == initial_chat_calls


# ==============================================================================
# 9. Coach Gemini 429 -> fail-fast on attempt 1 with zero retries
# ==============================================================================
@pytest.mark.asyncio
async def test_coach_gemini_429_fails_fast_with_zero_retries():
    """CoachAIService must fail fast on 429 with 0 retries and return grounded fallback."""
    service = CoachAIService()
    error_429 = Exception("429 RESOURCE_EXHAUSTED: Free tier quota exceeded")
    service.gemini.client.aio.models.generate_content = AsyncMock(side_effect=error_429)

    context = CoachContextPayload(
        candidate_name="Alex Candidate",
        current_session={"target_role": "Backend Engineer", "overall_score": 80},
        transcript_turns=[],
        evaluation_report={},
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    debrief = await service.generate_initial_debrief(context)

    # Exactly 1 attempt made (fail fast, no retry amplification)
    assert service.gemini.client.aio.models.generate_content.call_count == 1
    assert "Alex Candidate" in debrief
    assert "80/100" in debrief


# ==============================================================================
# 10. Coach Gemini transient 503 / timeout -> bounded retry (max 2 attempts)
# ==============================================================================
@pytest.mark.asyncio
async def test_coach_gemini_transient_503_bounded_retry():
    """Transient HTTP 503 UNAVAILABLE retries at most once (total 2 attempts) before falling back."""
    service = CoachAIService()
    error_503 = Exception("503 UNAVAILABLE: Server busy")
    service.gemini.client.aio.models.generate_content = AsyncMock(side_effect=error_503)

    context = CoachContextPayload(
        candidate_name="Alex Candidate",
        current_session={"target_role": "Backend Engineer", "overall_score": 80},
        transcript_turns=[],
        evaluation_report={},
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        debrief = await service.generate_initial_debrief(context)

    # Exactly 2 attempts made
    assert service.gemini.client.aio.models.generate_content.call_count == 2
    assert "Alex Candidate" in debrief


# ==============================================================================
# 11. Strict User and Session Isolation
# ==============================================================================
@pytest.mark.asyncio
async def test_strict_user_and_session_isolation(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """User B cannot fetch history or initialize conversation for User A's session."""
    headers_a = await _register_user(client, "user_a_isolation_coach@example.com")
    headers_b = await _register_user(client, "user_b_isolation_coach@example.com")

    session_a_id = await _create_completed_session(client, headers_a)

    # User B tries to initialize on User A's session -> 404
    init_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_a_id, "auto_debrief": True},
        headers=headers_b,
    )
    assert init_res.status_code == 404

    # User B tries to fetch history on User A's session -> 404
    hist_res = await client.get(
        f"/api/v1/coach/history/{session_a_id}", headers=headers_b
    )
    assert hist_res.status_code == 404


# ==============================================================================
# 12. Grounded ActionableCoachingPlan remains present
# ==============================================================================
@pytest.mark.asyncio
async def test_actionable_coaching_plan_present_in_response(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """Coach conversation response includes deterministic ActionableCoachingPlanDTO."""
    headers = await _register_user(client, "coach_action_plan_test@example.com")
    session_id = await _create_completed_session(client, headers)

    res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "actionable_plan" in data
    assert "weakness_resolutions" in data


# ==============================================================================
# 13. Historical progress intelligence & weakness resolutions remain present
# ==============================================================================
@pytest.mark.asyncio
async def test_history_endpoint_contains_resolutions_and_plan(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """GET /coach/history/{session_id} includes weakness_resolutions list."""
    headers = await _register_user(client, "coach_hist_resolutions@example.com")
    session_id = await _create_completed_session(client, headers)

    res = await client.get(f"/api/v1/coach/history/{session_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["weakness_resolutions"], list)


# ==============================================================================
# 14. Persisted assistant response survives reload without Gemini
# ==============================================================================
@pytest.mark.asyncio
async def test_persisted_assistant_response_survives_reload(
    client: AsyncClient, mock_coach_gemini_pipeline
):
    """After chat exchange, fetching history multiple times returns full transcript with 0 Gemini calls."""
    mock_debrief, mock_chat = mock_coach_gemini_pipeline
    headers = await _register_user(client, "coach_persist_reload@example.com")
    session_id = await _create_completed_session(client, headers)

    conv_id = (
        await client.post(
            "/api/v1/coach/conversation",
            json={"session_id": session_id, "auto_debrief": True},
            headers=headers,
        )
    ).json()["id"]

    await client.post(
        "/api/v1/coach/chat",
        json={"conversation_id": conv_id, "message": "Tell me how to improve."},
        headers=headers,
    )

    debrief_calls_before = mock_debrief.call_count
    chat_calls_before = mock_chat.call_count

    # Fetch history 5 times
    for _ in range(5):
        hist = await client.get(f"/api/v1/coach/history/{session_id}", headers=headers)
        assert hist.status_code == 200
        assert hist.json()["total_messages"] == 3

    # ZERO additional Gemini calls
    assert mock_debrief.call_count == debrief_calls_before
    assert mock_chat.call_count == chat_calls_before
