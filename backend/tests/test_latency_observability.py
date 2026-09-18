"""Tests for Latency Observability, High-Resolution Monotonic Instrumentation, and Server-Timing Headers (Task 7.2)."""

import logging
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.services.interview_service import format_server_timing


@pytest.fixture
def mock_gemini_turn_engine():
    """Mock Gemini initial question and next turn decisions for controlled timing tests."""
    with patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
    ) as mock_initial, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
    ) as mock_next:
        mock_initial.return_value = GeneratedQuestion(
            question_text="Could you walk me through how you design high-throughput REST APIs in FastAPI?",
            ideal_answer="Detailed explanation of async coroutines, dependency injection, and connection pooling.",
            primary_concept="API Design",
        )
        mock_next.return_value = NextTurnDecision(
            is_follow_up=True,
            follow_up_reasoning="Probing connection pooling resilience.",
            question_text="How do you configure database connection pools to prevent exhaustion under traffic spikes?",
            ideal_answer="Pool sizing, queue timeouts, max overflow, and health checks.",
            primary_concept="Connection Pooling",
            is_interview_complete=False,
        )
        yield mock_initial, mock_next


def parse_server_timing(header_str: str) -> dict[str, float]:
    """Helper to parse RFC 9110 / W3C Server-Timing header into metric->duration dict."""
    results = {}
    if not header_str:
        return results
    entries = [e.strip() for e in header_str.split(",")]
    for entry in entries:
        parts = [p.strip() for p in entry.split(";")]
        metric_name = parts[0]
        for p in parts[1:]:
            if p.startswith("dur="):
                results[metric_name] = float(p.split("=")[1])
    return results


def test_format_server_timing_utility():
    """T05: Verify format_server_timing creates valid W3C Server-Timing strings."""
    metrics = {
        "db-fetch": 8.24,
        "semantic": 4.12,
        "planning": 2.71,
        "gemini": 1834.60,
        "db-commit": 5.30,
        "total": 1858.42,
    }
    formatted = format_server_timing(metrics)
    assert formatted == "db-fetch;dur=8.2, semantic;dur=4.1, planning;dur=2.7, gemini;dur=1834.6, db-commit;dur=5.3, total;dur=1858.4"
    parsed = parse_server_timing(formatted)
    assert parsed["db-fetch"] == 8.2
    assert parsed["gemini"] == 1834.6
    assert parsed["total"] == 1858.4


@pytest.mark.asyncio
async def test_start_interview_emits_server_timing(client: AsyncClient):
    """T01, T03, T05: Start interview emits Server-Timing header with db-fetch, db-commit, and total."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "timing_start@example.com",
            "password": "SecurePass!123",
            "full_name": "Timing Start User",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Software Engineer",
            "seniority_level": "senior",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    session_id = create_res.json()["id"]

    # Start session -> creates Turn 0
    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    assert start_res.status_code == 200
    assert "Server-Timing" in start_res.headers
    timing_header = start_res.headers["Server-Timing"]
    parsed = parse_server_timing(timing_header)

    assert "db-fetch" in parsed, "db-fetch duration must be present in Server-Timing"
    assert "db-commit" in parsed, "db-commit duration must be present in Server-Timing"
    assert "total" in parsed, "total duration must be present in Server-Timing"
    assert parsed["total"] >= parsed["db-fetch"]


@pytest.mark.asyncio
async def test_answer_submission_emits_complete_server_timing(
    client: AsyncClient, mock_gemini_turn_engine
):
    """T01, T02, T03, T05: Answer submission emits Server-Timing with all critical boundaries."""
    mock_initial, mock_next = mock_gemini_turn_engine

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "timing_answer@example.com",
            "password": "SecurePass!123",
            "full_name": "Timing Answer User",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

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
    session_id = create_res.json()["id"]

    start_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/start",
        headers=headers,
    )
    t0_id = start_res.json()["id"]

    # 1. Answer Turn 0 (Intro warm-up -> Generates Core Q1 via Gemini)
    t0_ans_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
        json={"candidate_answer": "I am a backend engineer with 4 years of Python experience."},
        headers=headers,
    )
    assert t0_ans_res.status_code == 200
    assert "Server-Timing" in t0_ans_res.headers
    t0_timings = parse_server_timing(t0_ans_res.headers["Server-Timing"])

    assert "db-fetch" in t0_timings
    assert "planning" in t0_timings
    assert "gemini" in t0_timings
    assert "db-commit" in t0_timings
    assert "total" in t0_timings
    assert mock_initial.call_count == 1

    t1_id = t0_ans_res.json()["next_turn"]["id"]

    # 2. Answer Turn 1 (Core Q1 -> Evaluates semantics + Generates Turn 2 via Gemini)
    t1_ans_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t1_id}/answer",
        json={"candidate_answer": "I build async endpoints using FastAPI, Pydantic models, and SQLAlchemy 2.0."},
        headers=headers,
    )
    assert t1_ans_res.status_code == 200
    assert "Server-Timing" in t1_ans_res.headers
    t1_timings = parse_server_timing(t1_ans_res.headers["Server-Timing"])

    # Verify all 6 timing boundaries are present on standard turn answers
    assert "db-fetch" in t1_timings, "db-fetch timing missing"
    assert "semantic" in t1_timings, "semantic evaluation timing missing"
    assert "planning" in t1_timings, "question planning timing missing"
    assert "gemini" in t1_timings, "gemini latency timing missing"
    assert "db-commit" in t1_timings, "db-commit timing missing"
    assert "total" in t1_timings, "total request timing missing"

    assert t1_timings["total"] >= t1_timings["gemini"]
    assert mock_next.call_count == 1


@pytest.mark.asyncio
async def test_no_sensitive_data_in_timing_logs(
    client: AsyncClient, mock_gemini_turn_engine, caplog
):
    """T04: Verify structured server logs contain timing metrics with ZERO PII/tokens/prompts."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "secret_timing@example.com",
            "password": "SecurePass!123",
            "full_name": "Secret User",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "DevOps Engineer",
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
    t0_id = start_res.json()["id"]

    secret_answer = "MY_SECRET_CANDIDATE_ANSWER_TOKEN_XYZ_12345"
    with caplog.at_level(logging.INFO):
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
            json={"candidate_answer": secret_answer},
            headers=headers,
        )

    timing_logs = [r.message for r in caplog.records if "processed in" in r.message or "timing" in r.message.lower()]
    assert len(timing_logs) > 0, "Expected timing log records to be emitted"

    for log_msg in timing_logs:
        assert secret_answer not in log_msg
        assert "Bearer" not in log_msg
        assert "token" not in log_msg.lower() or "turn_id" in log_msg


@pytest.mark.asyncio
async def test_idempotent_answer_replay_timing_and_zero_extra_gemini_calls(
    client: AsyncClient, mock_gemini_turn_engine
):
    """T13, T14: Idempotent resubmission produces timing with ZERO additional Gemini calls."""
    mock_initial, mock_next = mock_gemini_turn_engine

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "idempotent_timing@example.com",
            "password": "SecurePass!123",
            "full_name": "Idempotent Timing User",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Data Engineer",
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
    t0_id = start_res.json()["id"]

    # Submit answer attempt 1
    ans1_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
        json={"candidate_answer": "Introduction response for data engineer."},
        headers=headers,
    )
    assert ans1_res.status_code == 200
    assert mock_initial.call_count == 1

    # Submit identical answer attempt 2 (idempotent replay)
    ans2_res = await client.post(
        f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
        json={"candidate_answer": "Introduction response for data engineer."},
        headers=headers,
    )
    assert ans2_res.status_code == 200
    assert "Server-Timing" in ans2_res.headers
    replay_timings = parse_server_timing(ans2_res.headers["Server-Timing"])
    assert "db-fetch" in replay_timings
    assert "total" in replay_timings

    # Zero additional Gemini calls made!
    assert mock_initial.call_count == 1
    assert mock_next.call_count == 0


@pytest.mark.asyncio
async def test_interview_budgets_unchanged(client: AsyncClient):
    """T15, T16: Verify Quick (3 core, max 6) and Full (6 core, max 10) budgets remain exact."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "budget_check@example.com",
            "password": "SecurePass!123",
            "full_name": "Budget User",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Quick Mode
    quick_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Frontend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
        },
        headers=headers,
    )
    quick_session = quick_res.json()
    assert quick_session["planned_core_questions"] == 3
    assert quick_session["max_total_turns"] == 6

    # Abandon quick session to create full session
    await client.post(
        f"/api/v1/interviews/sessions/{quick_session['id']}/abandon",
        headers=headers,
    )

    # Full Mode
    full_res = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Frontend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "full",
        },
        headers=headers,
    )
    full_session = full_res.json()
    assert full_session["planned_core_questions"] == 6
    assert full_session["max_total_turns"] == 10

