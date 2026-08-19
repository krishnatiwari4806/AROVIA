"""Unit tests for Gemini session evaluation service and structured response schemas."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.schemas.evaluation import SessionEvaluationReport
from app.services.gemini_service import GeminiService, _build_fallback_evaluation_report


@pytest.mark.asyncio
async def test_evaluate_interview_session_mocked_success():
    """Verify evaluate_interview_session correctly parses structured Gemini JSON response."""
    mock_report_data = {
        "turns_evaluation": [
            {
                "turn_index": 0,
                "relevance_score": 90,
                "correctness_score": 85,
                "keywords_score": 88,
                "clarity_score": 92,
                "confidence_score": 85,
                "covered_concepts": ["FastAPI Async", "PostgreSQL Connection Pooling"],
                "missed_concepts": ["Read Replica Failover"],
                "ideal_answer_comparison": "Candidate provided great practical context with slight omission of failover mechanics.",
                "turn_feedback": "Strong architectural foundation; expand on disaster recovery.",
            }
        ],
        "top_strengths": [
            {
                "title": "Clear Async Patterns",
                "description": "Demonstrated solid understanding of Python async ASGI architecture.",
                "evidence_turn_index": 0,
            }
        ],
        "top_improvements": [
            {
                "title": "High Availability Trade-offs",
                "description": "Lacked discussion of automated failover in database replication.",
                "actionable_recommendation": "Study Patroni or AWS RDS Multi-AZ failover patterns.",
                "evidence_turn_index": 0,
            }
        ],
        "executive_summary": "Candidate demonstrated strong mid-to-senior level backend proficiency with clear communication.",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_report_data)

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    service = GeminiService(api_key="test-key")
    with patch.object(service, "_client", mock_client):
        report = await service.evaluate_interview_session(
            target_role="Backend Engineer",
            seniority_level="mid",
            interview_focus="Technical Core",
            focus_skills=["FastAPI", "PostgreSQL"],
            transcript_turns=[
                {
                    "turn_index": 0,
                    "question_text": "How do you optimize FastAPI with PostgreSQL?",
                    "candidate_answer": "We used asyncpg and connection pooling.",
                    "ideal_answer": "Benchmark answer covering asyncpg, connection pooling, and replication.",
                }
            ],
        )

        assert isinstance(report, SessionEvaluationReport)
        assert len(report.turns_evaluation) == 1
        assert report.turns_evaluation[0].relevance_score == 90
        assert report.turns_evaluation[0].correctness_score == 85
        assert len(report.top_strengths) == 1
        assert len(report.top_improvements) == 1
        assert "Proficiency" in report.executive_summary or "proficiency" in report.executive_summary


def test_build_fallback_evaluation_report():
    """Verify fallback evaluation builder produces a complete, valid report."""
    transcript_turns = [
        {
            "turn_index": 0,
            "question_text": "Explain database indexing.",
            "candidate_answer": "Indexes use B-trees to speed up lookups.",
            "ideal_answer": "B-Tree, Hash, GIN indexes with trade-offs.",
        }
    ]

    report = _build_fallback_evaluation_report(
        transcript_turns=transcript_turns,
        target_role="Backend Engineer",
        seniority_level="senior",
    )

    assert isinstance(report, SessionEvaluationReport)
    assert len(report.turns_evaluation) == 1
    assert 0 <= report.turns_evaluation[0].relevance_score <= 100
    assert len(report.top_strengths) >= 2
    assert len(report.top_improvements) >= 2
    assert "Backend Engineer" in report.executive_summary
