"""Integration tests for Interview Setup, Session Lifecycle, and Concurrency Rules."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.resume import ParsedResumeData
from app.services.gemini_service import ParsedJobDescription
from tests.test_resume_upload import create_sample_docx


@pytest.mark.asyncio
async def test_unauthenticated_interview_endpoints_fail(client: AsyncClient):
    """Verify session endpoints reject unauthenticated requests with HTTP 401."""
    # Presets is public
    res_presets = await client.get("/api/v1/interviews/presets")
    assert res_presets.status_code == 200

    # Protected endpoints
    res_create = await client.post(
        "/api/v1/interviews/sessions",
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
        },
    )
    assert res_create.status_code == 401

    res_active = await client.get("/api/v1/interviews/sessions/active")
    assert res_active.status_code == 401

    res_get = await client.get("/api/v1/interviews/sessions/some-id")
    assert res_get.status_code == 401

    res_abandon = await client.post("/api/v1/interviews/sessions/some-id/abandon")
    assert res_abandon.status_code == 401


@pytest.mark.asyncio
async def test_create_standard_full_and_quick_practice_sessions(client: AsyncClient):
    """Test creating full (6 core / 9 turns) and quick (3 core / 5 turns) interview sessions."""
    # 1. Register candidate
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "interviewuser@example.com",
            "password": "StrongPassword!123",
            "full_name": "Interview User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock JD Gemini parser
    mock_parsed_jd = ParsedJobDescription(
        job_title="Senior Backend Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        core_responsibilities=["Scale APIs"],
        key_technologies=["AWS", "Docker"],
        experience_summary="Mid-to-senior backend role.",
    )

    with patch(
        "app.services.gemini_service.GeminiService.parse_job_description",
        new_callable=AsyncMock,
        return_value=mock_parsed_jd,
    ):
        # 3. Create Full Mock Interview Session
        create_res = await client.post(
            "/api/v1/interviews/sessions",
            headers=headers,
            json={
                "target_role": "Backend Engineer",
                "seniority_level": "mid",
                "interview_focus": "Technical Core",
                "practice_mode": "full",
                "custom_job_desc": "Looking for a Python Backend Engineer.",
                "focus_skills": ["Python", "FastAPI", "Docker"],
            },
        )
        assert create_res.status_code == 201
        session_data = create_res.json()
        assert session_data["target_role"] == "Backend Engineer"
        assert session_data["seniority_level"] == "mid"
        assert session_data["interview_focus"] == "Technical Core"
        assert session_data["practice_mode"] == "full"
        assert session_data["planned_core_questions"] == 6
        assert session_data["max_total_turns"] == 9
        assert session_data["current_turn_index"] == 0
        assert session_data["status"] == "in_progress"
        assert session_data["focus_skills"] == ["Python", "FastAPI", "Docker"]
        session_id = session_data["id"]

        # 4. GET /sessions/active returns the active session
        active_res = await client.get("/api/v1/interviews/sessions/active", headers=headers)
        assert active_res.status_code == 200
        assert active_res.json()["id"] == session_id

        # 5. GET /sessions/{id} returns details
        get_res = await client.get(f"/api/v1/interviews/sessions/{session_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == session_id

        # 6. Attempting to create a second session while first is active raises 409 Conflict
        second_create = await client.post(
            "/api/v1/interviews/sessions",
            headers=headers,
            json={
                "target_role": "Frontend Engineer",
                "seniority_level": "junior",
                "interview_focus": "Behavioral",
            },
        )
        assert second_create.status_code == 409
        err_json = second_create.json()
        assert err_json["error_code"] == "ACTIVE_SESSION_EXISTS"
        assert err_json["details"]["active_session_id"] == session_id

        # 7. Abandon the active session
        abandon_res = await client.post(
            f"/api/v1/interviews/sessions/{session_id}/abandon", headers=headers
        )
        assert abandon_res.status_code == 200
        assert abandon_res.json()["status"] == "abandoned"
        assert abandon_res.json()["completed_at"] is not None

        # 8. GET /sessions/active now returns 404
        active_res_after = await client.get("/api/v1/interviews/sessions/active", headers=headers)
        assert active_res_after.status_code == 404

        # 9. Create Quick Practice Session now that previous is abandoned
        quick_res = await client.post(
            "/api/v1/interviews/sessions",
            headers=headers,
            json={
                "target_role": "Machine Learning Engineer",
                "seniority_level": "senior",
                "interview_focus": "System Design",
                "practice_mode": "quick",
            },
        )
        assert quick_res.status_code == 201
        quick_data = quick_res.json()
        assert quick_data["practice_mode"] == "quick"
        assert quick_data["planned_core_questions"] == 3
        assert quick_data["max_total_turns"] == 5
        # Since no focus_skills passed, preset default skills are populated
        assert len(quick_data["focus_skills"]) > 0
        assert "PyTorch" in quick_data["focus_skills"]


@pytest.mark.asyncio
async def test_resume_association_and_set_null_on_delete(client: AsyncClient):
    """Test that interview session links to active resume and retains session when resume is deleted."""
    # 1. Register candidate
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "resumeassoc@example.com",
            "password": "StrongPassword!123",
            "full_name": "Resume Assoc User",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload resume with sufficient text (>50 chars)
    mock_resume_data = ParsedResumeData(
        skills=["Python", "SQL", "Docker"],
        experience_years=3.0,
        domains=["Backend"],
        education=[],
        summary="Backend developer with Python experience.",
    )
    docx_bytes = create_sample_docx(
        "Candidate Resume - Senior Software Engineer with deep expertise in Python, SQL, Docker, and distributed microservices architecture."
    )

    with patch(
        "app.services.gemini_service.GeminiService.parse_resume",
        new_callable=AsyncMock,
        return_value=mock_resume_data,
    ):
        upload_res = await client.post(
            "/api/v1/resumes/upload",
            headers=headers,
            files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert upload_res.status_code == 201
        resume_id = upload_res.json()["resume"]["id"]

    # 3. Create interview session (should link resume_id automatically)
    session_res = await client.post(
        "/api/v1/interviews/sessions",
        headers=headers,
        json={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
        },
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    assert session_data["resume_id"] == resume_id
    session_id = session_data["id"]

    # 4. Delete the resume
    del_res = await client.delete("/api/v1/resumes/me", headers=headers)
    assert del_res.status_code == 200

    # 5. Fetch the interview session: session still exists, but resume_id is SET NULL
    get_res = await client.get(f"/api/v1/interviews/sessions/{session_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["resume_id"] is None
    assert get_res.json()["status"] == "in_progress"
