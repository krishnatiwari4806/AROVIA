"""Integration tests for Coach REST API Endpoints, Anti-IDOR Security, and Persistence."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient


@pytest.fixture
def mock_coach_ai():
    """Mock CoachAIService methods at the service boundary."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### AI Coach Debrief\n\nGreat systems analysis on distributed locking!"
        )
        mock_chat.return_value = {
            "coach_response": "To improve your answer, discuss Redlock algorithm trade-offs and clock skew.",
            "suggested_followups": [
                "How does clock drift affect distributed locks?",
                "Give me a model answer for Turn 1.",
            ],
        }
        yield {"debrief": mock_debrief, "chat": mock_chat}


async def create_user_and_session(
    client: AsyncClient, email: str, full_name: str, password: str = "StrongPassword123!"
):
    """Helper to register a user, log in, create a completed session, and return headers + session_id."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Distributed Systems Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    return headers, session_id


# =========================================================================
# B. COACH ENDPOINT TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_endpoint_get_or_create_conversation_success(
    client: AsyncClient, mock_coach_ai
):
    """Test POST /api/v1/coach/conversation initializes conversation with debrief and follow-ups."""
    headers, session_id = await create_user_and_session(
        client, "coach_user_1@example.com", "Coach Candidate 1"
    )

    # 1. Initialize conversation with auto-debrief
    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert conv_res.status_code == 200
    conv_data = conv_res.json()

    assert conv_data["id"] is not None
    assert conv_data["session_id"] == session_id
    assert len(conv_data["messages"]) == 1
    assert conv_data["messages"][0]["sender"] == "coach"
    assert "AI Coach Debrief" in conv_data["messages"][0]["message_text"]
    assert len(conv_data["suggested_followups"]) == 3

    # 2. Idempotent call returns existing conversation without re-debriefing
    conv_res_2 = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    assert conv_res_2.status_code == 200
    conv_data_2 = conv_res_2.json()
    assert conv_data_2["id"] == conv_data["id"]
    assert len(conv_data_2["messages"]) == 1
    assert mock_coach_ai["debrief"].call_count == 1


@pytest.mark.asyncio
async def test_endpoint_get_or_create_conversation_without_debrief(
    client: AsyncClient, mock_coach_ai
):
    """Test POST /api/v1/coach/conversation with auto_debrief=False creates an empty conversation."""
    headers, session_id = await create_user_and_session(
        client, "coach_user_2@example.com", "Coach Candidate 2"
    )

    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": False},
        headers=headers,
    )
    assert conv_res.status_code == 200
    conv_data = conv_res.json()
    assert len(conv_data["messages"]) == 0
    assert mock_coach_ai["debrief"].call_count == 0


@pytest.mark.asyncio
async def test_endpoint_chat_success(
    client: AsyncClient, mock_coach_ai
):
    """Test POST /api/v1/coach/chat accepts inquiry and returns coach response + suggested followups."""
    headers, session_id = await create_user_and_session(
        client, "coach_user_3@example.com", "Coach Candidate 3"
    )

    # Initialize conversation
    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": False},
        headers=headers,
    )
    conv_id = conv_res.json()["id"]

    # Send chat message
    chat_res = await client.post(
        "/api/v1/coach/chat",
        json={
            "conversation_id": conv_id,
            "message": "How do I explain distributed lock safety under network partitions?",
            "context_turn_index": 0,
        },
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    assert chat_data["user_message"]["sender"] == "user"
    assert chat_data["user_message"]["message_text"] == "How do I explain distributed lock safety under network partitions?"
    assert chat_data["user_message"]["context_turn_index"] == 0

    assert chat_data["coach_message"]["sender"] == "coach"
    assert "Redlock algorithm trade-offs" in chat_data["coach_message"]["message_text"]
    assert chat_data["coach_message"]["context_turn_index"] == 0

    assert len(chat_data["suggested_followups"]) == 2


@pytest.mark.asyncio
async def test_endpoint_get_history(
    client: AsyncClient, mock_coach_ai
):
    """Test GET /api/v1/coach/history/{session_id} retrieves chronological coach message history."""
    headers, session_id = await create_user_and_session(
        client, "coach_user_4@example.com", "Coach Candidate 4"
    )

    # 1. Check history before conversation is created
    empty_res = await client.get(
        f"/api/v1/coach/history/{session_id}",
        headers=headers,
    )
    assert empty_res.status_code == 200
    assert empty_res.json()["total_messages"] == 0
    assert empty_res.json()["messages"] == []

    # 2. Create conversation with debrief + 1 chat message
    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": True},
        headers=headers,
    )
    conv_id = conv_res.json()["id"]

    await client.post(
        "/api/v1/coach/chat",
        json={
            "conversation_id": conv_id,
            "message": "Give me recommendations for Turn 1.",
        },
        headers=headers,
    )

    # 3. Retrieve populated history
    hist_res = await client.get(
        f"/api/v1/coach/history/{session_id}",
        headers=headers,
    )
    assert hist_res.status_code == 200
    hist_data = hist_res.json()

    assert hist_data["session_id"] == session_id
    assert hist_data["total_messages"] == 3
    assert hist_data["messages"][0]["sender"] == "coach"
    assert hist_data["messages"][1]["sender"] == "user"
    assert hist_data["messages"][2]["sender"] == "coach"


@pytest.mark.asyncio
async def test_endpoint_add_raw_message(
    client: AsyncClient
):
    """Test POST /api/v1/coach/messages appends raw candidate note into conversation."""
    headers, session_id = await create_user_and_session(
        client, "coach_user_5@example.com", "Coach Candidate 5"
    )

    conv_res = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id, "auto_debrief": False},
        headers=headers,
    )
    conv_id = conv_res.json()["id"]

    msg_res = await client.post(
        "/api/v1/coach/messages",
        json={
            "conversation_id": conv_id,
            "sender": "user",
            "message_text": "Remember to review consensus protocols tonight.",
            "context_turn_index": 2,
        },
        headers=headers,
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["conversation_id"] == conv_id
    assert msg_data["sender"] == "user"
    assert msg_data["message_text"] == "Remember to review consensus protocols tonight."
    assert msg_data["context_turn_index"] == 2


# =========================================================================
# C. SECURITY & ANTI-IDOR ENDPOINT TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_endpoint_unauthenticated_requests_rejected(
    client: AsyncClient
):
    """Verify that unauthenticated requests to all Coach endpoints return HTTP 401."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    # POST /conversation
    res1 = await client.post("/api/v1/coach/conversation", json={"session_id": fake_id})
    assert res1.status_code == 401

    # POST /chat
    res2 = await client.post("/api/v1/coach/chat", json={"conversation_id": fake_id, "message": "hello"})
    assert res2.status_code == 401

    # GET /history
    res3 = await client.get(f"/api/v1/coach/history/{fake_id}")
    assert res3.status_code == 401

    # POST /messages
    res4 = await client.post("/api/v1/coach/messages", json={"conversation_id": fake_id, "message_text": "note"})
    assert res4.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_anti_idor_cross_user_isolation(
    client: AsyncClient, mock_coach_ai
):
    """Verify User B cannot access, read, or inject messages into User A's session or coach conversation."""
    # 1. Setup User A with session and conversation
    headers_a, session_id_a = await create_user_and_session(
        client, "alice_coach@example.com", "Alice Architect"
    )
    conv_res_a = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id_a, "auto_debrief": True},
        headers=headers_a,
    )
    conv_id_a = conv_res_a.json()["id"]

    # 2. Setup User B
    headers_b, _ = await create_user_and_session(
        client, "bob_intruder@example.com", "Bob Intruder"
    )

    # 3. User B attempts to initialize or access User A's session conversation -> 404
    res_b_conv = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": session_id_a, "auto_debrief": True},
        headers=headers_b,
    )
    assert res_b_conv.status_code == 404

    # 4. User B attempts to view User A's session history -> 404
    res_b_hist = await client.get(
        f"/api/v1/coach/history/{session_id_a}",
        headers=headers_b,
    )
    assert res_b_hist.status_code == 404

    # 5. User B attempts to send chat message into User A's conversation -> 404
    res_b_chat = await client.post(
        "/api/v1/coach/chat",
        json={
            "conversation_id": conv_id_a,
            "message": "Injected malicious question from User B",
        },
        headers=headers_b,
    )
    assert res_b_chat.status_code == 404

    # 6. User B attempts to append raw message to User A's conversation -> 404
    res_b_msg = await client.post(
        "/api/v1/coach/messages",
        json={
            "conversation_id": conv_id_a,
            "sender": "user",
            "message_text": "Injected note from User B",
        },
        headers=headers_b,
    )
    assert res_b_msg.status_code == 404


# =========================================================================
# E. ENDPOINT VALIDATION & EDGE CASES
# =========================================================================

@pytest.mark.asyncio
async def test_endpoint_validation_and_not_found(
    client: AsyncClient
):
    """Verify validation errors (422) for invalid payloads and 404 for nonexistent resources."""
    headers, session_id = await create_user_and_session(
        client, "coach_validation_user@example.com", "Validation Candidate"
    )

    fake_id = "00000000-0000-0000-0000-000000000000"

    # Nonexistent session on /conversation -> 404
    res1 = await client.post(
        "/api/v1/coach/conversation",
        json={"session_id": fake_id},
        headers=headers,
    )
    assert res1.status_code == 404

    # Nonexistent conversation on /chat -> 404
    res2 = await client.post(
        "/api/v1/coach/chat",
        json={"conversation_id": fake_id, "message": "Valid question text"},
        headers=headers,
    )
    assert res2.status_code == 404

    # Empty chat message string -> 422
    res3 = await client.post(
        "/api/v1/coach/chat",
        json={"conversation_id": fake_id, "message": ""},
        headers=headers,
    )
    assert res3.status_code == 422

    # Invalid sender in /messages -> 422
    res4 = await client.post(
        "/api/v1/coach/messages",
        json={"conversation_id": fake_id, "sender": "superuser", "message_text": "text"},
        headers=headers,
    )
    assert res4.status_code == 422
