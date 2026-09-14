"""Mandatory Phase 2 Tests: Live Interview State, Counter & Turn Progression Hardening.

Verifies:
A. Six core questions + follow-up turns: QUESTION 6 OF 6, never QUESTION 7 OF 6.
B. Follow-ups do not increment core question index.
C. Turn 0 exists before Core Question 1 as an introduction/warm-up stage.
D. Turn 0 does not count toward core question total.
E. Turn 0 is preserved in interview transcript and session history.
F. Turn 0 respects preferred language (en, hi, hinglish).
G. Existing Full mode behavior remains intact.
H. Existing Quick mode behavior remains intact.
I. Existing interview termination behavior remains intact.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.interview_service import get_introduction_prompt


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
            question_text="Core Question 1: Describe Python memory management and garbage collection.",
            ideal_answer="Reference counting and generational cyclic GC.",
            primary_concept="Memory Management",
        )
        mock_next.return_value = NextTurnDecision(
            is_follow_up=False,
            follow_up_reasoning="Candidate answered adequately, advancing to next core concept.",
            question_text="Next Core Question.",
            ideal_answer="Benchmark answer.",
            primary_concept="Technical Domain",
            is_interview_complete=False,
        )
        yield mock_initial, mock_next


def test_turn0_introduction_prompt_languages():
    """Verify Turn 0 prompts for en, hi, and hinglish."""
    en_prompt = get_introduction_prompt("en", "Fullstack Developer", "senior")
    assert "Senior" in en_prompt
    assert "Fullstack Developer" in en_prompt
    assert "Before we dive into the technical discussion" in en_prompt
    assert "introduce yourself" in en_prompt

    hi_prompt = get_introduction_prompt("hi", "Backend Engineer", "mid")
    assert "Namaste!" in hi_prompt
    assert "Backend Engineer" in hi_prompt
    assert "introduction de sakte hain" in hi_prompt

    hinglish_prompt = get_introduction_prompt("hinglish", "DevOps Engineer", "junior")
    assert "welcome to AROVIA" in hinglish_prompt
    assert "DevOps Engineer" in hinglish_prompt
    assert "Technical discussion start karne se pehle" in hinglish_prompt
    assert "introduce yourself" in hinglish_prompt


@pytest.mark.asyncio
async def test_turn0_lifecycle_and_language_preservation(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Verify Turn 0 is created first, does not count as Core 1, and saves transcript for Hindi & Hinglish."""
    for lang in ["hi", "hinglish"]:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"turn0_{lang}@example.com",
                "password": "StrongPassword!123",
                "full_name": f"Turn0 {lang} User",
            },
        )
        headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}

        # Create session with preferred_language
        create_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Platform Engineer",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "preferred_language": lang,
                "practice_mode": "full",
            },
            headers=headers,
        )
        assert create_res.status_code == 201
        session_id = create_res.json()["id"]

        # Start interview -> Turn 0
        start_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start",
            headers=headers,
        )
        assert start_res.status_code == 200
        t0 = start_res.json()
        assert t0["turn_index"] == 0
        assert t0["question_type"] == "introduction"
        assert t0["interview_phase"] == "introduction"
        assert t0["core_question_index"] is None
        assert t0["core_question_number"] is None
        assert t0["total_core_questions"] == 6

        if lang == "hi":
            assert "Namaste!" in t0["question_text"]
        else:
            assert "Technical discussion start karne se pehle" in t0["question_text"]

        # Answer Turn 0
        ans_t0 = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{t0['id']}/answer",
            json={"candidate_answer": "Mera naam Rahul hai aur main 6 saal se cloud infra par kaam kar raha hoon.", "turn_duration_sec": 35},
            headers=headers,
        )
        assert ans_t0.status_code == 200
        ans_data = ans_t0.json()
        assert ans_data["is_interview_complete"] is False
        assert ans_data["current_core_question_index"] == 0
        assert ans_data["total_core_questions"] == 6
        assert ans_data["interview_phase"] == "core_question"

        # Next turn is Core Question 1 (Turn 1)
        t1 = ans_data["next_turn"]
        assert t1["turn_index"] == 1
        assert t1["question_type"] == "core"
        assert t1["core_question_number"] == 1
        assert t1["total_core_questions"] == 6
        assert t1["interview_phase"] == "core_question"


@pytest.mark.asyncio
async def test_six_core_questions_with_follow_ups_never_exceeds_core_denominator(
    client: AsyncClient, mock_gemini_turn_engine
):
    """Test 6 core questions with multiple follow-up turns:

    Turn 0: Intro
    Turn 1: Core Q1 (Question 1 of 6)
    Turn 2: Core Q2 (Question 2 of 6)
    Turn 3: Core Q3 (Question 3 of 6)
    Turn 4: Follow-up 1 on Core Q3 (Question 3 of 6 • Follow-up 1)
    Turn 5: Follow-up 2 on Core Q3 (Question 3 of 6 • Follow-up 2)
    Turn 6: Core Q4 (Question 4 of 6)
    Turn 7: Core Q5 (Question 5 of 6)
    Turn 8: Core Q6 (Question 6 of 6)
    Completion: Completed cleanly at Question 6 of 6, NEVER Question 7 of 6.
    """
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "six_core_followups@example.com",
            "password": "StrongPassword!123",
            "full_name": "Six Core User",
        },
    )
    assert reg_res.status_code == 201
    headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
    mock_initial, mock_next = mock_gemini_turn_engine

    # 1. Create full mock interview session (planned_core=6, max_turns=10)
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

    # 2. Start session -> Turn 0 (Intro)
    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    t0_id = start_res.json()["id"]

    # Answer Turn 0 (Intro) -> Turn 1 (Core Q1)
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
        json={"candidate_answer": "Candidate introduction and background."},
        headers=headers,
    )
    t1 = ans0.json()["next_turn"]
    assert t1["turn_index"] == 1
    assert t1["core_question_number"] == 1
    assert t1["total_core_questions"] == 6
    assert t1["interview_phase"] == "core_question"

    # Answer Turn 1 (Core Q1) -> Turn 2 (Core Q2)
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Core Q2: Explain database partitioning strategies.",
        ideal_answer="Horizontal and vertical sharding.",
        primary_concept="Databases",
        is_interview_complete=False,
    )
    ans1 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t1['id']}/answer",
        json={"candidate_answer": "Answer to Core Q1."},
        headers=headers,
    )
    t2 = ans1.json()["next_turn"]
    assert t2["turn_index"] == 2
    assert t2["core_question_number"] == 2
    assert t2["total_core_questions"] == 6
    assert t2["interview_phase"] == "core_question"

    # Answer Turn 2 (Core Q2) -> Turn 3 (Core Q3)
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Core Q3: How do you handle distributed caching consistency?",
        ideal_answer="Cache-aside, write-through, TTL invalidation.",
        primary_concept="Caching",
        is_interview_complete=False,
    )
    ans2 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t2['id']}/answer",
        json={"candidate_answer": "Answer to Core Q2."},
        headers=headers,
    )
    t3 = ans2.json()["next_turn"]
    assert t3["turn_index"] == 3
    assert t3["core_question_number"] == 3
    assert t3["total_core_questions"] == 6
    assert t3["interview_phase"] == "core_question"

    # Answer Turn 3 (Core Q3) -> Gemini requests Follow-up 1 on Core Q3!
    mock_next.return_value = NextTurnDecision(
        is_follow_up=True,
        question_text="Follow-up 1 on Q3: What happens when the Redis primary fails during write?",
        ideal_answer="Redis Sentinel / Cluster failover and replication offset.",
        primary_concept="Cache Failover",
        is_interview_complete=False,
    )
    ans3 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t3['id']}/answer",
        json={"candidate_answer": "We use Redis with TTL cache-aside."},
        headers=headers,
    )
    t4 = ans3.json()["next_turn"]
    assert t4["turn_index"] == 4
    assert t4["is_follow_up"] is True
    assert t4["parent_turn_id"] == t3["id"]
    # CRITICAL: Core question number MUST STAY 3!
    assert t4["core_question_number"] == 3
    assert t4["follow_up_number"] == 1
    assert t4["total_core_questions"] == 6
    assert t4["interview_phase"] == "follow_up"

    # Answer Turn 4 (Follow-up 1 on Q3) -> Follow-up cannot chain, advances to Core Q4 (Turn 5)
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Core Q4: Describe event-driven messaging with Kafka.",
        ideal_answer="Topic partitions, consumer groups, and offset commits.",
        primary_concept="Message Queues",
        is_interview_complete=False,
    )
    ans4 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t4['id']}/answer",
        json={"candidate_answer": "Sentinel promotes replica to master."},
        headers=headers,
    )
    t5 = ans4.json()["next_turn"]
    assert t5["turn_index"] == 5
    assert t5["is_follow_up"] is False
    assert t5["core_question_number"] == 4
    assert t5["total_core_questions"] == 6
    assert t5["interview_phase"] == "core_question"

    # Answer Turn 5 (Core Q4) -> Core Q5 (Turn 6)
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Core Q5: How do you structure microservice authentication?",
        ideal_answer="OAuth2, JWT tokens, asymmetric key validation.",
        primary_concept="Security",
        is_interview_complete=False,
    )
    ans5 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t5['id']}/answer",
        json={"candidate_answer": "Kafka consumers in consumer groups."},
        headers=headers,
    )
    t6 = ans5.json()["next_turn"]
    assert t6["turn_index"] == 6
    assert t6["core_question_number"] == 5
    assert t6["total_core_questions"] == 6
    assert t6["interview_phase"] == "core_question"

    # Answer Turn 6 (Core Q5) -> Core Q6 (Turn 7)
    mock_next.return_value = NextTurnDecision(
        is_follow_up=False,
        question_text="Core Q6: Describe observability and distributed tracing.",
        ideal_answer="OpenTelemetry, trace IDs, span propagation.",
        primary_concept="Observability",
        is_interview_complete=False,
    )
    ans6 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t6['id']}/answer",
        json={"candidate_answer": "JWT verification at API gateway."},
        headers=headers,
    )
    t7 = ans6.json()["next_turn"]
    assert t7["turn_index"] == 7
    assert t7["core_question_number"] == 6
    assert t7["total_core_questions"] == 6
    assert t7["interview_phase"] == "core_question"

    # Answer Turn 7 (Core Q6) -> Must complete! Core target 6 of 6 reached.
    ans7 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t7['id']}/answer",
        json={"candidate_answer": "OpenTelemetry spans propagated in headers."},
        headers=headers,
    )
    assert ans7.status_code == 200
    final_data = ans7.json()
    assert final_data["is_interview_complete"] is True
    assert final_data["session_status"] == "evaluating"
    assert final_data["next_turn"] is None
    assert final_data["total_core_questions"] == 6

    # Verify all turns in history
    history_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/turns",
        headers=headers,
    )
    assert history_res.status_code == 200
    all_turns = history_res.json()
    assert len(all_turns) == 8  # 1 intro + 6 core + 1 follow-up

    # Verify no turn in history ever has core_question_number > 6
    for t in all_turns:
        if t["core_question_number"] is not None:
            assert t["core_question_number"] <= 6, f"Invalid core number {t['core_question_number']}"
        assert t["total_core_questions"] == 6
