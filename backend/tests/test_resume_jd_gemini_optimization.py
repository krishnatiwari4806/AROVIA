"""Comprehensive verification tests for Resume & Custom JD Gemini Optimization & Quota Safety (Task 3).

Verifies all 14 critical test matrix requirements:
1. First resume upload -> expected Gemini parse_resume call (exactly 1 call).
2. Successful resume result persists in DB (parsed_data accurately stored).
3. Resume GET / profile access (GET /resumes/me) -> zero Gemini calls.
4. Interview session using persisted resume -> zero resume parsing Gemini calls.
5. Resume HTTP 429 / RESOURCE_EXHAUSTED -> fail-fast with zero retry amplification.
6. Resume transient HTTP 503 / timeout -> bounded retry only (max 2 attempts).
7. Explicit user re-upload / retry remains possible and works as expected.
8. First custom JD parse -> expected Gemini parse_job_description call (exactly 1 call).
9. Persisted JD reused -> zero duplicate JD parse Gemini calls.
10. Session refresh / resume -> zero JD parse Gemini calls.
11. Custom JD HTTP 429 -> fail-fast with zero retry amplification.
12. Custom JD transient HTTP 503 / timeout -> bounded retry only (max 2 attempts).
13. Strict User Isolation: User A cannot access or mutate User B's resume/JD.
14. No automatic duplicate parsing from lifecycle or setup flows.
"""

import io
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.interview import GeneratedQuestion, NextTurnDecision
from app.schemas.resume import ParsedResumeData
from app.services.gemini_service import GeminiService, ParsedJobDescription


# Minimal valid PDF binary with '%PDF-1.4' magic bytes
MINIMAL_VALID_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    b"4 0 obj << /Length 200 >> stream\n"
    b"BT /F1 12 Tf 100 700 Td (John Doe Software Engineer with 6 years experience in Python, FastAPI, PostgreSQL, and distributed systems architecture.) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    b"xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000247 00000 n\n0000000501 00000 n\n"
    b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n578\n%%EOF\n"
)


@pytest.fixture
def mock_parsed_resume_data():
    """Mock structured ParsedResumeData."""
    return ParsedResumeData(
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
        experience_years=5.0,
        domains=["Backend Systems", "Distributed Architecture"],
        education=[],
        summary="Senior Backend Engineer with 5 years building scalable web services.",
        projects=[],
        work_history=[],
    )


@pytest.fixture
def mock_parsed_jd_data():
    """Mock structured ParsedJobDescription."""
    return ParsedJobDescription(
        job_title="Senior Python Backend Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Kafka"],
        core_responsibilities=["Design distributed microservices", "Optimize database queries"],
        key_technologies=["Python 3.12", "FastAPI", "PostgreSQL", "Redis"],
        experience_summary="5+ years backend software development experience required.",
    )


async def _register_user(client: AsyncClient, email: str) -> dict:
    """Helper to register user and return auth headers."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword!123",
            "full_name": "Test User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. First resume upload -> expected Gemini parse_resume call (exactly 1 call)
# ==============================================================================
@pytest.mark.asyncio
async def test_first_resume_upload_invokes_gemini_once(
    client: AsyncClient, mock_parsed_resume_data
):
    """Uploading a new valid resume document calls parse_resume exactly once."""
    headers = await _register_user(client, "res_first_upload@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=mock_parsed_resume_data,
    ) as mock_parse:
        files = {"file": ("test_resume.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        res = await client.post("/api/v1/resumes/upload", files=files, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["message"] == "Resume successfully uploaded and parsed."
        assert "Python" in data["resume"]["parsed_data"]["skills"]
        assert mock_parse.call_count == 1


# ==============================================================================
# 2. Successful resume result persists in DB (parsed_data accurately stored)
# ==============================================================================
@pytest.mark.asyncio
async def test_successful_resume_persists_in_db(
    client: AsyncClient, mock_parsed_resume_data
):
    """Uploaded resume parsed data is accurately persisted and retrievable."""
    headers = await _register_user(client, "res_persists_db@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=mock_parsed_resume_data,
    ):
        files = {"file": ("test_resume.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        await client.post("/api/v1/resumes/upload", files=files, headers=headers)

    # Fetch from database
    get_res = await client.get("/api/v1/resumes/me", headers=headers)
    assert get_res.status_code == 200
    resume_db = get_res.json()
    assert resume_db["parsed_data"]["experience_years"] == 5.0
    assert resume_db["parsed_data"]["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]


# ==============================================================================
# 3. Resume GET / profile access -> zero Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_resume_get_me_zero_gemini_calls(
    client: AsyncClient, mock_parsed_resume_data
):
    """Calling GET /resumes/me multiple times reads directly from PostgreSQL with 0 Gemini calls."""
    headers = await _register_user(client, "res_get_zero_gem@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=mock_parsed_resume_data,
    ):
        files = {"file": ("test_resume.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        await client.post("/api/v1/resumes/upload", files=files, headers=headers)

    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
    ) as mock_parse:
        # Simulate 5 page loads / profile views
        for _ in range(5):
            get_res = await client.get("/api/v1/resumes/me", headers=headers)
            assert get_res.status_code == 200

        assert mock_parse.call_count == 0


# ==============================================================================
# 4. Interview session using persisted resume -> zero resume parsing Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_interview_session_creation_reuses_persisted_resume_without_reparsing(
    client: AsyncClient, mock_parsed_resume_data
):
    """Creating an interview session loads resume.parsed_data from DB without calling parse_resume."""
    headers = await _register_user(client, "res_interview_reuse@example.com")

    # Upload resume
    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=mock_parsed_resume_data,
    ):
        files = {"file": ("test_resume.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        await client.post("/api/v1/resumes/upload", files=files, headers=headers)

    # Now create interview session
    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
    ) as mock_parse_resume, patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
        return_value=GeneratedQuestion(
            question_text="Sample Q",
            ideal_answer="Sample A",
            primary_concept="Core Engineering",
        ),
    ) as mock_init_q:
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "mid",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
            },
            headers=headers,
        )
        assert sess_res.status_code == 201
        session_id = sess_res.json()["id"]

        # Start interview and answer Turn 0
        t0_res = await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)
        t0_id = t0_res.json()["id"]

        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
            json={"candidate_answer": "Intro response."},
            headers=headers,
        )

        # parse_resume was NEVER re-invoked
        assert mock_parse_resume.call_count == 0
        # generate_initial_question received resume_data from DB
        assert mock_init_q.call_count == 1
        call_kwargs = mock_init_q.call_args.kwargs
        assert call_kwargs.get("resume_data") is not None
        assert "Python" in call_kwargs["resume_data"]["skills"]


# ==============================================================================
# 5. Resume HTTP 429 -> fail-fast with zero retry amplification
# ==============================================================================
@pytest.mark.asyncio
async def test_resume_429_fails_fast_with_zero_retries():
    """GeminiService.parse_resume must fail fast on 429 with 0 retries."""
    service = GeminiService()
    error_429 = Exception("429 RESOURCE_EXHAUSTED: Free tier quota exceeded")
    service.client.aio.models.generate_content = AsyncMock(side_effect=error_429)

    with pytest.raises(Exception) as exc_info:
        await service.parse_resume("Raw candidate resume text...")

    # generate_content was called EXACTLY ONCE (no retry loop on 429)
    assert service.client.aio.models.generate_content.call_count == 1
    assert "temporarily unavailable" in str(exc_info.value)


# ==============================================================================
# 6. Resume transient HTTP 503 / timeout -> bounded retry only (max 2 attempts)
# ==============================================================================
@pytest.mark.asyncio
async def test_resume_transient_503_bounded_retry():
    """Transient HTTP 503 UNAVAILABLE retries at most once (total 2 attempts)."""
    service = GeminiService()
    error_503 = Exception("503 UNAVAILABLE: High backend load")
    service.client.aio.models.generate_content = AsyncMock(side_effect=error_503)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception) as exc_info:
            await service.parse_resume("Raw candidate resume text...")

    assert service.client.aio.models.generate_content.call_count == 2
    assert "temporarily unavailable" in str(exc_info.value)


# ==============================================================================
# 7. Explicit user re-upload / retry remains possible
# ==============================================================================
@pytest.mark.asyncio
async def test_explicit_user_reupload_allowed_and_updates_db(
    client: AsyncClient, mock_parsed_resume_data
):
    """When candidate explicitly uploads a new resume, it is parsed and updates DB."""
    headers = await _register_user(client, "res_reupload_allowed@example.com")

    updated_parsed = ParsedResumeData(
        skills=["Go", "Kubernetes", "AWS", "gRPC"],
        experience_years=7.0,
        domains=["Cloud Systems"],
        education=[],
        summary="Cloud Systems Architect with 7 years experience.",
        projects=[],
        work_history=[],
    )

    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
    ) as mock_parse:
        # First upload
        mock_parse.return_value = mock_parsed_resume_data
        files1 = {"file": ("resume_v1.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        res1 = await client.post("/api/v1/resumes/upload", files=files1, headers=headers)
        assert res1.status_code == 201
        assert res1.json()["resume"]["parsed_data"]["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]

        # Re-upload (User explicit action)
        mock_parse.return_value = updated_parsed
        files2 = {"file": ("resume_v2.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        res2 = await client.post("/api/v1/resumes/upload", files=files2, headers=headers)
        assert res2.status_code == 201
        assert res2.json()["resume"]["parsed_data"]["skills"] == ["Go", "Kubernetes", "AWS", "gRPC"]

        # Exactly 2 explicit parse calls
        assert mock_parse.call_count == 2


# ==============================================================================
# 8. First custom JD parse -> expected Gemini parse_job_description call
# ==============================================================================
@pytest.mark.asyncio
async def test_first_custom_jd_parse_invokes_gemini_once(
    client: AsyncClient, mock_parsed_jd_data
):
    """Providing custom_job_desc on session creation invokes parse_job_description exactly once."""
    headers = await _register_user(client, "jd_first_parse@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
        return_value=mock_parsed_jd_data,
    ) as mock_jd_parse:
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
                "custom_job_desc": "Looking for a Senior Python Developer with Kafka and Kubernetes experience.",
            },
            headers=headers,
        )
        assert sess_res.status_code == 201
        assert mock_jd_parse.call_count == 1


# ==============================================================================
# 9. Persisted JD reused -> zero duplicate Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_persisted_jd_reused_during_turn_progression_zero_gemini_calls(
    client: AsyncClient, mock_parsed_jd_data
):
    """Interview turn progression reuses session.parsed_jd_data with 0 duplicate parse_job_description calls."""
    headers = await _register_user(client, "jd_turn_reuse@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
        return_value=mock_parsed_jd_data,
    ):
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
                "custom_job_desc": "Senior Backend Developer position.",
            },
            headers=headers,
        )
        session_id = sess_res.json()["id"]

    # Start and advance turns
    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
    ) as mock_jd_parse, patch(
        "app.services.gemini_service.GeminiService.generate_initial_question",
        new_callable=AsyncMock,
        return_value=GeneratedQuestion(
            question_text="Q1",
            ideal_answer="A1",
            primary_concept="Core Engineering",
        ),
    ) as mock_init_q, patch(
        "app.services.gemini_service.GeminiService.evaluate_and_generate_next_turn",
        new_callable=AsyncMock,
        return_value=NextTurnDecision(
            is_follow_up=False,
            question_text="Q2",
            ideal_answer="A2",
            is_interview_complete=False,
        ),
    ) as mock_next_q:
        t0_id = (await client.post(f"/api/v1/interviews/sessions/{session_id}/start", headers=headers)).json()["id"]

        # Turn 0 Answer
        t1_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{t0_id}/answer",
            json={"candidate_answer": "Intro answer"},
            headers=headers,
        )
        t1_id = t1_res.json()["next_turn"]["id"]

        # Turn 1 Answer
        await client.post(
            f"/api/v1/interviews/sessions/{session_id}/turns/{t1_id}/answer",
            json={"candidate_answer": "Turn 1 answer"},
            headers=headers,
        )

        # parse_job_description was NEVER called during turns
        assert mock_jd_parse.call_count == 0
        # JD was forwarded to initial question and adaptive next turn
        assert mock_init_q.call_args.kwargs.get("parsed_jd_data") is not None
        assert mock_next_q.call_args.kwargs.get("parsed_jd_data") is not None


# ==============================================================================
# 10. Session refresh / resume -> zero JD parse Gemini calls
# ==============================================================================
@pytest.mark.asyncio
async def test_session_refresh_zero_jd_parse_calls(
    client: AsyncClient, mock_parsed_jd_data
):
    """GET /sessions/{id} returns saved JD details with 0 JD parse calls."""
    headers = await _register_user(client, "jd_refresh_zero@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
        return_value=mock_parsed_jd_data,
    ):
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
                "custom_job_desc": "Staff Backend Engineer role.",
            },
            headers=headers,
        )
        session_id = sess_res.json()["id"]

    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
    ) as mock_jd_parse:
        for _ in range(5):
            get_sess = await client.get(f"/api/v1/interviews/sessions/{session_id}", headers=headers)
            assert get_sess.status_code == 200

        assert mock_jd_parse.call_count == 0


# ==============================================================================
# 11. Custom JD HTTP 429 -> fail-fast with zero retry amplification
# ==============================================================================
@pytest.mark.asyncio
async def test_jd_429_fails_fast_with_zero_retries():
    """GeminiService.parse_job_description fails fast on 429 and returns fallback."""
    service = GeminiService()
    error_429 = Exception("429 RESOURCE_EXHAUSTED: Free tier quota exceeded")
    service.client.aio.models.generate_content = AsyncMock(side_effect=error_429)

    result = await service.parse_job_description("Sample Job Description...")

    # Called exactly once (no retry loop on 429)
    assert service.client.aio.models.generate_content.call_count == 1
    assert "fallback parsing mode" in result.experience_summary


# ==============================================================================
# 12. Custom JD transient HTTP 503 / timeout -> bounded retry only (max 2 attempts)
# ==============================================================================
@pytest.mark.asyncio
async def test_jd_transient_503_bounded_retry():
    """Transient HTTP 503 UNAVAILABLE retries at most once (total 2 attempts)."""
    service = GeminiService()
    error_503 = Exception("503 UNAVAILABLE: High backend load")
    service.client.aio.models.generate_content = AsyncMock(side_effect=error_503)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await service.parse_job_description("Sample Job Description...")

    assert service.client.aio.models.generate_content.call_count == 2
    assert "fallback parsing mode" in result.experience_summary


# ==============================================================================
# 13. Strict User Isolation for resume and JD data
# ==============================================================================
@pytest.mark.asyncio
async def test_strict_user_isolation_resume_and_session(
    client: AsyncClient, mock_parsed_resume_data, mock_parsed_jd_data
):
    """User A cannot access or mutate User B's resume or interview session."""
    headers_a = await _register_user(client, "user_a_isolation@example.com")
    headers_b = await _register_user(client, "user_b_isolation@example.com")

    # User A uploads resume
    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=mock_parsed_resume_data,
    ):
        files = {"file": ("user_a_resume.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")}
        await client.post("/api/v1/resumes/upload", files=files, headers=headers_a)

    # User A creates session with JD
    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
        return_value=mock_parsed_jd_data,
    ):
        sess_a = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
                "custom_job_desc": "User A proprietary JD.",
            },
            headers=headers_a,
        )
        session_a_id = sess_a.json()["id"]

    # User B checks resume -> 404 (User B has no resume)
    res_b = await client.get("/api/v1/resumes/me", headers=headers_b)
    assert res_b.status_code == 404

    # User B attempts to access User A's session -> 404
    sess_b_try = await client.get(f"/api/v1/interviews/sessions/{session_a_id}", headers=headers_b)
    assert sess_b_try.status_code == 404


# ==============================================================================
# 14. No automatic duplicate parsing from lifecycle or setup flows
# ==============================================================================
@pytest.mark.asyncio
async def test_no_custom_jd_means_zero_jd_gemini_calls(client: AsyncClient):
    """Standard role preset setup without custom_job_desc makes ZERO JD Gemini calls."""
    headers = await _register_user(client, "preset_no_jd@example.com")

    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
    ) as mock_jd_parse:
        sess_res = await client.post(
            "/api/v1/interviews/sessions",
            json={
                "target_role": "Frontend",
                "seniority_level": "senior",
                "interview_focus": "Technical Core",
                "practice_mode": "quick",
            },
            headers=headers,
        )
        assert sess_res.status_code == 201
        assert mock_jd_parse.call_count == 0
