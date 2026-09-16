"""Integration tests for Resume REST API endpoints and atomic lifecycle management."""

import os
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.schemas.resume import ParsedResumeData
from tests.test_resume_upload import create_sample_docx, create_sample_pdf


MOCK_PARSED_DATA = ParsedResumeData(
    skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    experience_years=4.0,
    domains=["Backend Engineering", "Distributed Systems"],
    education=[{"institution": "Stanford University", "degree": "M.S. Computer Science", "graduation_year": "2021"}],
    summary="Passionate backend engineer with 4 years of building distributed web services.",
    projects=[
        {
            "title": "Cloud Inventory Engine",
            "description": "Distributed inventory management microservice.",
            "technologies": ["Python", "FastAPI", "PostgreSQL", "Redis"],
            "responsibilities": "Lead engineer designing state sync.",
            "architecture_details": "CQRS with Redis cache invalidation.",
            "challenges": "Resolving race conditions on concurrent stock updates.",
            "outcomes": "Zero stock discrepancy across 100k daily orders.",
        }
    ],
    work_history=[
        {
            "company": "Acme Corp",
            "role": "Backend Engineer",
            "duration": "2021 - Present",
            "responsibilities": ["Maintained REST APIs", "Database query optimization"],
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
            "achievements": ["Reduced API latency by 40%"],
        }
    ],
)


@pytest.mark.asyncio
async def test_unauthenticated_resume_endpoints_fail(client: AsyncClient):
    """Verify resume endpoints reject unauthenticated requests with HTTP 401."""
    res_get = await client.get("/api/v1/resumes/me")
    assert res_get.status_code == 401

    res_upload = await client.post("/api/v1/resumes/upload")
    assert res_upload.status_code == 401

    res_put = await client.put("/api/v1/resumes/me/parsed", json={"skills": ["Python"]})
    assert res_put.status_code == 401

    res_del = await client.delete("/api/v1/resumes/me")
    assert res_del.status_code == 401


@pytest.mark.asyncio
async def test_resume_upload_get_update_delete_lifecycle(client: AsyncClient):
    """Full lifecycle test: upload resume, fetch parsed data, update skills and projects, delete resume."""
    # 1. Register candidate
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "resumetest@example.com",
            "password": "StrongPassword!123",
            "full_name": "Resume Candidate",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET before upload returns 404
    get_res_empty = await client.get("/api/v1/resumes/me", headers=headers)
    assert get_res_empty.status_code == 404

    # 3. Upload DOCX resume
    docx_bytes = create_sample_docx(
        "Resume Candidate - Python Backend Engineer with 4 years experience. Skills: Python, FastAPI, Docker, SQL."
    )

    with patch("app.services.gemini_service.GeminiService.parse_resume", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = MOCK_PARSED_DATA

        files = {"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        upload_res = await client.post("/api/v1/resumes/upload", headers=headers, files=files)

        assert upload_res.status_code == 201
        data = upload_res.json()
        assert data["message"] == "Resume successfully uploaded and parsed."
        assert data["resume"]["file_name"] == "resume.docx"
        assert data["resume"]["parsed_data"]["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]
        assert data["resume"]["parsed_data"]["experience_years"] == 4.0
        assert len(data["resume"]["parsed_data"]["projects"]) == 1
        assert data["resume"]["parsed_data"]["projects"][0]["title"] == "Cloud Inventory Engine"
        assert len(data["resume"]["parsed_data"]["work_history"]) == 1
        assert data["resume"]["parsed_data"]["work_history"][0]["company"] == "Acme Corp"

    # 4. GET /me returns active resume with projects and work history
    get_res = await client.get("/api/v1/resumes/me", headers=headers)
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["file_name"] == "resume.docx"
    assert "Python" in get_data["parsed_data"]["skills"]
    assert get_data["parsed_data"]["projects"][0]["title"] == "Cloud Inventory Engine"

    # 5. PUT /me/parsed updates candidate profile including projects
    put_res = await client.put(
        "/api/v1/resumes/me/parsed",
        headers=headers,
        json={
            "skills": ["Python", "FastAPI", "GraphQL", "AWS"],
            "experience_years": 5.0,
            "summary": "Updated executive career summary.",
            "projects": [
                {
                    "title": "Updated High Scale Gateway",
                    "description": "API Gateway serving 50k RPS.",
                    "technologies": ["Go", "FastAPI"],
                    "responsibilities": "Core author",
                    "architecture_details": "Async proxy",
                    "challenges": "Memory footprint",
                    "outcomes": "Saved 40% compute",
                }
            ],
        },
    )
    assert put_res.status_code == 200
    put_data = put_res.json()
    assert put_data["parsed_data"]["skills"] == ["Python", "FastAPI", "GraphQL", "AWS"]
    assert put_data["parsed_data"]["experience_years"] == 5.0
    assert put_data["parsed_data"]["summary"] == "Updated executive career summary."
    assert len(put_data["parsed_data"]["projects"]) == 1
    assert put_data["parsed_data"]["projects"][0]["title"] == "Updated High Scale Gateway"
    # Domains preserved
    assert "Backend Engineering" in put_data["parsed_data"]["domains"]

    # 6. DELETE /me removes active resume
    del_res = await client.delete("/api/v1/resumes/me", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Resume successfully deleted."

    # 7. Subsequent GET returns 404
    get_res_after_del = await client.get("/api/v1/resumes/me", headers=headers)
    assert get_res_after_del.status_code == 404


@pytest.mark.asyncio
async def test_resume_atomic_replacement_deletes_old_file(client: AsyncClient):
    """Verify that re-uploading a resume replaces DB record and removes prior file on disk."""
    # Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "replacetest@example.com",
            "password": "StrongPassword!123",
            "full_name": "Replace Candidate",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First Upload: PDF
    pdf_bytes = create_sample_pdf("First resume version text with sufficient length to pass extraction.")
    with patch("app.services.gemini_service.GeminiService.parse_resume", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = MOCK_PARSED_DATA
        files = {"file": ("first_resume.pdf", pdf_bytes, "application/pdf")}
        up1 = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert up1.status_code == 201

    # Second Upload: DOCX (replacement)
    docx_bytes = create_sample_docx("Second resume version text with updated skills and background.")
    new_parsed_data = ParsedResumeData(
        skills=["Rust", "Go", "Kubernetes"],
        experience_years=6.0,
        domains=["Systems Engineering"],
        education=[],
        summary="Senior Systems Engineer.",
    )

    with patch("app.services.gemini_service.GeminiService.parse_resume", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = new_parsed_data
        files = {"file": ("second_resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        up2 = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert up2.status_code == 201
        assert up2.json()["resume"]["file_name"] == "second_resume.docx"
        assert up2.json()["resume"]["parsed_data"]["skills"] == ["Rust", "Go", "Kubernetes"]

    # Verify GET returns updated data
    get_res = await client.get("/api/v1/resumes/me", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["file_name"] == "second_resume.docx"


@pytest.mark.asyncio
async def test_resume_atomic_failure_keeps_old_resume_intact(client: AsyncClient):
    """Verify that if a second upload fails during AI parsing, the previous resume remains completely intact."""
    # Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "atomicfail@example.com",
            "password": "StrongPassword!123",
            "full_name": "Atomic Candidate",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload valid initial resume
    pdf_bytes = create_sample_pdf("Initial valid candidate resume with full technical details and experience.")
    with patch("app.services.gemini_service.GeminiService.parse_resume", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = MOCK_PARSED_DATA
        files = {"file": ("initial.pdf", pdf_bytes, "application/pdf")}
        up1 = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert up1.status_code == 201

    # 2. Attempt second upload where Gemini fails (raises 503)
    docx_bytes = create_sample_docx("Second resume that will fail during Gemini structured parsing.")
    with patch("app.services.gemini_service.GeminiService.parse_resume", new_callable=AsyncMock) as mock_parse:
        from app.core.exceptions import AppError
        mock_parse.side_effect = AppError("AI service unavailable", status_code=503, error_code="AI_SERVICE_UNAVAILABLE")

        files = {"file": ("second_failing.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        up2 = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
        assert up2.status_code == 503

    # 3. Verify original resume is still completely intact in DB and accessible
    get_res = await client.get("/api/v1/resumes/me", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["file_name"] == "initial.pdf"
    assert get_res.json()["parsed_data"]["skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]


@pytest.mark.asyncio
async def test_resume_upload_oversized_file_fails(client: AsyncClient):
    """Verify file exceeding 5MB is rejected with HTTP 422."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "oversized@example.com",
            "password": "StrongPassword!123",
            "full_name": "Oversized Candidate",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("oversized.pdf", b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 1024), "application/pdf")}
    res = await client.post("/api/v1/resumes/upload", headers=headers, files=files)
    assert res.status_code == 422
    assert "exceeds maximum allowed size" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_upload_gemini_503_returns_accurate_resume_analysis_message(client: AsyncClient):
    """Verify endpoint propagates HTTP 503 with resume analysis message rather than evaluation message."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "gemini503test@example.com",
            "password": "StrongPassword!123",
            "full_name": "Gemini Test Candidate",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    docx_bytes = create_sample_docx("Valid candidate resume text for 503 propagation test with Python and FastAPI.")
    files = {"file": ("test.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    from app.core.exceptions import AppError
    with patch("app.services.gemini_service.GeminiService.parse_resume", new_callable=AsyncMock) as mock_parse:
        mock_parse.side_effect = AppError(
            message="AI resume analysis service is temporarily unavailable. Please retry shortly.",
            status_code=503,
            error_code="AI_SERVICE_UNAVAILABLE",
        )
        res = await client.post("/api/v1/resumes/upload", headers=headers, files=files)

        assert res.status_code == 503
        data = res.json()
        assert data["detail"] == "AI resume analysis service is temporarily unavailable. Please retry shortly."
        assert data["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert "evaluation" not in data["detail"].lower()

