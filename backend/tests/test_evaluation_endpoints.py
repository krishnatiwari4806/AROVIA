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
                    turn_index=1,
                    relevance_score=95,
                    correctness_score=92,
                    keywords_score=90,
                    clarity_score=95,
                    confidence_score=90,
                    covered_concepts=["WAL Bypass", "Crash Safety Trade-offs"],
                    missed_concepts=["Replication Ineligibility"],
                    ideal_answer_comparison="Accurate explanation of WAL bypass speedup and crash implications.",
                    turn_feedback="Excellent awareness of database failure boundaries.",
                ),
            ],
            top_strengths=[
                StrengthItem(
                    title="Deep PostgreSQL Mastery",
                    description="Demonstrated nuanced understanding of write performance and WAL trade-offs.",
                    evidence_turn_index=0,
                )
            ],
            top_improvements=[
                ImprovementItem(
                    title="Partitioning Strategies",
                    description="Could explore declarative range and hash partitioning for multi-terabyte scale.",
                    actionable_recommendation="Review PostgreSQL declarative partitioning guides.",
                    evidence_turn_index=0,
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
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial:
        from app.schemas.interview import GeneratedQuestion, NextTurnDecision

        mock_initial.return_value = GeneratedQuestion(
            question_text="How do you handle high-throughput writes in PostgreSQL?",
            ideal_answer="Explanation covering connection pooling, batching, and WAL tuning.",
            primary_concept="Database Write Scaling",
        )
        start_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start",
            headers=headers,
        )
        assert start_res.status_code == 200
        turn0_id = start_res.json()["id"]

    # 4. Answer Turn 0
    with patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_next.return_value = NextTurnDecision(
            is_follow_up=False,
            is_interview_complete=True,
            question_text=None,
            follow_up_reasoning="Candidate answered thoroughly.",
        )
        ans_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
            json={
                "candidate_answer": "We use connection pooling with asyncpg and bulk inserts for high throughput writes.",
                "turn_duration_sec": 75,
            },
            headers=headers,
        )
        assert ans_res.status_code == 200
        assert ans_res.json()["is_interview_complete"] is True

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

    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial:
        from app.schemas.interview import GeneratedQuestion, NextTurnDecision

        mock_initial.return_value = GeneratedQuestion(
            question_text="Describe distributed caching strategies.",
            ideal_answer="Redis cluster, cache invalidation, write-through vs cache-aside.",
            primary_concept="Caching Architecture",
        )
        start_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/start",
            headers=headers,
        )
        turn0_id = start_res.json()["id"]

    # Answer Turn
    with patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_next.return_value = NextTurnDecision(
            is_follow_up=False,
            is_interview_complete=True,
            question_text=None,
        )
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{turn0_id}/answer",
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
