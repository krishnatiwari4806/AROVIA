"""Unit tests for Interview Presets Catalog and Pydantic DTOs."""

import pytest
from pydantic import ValidationError

from app.schemas.interview import (
    InterviewFocus,
    InterviewSessionCreateRequest,
    PracticeMode,
    SeniorityLevel,
)
from app.services.interview_presets import (
    PACING_GUIDELINES,
    ROLE_PRESETS,
    get_presets_catalog,
)


def test_get_presets_catalog_structure():
    """Verify presets catalog returns all 7 standard role presets and pacing rules."""
    catalog = get_presets_catalog()

    assert len(catalog.roles) == 7
    role_ids = [r.role_id for r in catalog.roles]
    assert "backend-engineer" in role_ids
    assert "frontend-engineer" in role_ids
    assert "fullstack-engineer" in role_ids
    assert "devops-cloud-engineer" in role_ids
    assert "data-engineer" in role_ids
    assert "ml-engineer" in role_ids
    assert "mobile-engineer" in role_ids

    # Verify default skills exist for each role
    for role in catalog.roles:
        assert len(role.default_skills) >= 4
        assert len(role.recommended_seniority) >= 1

    # Verify seniority levels
    seniority_ids = [s["id"] for s in catalog.seniority_levels]
    assert set(seniority_ids) == {"junior", "mid", "senior"}

    # Verify focus areas
    focus_ids = [f["id"] for f in catalog.focus_areas]
    assert set(focus_ids) == {"Technical Core", "System Design", "Behavioral"}

    # Verify practice modes
    mode_ids = [m["id"] for m in catalog.practice_modes]
    assert set(mode_ids) == {"full", "quick"}

    # Verify pacing guidelines
    assert catalog.pacing_guidelines["Technical Core"] == 120
    assert catalog.pacing_guidelines["Behavioral"] == 120
    assert catalog.pacing_guidelines["System Design"] == 180


def test_interview_session_create_request_validation():
    """Verify Pydantic validation on InterviewSessionCreateRequest."""
    # Valid standard request
    valid_req = InterviewSessionCreateRequest(
        target_role="Backend Engineer",
        seniority_level=SeniorityLevel.mid,
        interview_focus=InterviewFocus.technical_core,
        practice_mode=PracticeMode.full,
        custom_job_desc="Looking for a Python and FastAPI engineer.",
        focus_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    assert valid_req.target_role == "Backend Engineer"
    assert valid_req.seniority_level == SeniorityLevel.mid
    assert valid_req.interview_focus == InterviewFocus.technical_core
    assert valid_req.practice_mode == PracticeMode.full

    # Valid custom role request
    custom_req = InterviewSessionCreateRequest(
        target_role="Security Architect",
        seniority_level=SeniorityLevel.senior,
        interview_focus=InterviewFocus.system_design,
        practice_mode=PracticeMode.quick,
    )
    assert custom_req.target_role == "Security Architect"
    assert custom_req.practice_mode == PracticeMode.quick

    # Invalid empty target_role
    with pytest.raises(ValidationError):
        InterviewSessionCreateRequest(
            target_role="A",  # Less than min_length 2
            seniority_level=SeniorityLevel.junior,
            interview_focus=InterviewFocus.technical_core,
        )

    # Invalid job description exceeding 10,000 chars
    with pytest.raises(ValidationError):
        InterviewSessionCreateRequest(
            target_role="Backend Engineer",
            seniority_level=SeniorityLevel.mid,
            interview_focus=InterviewFocus.technical_core,
            custom_job_desc="X" * 10001,
        )
