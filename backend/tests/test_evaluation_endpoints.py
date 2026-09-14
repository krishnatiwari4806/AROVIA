"""Integration tests for Evaluation Endpoints and Multi-Dimensional Pipeline (Phase 6)."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.evaluation import (
    ImprovementItem,
    SessionEvaluationReport,
    StrengthItem,
    TurnEvaluationItem,
)


@pytest.fixture
def mock_gemini_evaluation():
    """Mock Gemini evaluate_interview_session structured response."""
    with patch(
        "app.services.gemini_service.GeminiService.evaluate_interview_session",
        new_callable=AsyncMock,
    ) as mock_eval:
        mock_eval.return_value = SessionEvaluationReport(
            turns_evaluation=[
                TurnEvaluationItem(
                    turn_index=0,
                    relevance_score=90,
                    correctness_score=85,
                    keywords_score=85,
                    clarity_score=90,
                    confidence_score=85,
                    covered_concepts=["Background", "Experience"],
                    missed_concepts=[],
                    ideal_answer_comparison="Clear introduction of background and experience.",
                    turn_feedback="Good concise introduction.",
                ),
                TurnEvaluationItem(
                    turn_index=1,
                    relevance_score=90,
                    correctness_score=88,
                    keywords_score=85,
                    clarity_score=90,
                    confidence_score=85,
                    covered_concepts=["Connection Pooling", "Bulk Inserts", "Unlogged Tables"],
                    missed_concepts=["Table Partitioning"],
                    ideal_answer_comparison="Great practical knowledge of asyncpg and write throughput.",
                    turn_feedback="Solid grasp of PostgreSQL write optimization.",
                ),
                TurnEvaluationItem(
                    turn_index=2,
                    relevance_score=92,
                    correctness_score=90,
                    keywords_score=88,
                    clarity_score=90,
                    confidence_score=88,
                    covered_concepts=["Saga Pattern", "Choreography", "RabbitMQ"],
                    missed_concepts=[],
                    ideal_answer_comparison="Clear understanding of distributed transaction saga patterns.",
                    turn_feedback="Strong knowledge of message-driven saga choreography.",
                ),
                TurnEvaluationItem(
                    turn_index=3,
                    relevance_score=95,
                    correctness_score=92,
                    keywords_score=90,
                    clarity_score=95,
                    confidence_score=90,
                    covered_concepts=["OpenTelemetry", "Distributed Tracing"],
                    missed_concepts=[],
                    ideal_answer_comparison="Accurate explanation of distributed tracing.",
                    turn_feedback="Excellent observability awareness.",
                ),
            ],
            top_strengths=[
                StrengthItem(
                    title="Deep PostgreSQL Mastery",
                    description="Demonstrated nuanced understanding of write performance and WAL trade-offs.",
                    evidence_turn_index=1,
                )
            ],
            top_improvements=[
                ImprovementItem(
                    title="Partitioning Strategies",
                    description="Could explore declarative range and hash partitioning for multi-terabyte scale.",
                    actionable_recommendation="Review PostgreSQL declarative partitioning guides.",
                    evidence_turn_index=1,
                )
            ],
            executive_summary="Candidate demonstrated impressive database engineering competence across multiple challenging turns.",
        )
        yield mock_eval


@pytest.mark.asyncio
async def test_evaluate_session_endpoint_success(
    client: AsyncClient, mock_gemini_evaluation
):
    """Test POST /sessions/{id}/evaluate orchestrates evaluation and finalizes session."""
    # 1. Register candidate and get auth token
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "eval_candidate1@example.com",
            "password": "StrongPassword!123",
            "full_name": "Eval Candidate 1",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create a session
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

    # 3. Start interview (Turn 0)
    from app.schemas.interview import GeneratedQuestion, NextTurnDecision

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res.status_code == 200
    turn0_id = start_res.json()["id"]

    # 4. Answer Turn 0 (Intro), 1 (Core 1), 2 (Core 2), and 3 (Core 3) to complete all 3 quick-mode core questions
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_initial.return_value = GeneratedQuestion(
            question_text="How do you handle high-throughput writes in PostgreSQL?",
            ideal_answer="Explanation covering connection pooling, batching, and WAL tuning.",
            primary_concept="Database Write Scaling",
        )
        mock_next.side_effect = [
            NextTurnDecision(
                is_follow_up=False,
                is_interview_complete=False,
                question_text="How do you handle transactions across microservices?",
                ideal_answer="Saga pattern with compensating transactions.",
                primary_concept="Distributed Transactions",
                follow_up_reasoning="Good answer, moving to next core competency.",
            ),
            NextTurnDecision(
                is_follow_up=False,
                is_interview_complete=False,
                question_text="How do you monitor distributed systems and trace requests?",
                ideal_answer="Distributed tracing using OpenTelemetry and context propagation.",
                primary_concept="Observability",
                follow_up_reasoning="Moving to system observability.",
            ),
            NextTurnDecision(
                is_follow_up=False,
                is_interview_complete=True,
                question_text="",
                ideal_answer="",
                primary_concept="",
                follow_up_reasoning="Completed planned interview questions.",
            ),
        ]
        # Turn 0: Intro answer -> generates Core 1 via mock_initial
        ans0 = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
            json={
                "candidate_answer": "Hi, I am an experienced backend engineer with 5 years in Python and distributed systems.",
                "turn_duration_sec": 30,
            },
            headers=headers,
        )
        assert ans0.status_code == 200
        assert ans0.json()["is_interview_complete"] is False
        turn1_id = ans0.json()["next_turn"]["id"]

        # Turn 1: Core 1 answer -> generates Core 2 via mock_next
        ans1 = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
            json={
                "candidate_answer": "We use connection pooling with asyncpg, batching with bulk inserts, and WAL tuning for high throughput writes.",
                "turn_duration_sec": 75,
            },
            headers=headers,
        )
        assert ans1.status_code == 200
        assert ans1.json()["is_interview_complete"] is False
        turn2_id = ans1.json()["next_turn"]["id"]

        # Turn 2: Core 2 answer -> generates Core 3 via mock_next
        ans2 = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn2_id}/answer",
            json={
                "candidate_answer": "We use choreography-based Sagas with compensating transactions and RabbitMQ message queues.",
                "turn_duration_sec": 60,
            },
            headers=headers,
        )
        assert ans2.status_code == 200
        assert ans2.json()["is_interview_complete"] is False
        turn3_id = ans2.json()["next_turn"]["id"]

        # Turn 3: Core 3 answer completes the session (3 of 3 core completed)
        ans3 = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn3_id}/answer",
            json={
                "candidate_answer": "We implement distributed tracing with OpenTelemetry and context propagation to track requests.",
                "turn_duration_sec": 50,
            },
            headers=headers,
        )
        assert ans3.status_code == 200
        assert ans3.json()["is_interview_complete"] is True

    # 5. Evaluate the completed interview session
    eval_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/evaluate",
        headers=headers,
    )
    assert eval_res.status_code == 200
    data = eval_res.json()

    assert data["session_id"] == session_id
    assert data["status"] == "completed"
    assert 80 <= data["overall_score"] <= 100
    assert "dimension_scores" in data
    assert data["dimension_scores"]["correctness"] >= 80
    assert data["dimension_scores"]["relevance"] >= 80
    assert len(data["turns_evaluation"]) >= 1
    assert len(data["top_strengths"]) >= 1
    assert len(data["top_improvements"]) >= 1
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_session_evaluation_saved_report(
    client: AsyncClient, mock_gemini_evaluation
):
    """Test GET /sessions/{id}/evaluation retrieves saved evaluation report card."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "eval_candidate2@example.com",
            "password": "StrongPassword!123",
            "full_name": "Eval Candidate 2",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create and start session
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
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    turn0_id = start_res.json()["id"]

    # Answer Turn 0 (Intro) -> Core 1
    ans0 = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
        json={
            "candidate_answer": "Candidate introduction overview.",
            "turn_duration_sec": 30,
        },
        headers=headers,
    )
    turn1_id = ans0.json()["next_turn"]["id"]

    # Answer Core 1
    await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{turn1_id}/answer",
        json={
            "candidate_answer": "We use Redis cache-aside with TTL and pub-sub for invalidation.",
            "turn_duration_sec": 90,
        },
        headers=headers,
    )

    # First trigger evaluation
    eval_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/evaluate",
        headers=headers,
    )
    assert eval_res.status_code == 200

    # Now GET evaluation
    get_res = await client.get(
        f"/api/v1/interviews/sessions/{session_id}/evaluation",
        headers=headers,
    )
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["session_id"] == session_id
    assert get_data["overall_score"] > 0
    assert len(get_data["top_strengths"]) >= 1


@pytest.mark.asyncio
async def test_evaluate_unauthorized_user_fails(
    client: AsyncClient,
):
    """Test unauthenticated or unauthorized access to evaluation endpoints is rejected."""
    fake_session_id = "00000000-0000-0000-0000-000000000000"

    resp1 = await client.post(
        f"/api/v1/interviews/sessions/{fake_session_id}/evaluate"
    )
    assert resp1.status_code == 401

    resp2 = await client.get(
        f"/api/v1/interviews/sessions/{fake_session_id}/evaluation"
    )
    assert resp2.status_code == 401
