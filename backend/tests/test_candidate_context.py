"""Unit tests for Candidate Context Extraction, Skill Normalization, and Deterministic Matching (Phase 3)."""

import pytest

from app.services.candidate_context import (
    CandidateContext,
    build_candidate_context,
    compute_matched_and_missing_skills,
    normalize_skill,
)


def test_normalize_skill_standard_and_aliases():
    """Test skill normalization handles variations, punctuation, and aliases deterministically."""
    assert normalize_skill("PostgreSQL") == "postgresql"
    assert normalize_skill("postgres") == "postgresql"
    assert normalize_skill("PSQL") == "postgresql"
    assert normalize_skill("React.js") == "react"
    assert normalize_skill("ReactJS") == "react"
    assert normalize_skill("React") == "react"
    assert normalize_skill("Node.js") == "nodejs"
    assert normalize_skill("NodeJS") == "nodejs"
    assert normalize_skill("FastAPI") == "fastapi"
    assert normalize_skill("Python 3") == "python"
    assert normalize_skill("K8s") == "kubernetes"
    assert normalize_skill("Kubernetes") == "kubernetes"
    assert normalize_skill("Amazon Web Services") == "aws"
    assert normalize_skill("AWS") == "aws"


def test_compute_matched_and_missing_skills():
    """Test matched vs missing skills separation without overmatching or false positives."""
    resume_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"]
    jd_skills = ["Python", "PostgreSQL", "AWS", "Kubernetes", "Redis"]

    matched, missing = compute_matched_and_missing_skills(
        resume_skills=resume_skills, jd_skills=jd_skills
    )

    assert "Python" in matched
    assert "PostgreSQL" in matched
    assert "AWS" in missing
    assert "Kubernetes" in missing
    assert "Redis" in missing
    assert len(matched) == 2
    assert len(missing) == 3


def test_candidate_context_builder_with_resume_projects_and_work():
    """Test building CandidateContext extracts projects, work history, skills, and intro response."""
    resume_data = {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Next.js"],
        "experience_years": 3.5,
        "domains": ["Backend Systems", "Fullstack Development"],
        "education": [{"institution": "MIT", "degree": "BS CS", "graduation_year": "2021"}],
        "summary": "Fullstack backend engineer specializing in high-performance APIs.",
        "projects": [
            {
                "title": "Weather Analytics Hub",
                "description": "Real-time telemetry and weather prediction dashboard.",
                "technologies": ["Python", "FastAPI", "Next.js", "PostgreSQL"],
                "architecture_details": "Microservices with Redis caching and PostgreSQL time-series partitioning.",
                "responsibilities": "Architected backend API and data ingestion pipeline.",
                "challenges": "Handled high-volume sensor streams without dropping packets.",
            }
        ],
        "work_history": [
            {
                "company": "Acme Cloud Corp",
                "role": "Software Engineer II",
                "duration": "2021 - 2024",
                "responsibilities": ["Built RESTful microservices", "Optimized database queries"],
                "technologies": ["Python", "Docker", "PostgreSQL"],
                "achievements": ["Reduced API latency by 40%"],
            }
        ],
    }

    parsed_jd_data = {
        "job_title": "Senior Backend Engineer",
        "required_skills": ["Python", "FastAPI", "AWS", "Kafka"],
        "core_responsibilities": ["Design scalable microservices", "Own data pipelines"],
        "key_technologies": ["Python", "AWS"],
    }

    context = build_candidate_context(
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        preferred_language="en",
        resume_data=resume_data,
        parsed_jd_data=parsed_jd_data,
        introduction_response="I have 3+ years of experience building distributed backend systems in Python.",
    )

    assert context.has_resume is True
    assert context.has_jd is True
    assert len(context.projects) == 1
    assert context.projects[0].title == "Weather Analytics Hub"
    assert "Next.js" in context.projects[0].technologies
    assert len(context.work_history) == 1
    assert context.work_history[0].company == "Acme Cloud Corp"
    assert "Python" in context.matched_skills
    assert "FastAPI" in context.matched_skills
    assert "AWS" in context.missing_skills
    assert "Kafka" in context.missing_skills
    assert "Weather Analytics Hub" in context.format_candidate_summary()
    assert "Acme Cloud Corp" in context.format_candidate_summary()
    assert "AWS" in context.format_jd_summary()


def test_candidate_context_zero_hallucination_when_empty():
    """Test that missing resume or JD produces empty evidence and does NOT hallucinate facts."""
    context = build_candidate_context(
        target_role="Frontend Engineer",
        seniority_level="junior",
        interview_focus="Technical Core",
        preferred_language="en",
        resume_data=None,
        parsed_jd_data=None,
    )

    assert context.has_resume is False
    assert context.has_jd is False
    assert len(context.projects) == 0
    assert len(context.work_history) == 0
    assert len(context.skills) == 0
    assert len(context.matched_skills) == 0
    assert len(context.missing_skills) == 0
    assert "No uploaded resume" in context.format_candidate_summary()
    assert "No Job Description provided" in context.format_jd_summary()
