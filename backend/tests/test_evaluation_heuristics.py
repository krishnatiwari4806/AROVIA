"""Unit tests for local NLP filler-word heuristics (₹0 Zero Cost)."""

import pytest
from app.services.evaluation_heuristics import analyze_speech_confidence


def test_analyze_speech_confidence_clean_answer():
    """Verify clean response with zero filler words yields maximum confidence score."""
    clean_text = (
        "In our microservices architecture, we utilized PostgreSQL with read replicas "
        "and Redis caching to handle high traffic spikes. We implemented connection pooling "
        "and database indexes on foreign keys to maintain sub-50ms latency."
    )
    result = analyze_speech_confidence(clean_text)

    assert result["filler_count"] == 0
    assert result["filler_density"] == 0.0
    assert result["heuristic_confidence_score"] == 100
    assert len(result["detected_fillers"]) == 0
    assert result["total_words"] > 20


def test_analyze_speech_confidence_filler_heavy_answer():
    """Verify answer with multiple hesitation and filler markers receives score penalty."""
    hesitant_text = (
        "Um, so basically like, I think maybe we sort of used Redis, or uh, you know, "
        "some kind of cache, but I'm probably not sure about the exact replication setup."
    )
    result = analyze_speech_confidence(hesitant_text)

    assert result["filler_count"] >= 5
    assert result["filler_density"] > 10.0
    assert result["heuristic_confidence_score"] < 50
    assert "um" in result["detected_fillers"]
    assert "like" in result["detected_fillers"]
    assert "basically" in result["detected_fillers"]


def test_analyze_speech_confidence_empty_or_whitespace():
    """Verify empty or whitespace strings return baseline neutral score without crashing."""
    result_empty = analyze_speech_confidence("")
    assert result_empty["filler_count"] == 0
    assert result_empty["heuristic_confidence_score"] == 50

    result_whitespace = analyze_speech_confidence("   \n\t  ")
    assert result_whitespace["filler_count"] == 0
    assert result_whitespace["heuristic_confidence_score"] == 50


def test_analyze_speech_confidence_score_clamping():
    """Verify heuristic score is strictly clamped between 0 and 100."""
    extreme_filler = "um uh er ah like you know sort of kind of basically actually um uh"
    result = analyze_speech_confidence(extreme_filler)
    assert 0 <= result["heuristic_confidence_score"] <= 100
    assert result["heuristic_confidence_score"] == 0
