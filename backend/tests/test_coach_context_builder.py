"""Unit tests for CoachContextBuilder and CoachContextPayload prompt formatting and recurrence hardening."""

import pytest
from app.services.coach_context_builder import (
    CoachContextBuilder,
    CoachContextPayload,
    STABLE_DELTA_THRESHOLD,
    _classify_direction,
    _extract_filler_metrics,
    _format_delta,
    _truncate_text,
    aggregate_recurring_patterns,
    classify_pacing,
    get_canonical_topic,
    normalize_title,
)


def test_to_prompt_context_renders_all_concepts_and_five_scores():
    """Verify primary concept, covered concepts, missed concepts, and 5 scores are rendered."""
    payload = CoachContextPayload(
        candidate_name="Alex Mercer",
        current_session={
            "target_role": "Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "standard",
            "overall_score": 85,
            "dimension_scores": {
                "relevance": 90,
                "correctness": 85,
                "keywords": 80,
                "clarity": 88,
                "confidence": 82,
            },
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "Explain database indexing with B-Trees.",
                "candidate_answer": "B-Trees keep data sorted and allow search in O(log n).",
                "primary_concept": "Database Index Structures",
                "covered_concepts": ["B-Tree logarithmic search", "Sorted key order"],
                "missed_concepts": ["Write amplification trade-offs", "Clustered vs secondary index"],
                "relevance_score": 92,
                "correctness_score": 88,
                "keywords_score": 84,
                "clarity_score": 90,
                "confidence_score": 86,
                "ideal_answer_comparison": "Strong foundational explanation with clear complexity metrics.",
                "turn_feedback": "Accurate search complexity analysis.",
            }
        ],
        evaluation_report={
            "executive_summary": "Strong systems design fundamentals.",
            "top_strengths": [
                {"title": "Search Complexity", "description": "Clear grasp of logarithmic bounds."}
            ],
            "top_improvements": [
                {
                    "title": "Index Trade-offs",
                    "description": "Discuss write overhead.",
                    "actionable_recommendation": "Review B-Tree page splits and WAL implications.",
                }
            ],
        },
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # a) covered_concepts appear in rendered prompt
    assert "Covered Concepts: B-Tree logarithmic search, Sorted key order" in prompt

    # b) missed_concepts appear in rendered prompt
    assert "Missed Concepts: Write amplification trade-offs, Clustered vs secondary index" in prompt

    # c) primary_concept appears when available
    assert "Primary Concept: Database Index Structures" in prompt

    # d) all five per-turn dimension scores appear
    assert "Scores: [Relevance: 92/100, Correctness: 88/100, Keywords: 84/100, Clarity: 90/100, Confidence: 86/100]" in prompt

    # f) existing transcript question/answer and evaluator feedback remain present
    assert "Question: Explain database indexing with B-Trees." in prompt
    assert "Candidate Answer: B-Trees keep data sorted and allow search in O(log n)." in prompt
    assert "Benchmark Comparison: Strong foundational explanation with clear complexity metrics." in prompt
    assert "Evaluator Feedback: Accurate search complexity analysis." in prompt


def test_to_prompt_context_safe_handling_of_empty_and_none_fields():
    """Verify empty/None concepts and missing optional fields do not crash context rendering."""
    payload = CoachContextPayload(
        candidate_name="Jane Doe",
        current_session={
            "target_role": "Frontend Developer",
            "seniority_level": "mid",
            "interview_focus": "React",
            "practice_mode": "quick",
            "overall_score": None,
            "dimension_scores": None,
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "What is the Virtual DOM?",
                "candidate_answer": None,
                "primary_concept": None,
                "covered_concepts": [],
                "missed_concepts": [],
                "relevance_score": None,
                "correctness_score": None,
                "keywords_score": None,
                "clarity_score": None,
                "confidence_score": None,
                "ideal_answer_comparison": None,
                "turn_feedback": None,
            }
        ],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # e) missing optional fields do not crash rendering and empty arrays render as 'None recorded'
    assert "Covered Concepts: None recorded" in prompt
    assert "Missed Concepts: None recorded" in prompt
    assert "Candidate Answer: (No answer recorded)" in prompt
    assert "Primary Concept:" not in prompt
    assert "Scores:" not in prompt


def test_to_prompt_context_multi_turn_ordering_and_partial_scores():
    """Verify multiple turns maintain chronological ordering and partial score formatting works."""
    payload = CoachContextPayload(
        candidate_name="Bob Smith",
        current_session={
            "target_role": "DevOps Engineer",
            "seniority_level": "senior",
            "interview_focus": "Kubernetes",
            "practice_mode": "quick",
            "overall_score": 78,
            "dimension_scores": {"correctness": 78},
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "What is a Kubernetes Pod?",
                "candidate_answer": "The smallest deployable unit in K8s.",
                "primary_concept": "K8s Architecture",
                "covered_concepts": ["Container wrapper", "Shared network namespace"],
                "missed_concepts": ["Volume lifecycle"],
                "relevance_score": 90,
                "correctness_score": 85,
                "keywords_score": None,
                "clarity_score": 80,
                "confidence_score": None,
            },
            {
                "turn_index": 1,
                "question_text": "How do Services handle load balancing?",
                "candidate_answer": "Via iptables or IPVS routing to endpoints.",
                "primary_concept": "K8s Networking",
                "covered_concepts": ["kube-proxy", "iptables/IPVS"],
                "missed_concepts": ["Headless service DNS resolution"],
                "relevance_score": 95,
                "correctness_score": 90,
                "keywords_score": 88,
                "clarity_score": 92,
                "confidence_score": 89,
            },
        ],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # Verify chronological turn ordering
    turn1_pos = prompt.find("[Turn 1]")
    turn2_pos = prompt.find("[Turn 2]")
    assert turn1_pos != -1 and turn2_pos != -1
    assert turn1_pos < turn2_pos

    # Turn 1 partial scores
    assert "Scores: [Relevance: 90/100, Correctness: 85/100, Clarity: 80/100]" in prompt

    # Turn 2 full scores
    assert "Scores: [Relevance: 95/100, Correctness: 90/100, Keywords: 88/100, Clarity: 92/100, Confidence: 89/100]" in prompt


def test_historical_sessions_with_complete_dimensions_and_improving_trend():
    """Verify historical sessions render with dimensions and calculate Improving trends (55 -> 68 -> 76 = +21)."""
    payload = CoachContextPayload(
        candidate_name="Taylor Swift",
        current_session={
            "target_role": "Python Backend Engineer",
            "seniority_level": "senior",
            "interview_focus": "Distributed Systems",
            "practice_mode": "standard",
            "overall_score": 76,
            "dimension_scores": {
                "relevance": 78,
                "correctness": 74,
                "keywords": 69,
                "clarity": 81,
                "confidence": 78,
            },
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[
            {
                "id": "sess-hist-1",
                "target_role": "Python Backend Engineer",
                "overall_score": 55,
                "dimension_scores": {
                    "relevance": 60,
                    "correctness": 48,
                    "keywords": 52,
                    "clarity": 70,
                    "confidence": 55,
                },
                "date": "2026-09-10",
            },
            {
                "id": "sess-hist-2",
                "target_role": "Python Backend Engineer",
                "overall_score": 68,
                "dimension_scores": {
                    "relevance": 70,
                    "correctness": 61,
                    "keywords": 64,
                    "clarity": 72,
                    "confidence": 63,
                },
                "date": "2026-09-11",
            },
        ],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # Verify historical session representation with dimensions
    assert "- Past Session (2026-09-10): Python Backend Engineer" in prompt
    assert "Overall: 55/100" in prompt
    assert "Dimensions: Relevance 60, Correctness 48, Keywords 52, Clarity 70, Confidence 55" in prompt

    assert "- Past Session (2026-09-11): Python Backend Engineer" in prompt
    assert "Overall: 68/100" in prompt
    assert "Dimensions: Relevance 70, Correctness 61, Keywords 64, Clarity 72, Confidence 63" in prompt

    # Verify overall trend calculation: 55 -> 68 -> 76 (+21 points, Improving)
    assert "Overall Score Trend:" in prompt
    assert "55 → 68 → 76" in prompt
    assert "Net Change: +21 points" in prompt
    assert "Direction: Improving" in prompt

    # Verify dimension trend calculations
    assert "- Relevance: 60 → 70 → 78 (+18, Improving)" in prompt
    assert "- Correctness: 48 → 61 → 74 (+26, Improving)" in prompt
    assert "- Keywords: 52 → 64 → 69 (+17, Improving)" in prompt
    assert "- Clarity: 70 → 72 → 81 (+11, Improving)" in prompt
    assert "- Confidence: 55 → 63 → 78 (+23, Improving)" in prompt


def test_declining_overall_and_dimension_trends():
    """Verify declining trend is properly detected when score decreases (85 -> 75 -> 65 = -20)."""
    payload = CoachContextPayload(
        candidate_name="Charlie Brown",
        current_session={
            "target_role": "Fullstack Engineer",
            "seniority_level": "senior",
            "interview_focus": "System Design",
            "practice_mode": "standard",
            "overall_score": 65,
            "dimension_scores": {
                "relevance": 70,
                "correctness": 65,
                "keywords": 60,
                "clarity": 68,
                "confidence": 62,
            },
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[
            {
                "id": "h1",
                "target_role": "Fullstack Engineer",
                "overall_score": 85,
                "dimension_scores": {
                    "relevance": 90,
                    "correctness": 85,
                    "keywords": 80,
                    "clarity": 88,
                    "confidence": 82,
                },
                "date": "2026-09-01",
            },
            {
                "id": "h2",
                "target_role": "Fullstack Engineer",
                "overall_score": 75,
                "dimension_scores": {
                    "relevance": 80,
                    "correctness": 75,
                    "keywords": 70,
                    "clarity": 78,
                    "confidence": 72,
                },
                "date": "2026-09-05",
            },
        ],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    assert "85 → 75 → 65" in prompt
    assert "Net Change: -20 points" in prompt
    assert "Direction: Declining" in prompt
    assert "- Relevance: 90 → 80 → 70 (-20, Declining)" in prompt
    assert "- Correctness: 85 → 75 → 65 (-20, Declining)" in prompt


def test_stable_trend_within_deterministic_threshold():
    """Verify net score delta within threshold [-2, +2] classifies as Stable."""
    assert STABLE_DELTA_THRESHOLD == 2
    assert _classify_direction(2) == "Stable"
    assert _classify_direction(0) == "Stable"
    assert _classify_direction(-2) == "Stable"
    assert _classify_direction(3) == "Improving"
    assert _classify_direction(-3) == "Declining"

    payload = CoachContextPayload(
        candidate_name="Sam Altman",
        current_session={
            "target_role": "AI Engineer",
            "seniority_level": "senior",
            "interview_focus": "ML Architecture",
            "practice_mode": "standard",
            "overall_score": 76,
            "dimension_scores": {
                "relevance": 77,
                "correctness": 73,
                "keywords": 75,
                "clarity": 74,
                "confidence": 78,
            },
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[
            {
                "id": "h1",
                "target_role": "AI Engineer",
                "overall_score": 75,
                "dimension_scores": {
                    "relevance": 75,
                    "correctness": 75,
                    "keywords": 75,
                    "clarity": 75,
                    "confidence": 75,
                },
                "date": "2026-09-01",
            },
        ],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    assert "75 → 76" in prompt
    assert "Net Change: +1 points" in prompt
    assert "Direction: Stable" in prompt

    # Relevance (+2) -> Stable
    assert "- Relevance: 75 → 77 (+2, Stable)" in prompt
    # Correctness (-2) -> Stable
    assert "- Correctness: 75 → 73 (-2, Stable)" in prompt
    # Keywords (0) -> Stable
    assert "- Keywords: 75 → 75 (0, Stable)" in prompt
    # Confidence (+3) -> Improving
    assert "- Confidence: 75 → 78 (+3, Improving)" in prompt


def test_single_valid_observation_insufficient_data():
    """Verify single observation yields Insufficient historical data without crashing."""
    payload = CoachContextPayload(
        candidate_name="Solo Learner",
        current_session={
            "target_role": "Software Engineer",
            "seniority_level": "entry",
            "interview_focus": "Python",
            "practice_mode": "quick",
            "overall_score": 80,
            "dimension_scores": {"relevance": 80},
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    assert "Historical Performance: This is the candidate's first recorded interview session in AROVIA." in prompt
    assert "Overall Score Trend: Insufficient historical data." in prompt
    assert "Dimension Trends:" not in prompt


def test_missing_and_partial_dimension_scores_safe_rendering():
    """Verify missing/malformed dimension dictionaries and partial dimensions are handled safely."""
    payload = CoachContextPayload(
        candidate_name="Resilience Tester",
        current_session={
            "target_role": "Security Engineer",
            "seniority_level": "senior",
            "interview_focus": "AppSec",
            "practice_mode": "quick",
            "overall_score": 75,
            "dimension_scores": {
                "relevance": 75,
                "clarity": 82,
            },
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[
            {
                "id": "h1",
                "target_role": "Security Engineer",
                "overall_score": 60,
                "dimension_scores": None,
                "date": "2026-09-01",
            },
            {
                "id": "h2",
                "target_role": "Security Engineer",
                "overall_score": 70,
                "dimension_scores": {
                    "relevance": 70,
                    "clarity": 80,
                    "invalid_dim": "bad_value",
                    "confidence": -5,
                },
                "date": "2026-09-05",
            },
        ],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # Overall trend (60 -> 70 -> 75 = +15, Improving)
    assert "60 → 70 → 75" in prompt
    assert "Net Change: +15 points" in prompt
    assert "Direction: Improving" in prompt

    # Relevance has 2 valid points (70 in h2, 75 in current) -> Trend rendered
    assert "- Relevance: 70 → 75 (+5, Improving)" in prompt

    # Clarity has 2 valid points (80 in h2, 82 in current) -> Trend rendered
    assert "- Clarity: 80 → 82 (+2, Stable)" in prompt

    # Correctness, Keywords, Confidence have < 2 points -> Not rendered in dimension trends
    assert "- Correctness:" not in prompt
    assert "- Keywords:" not in prompt
    assert "- Confidence:" not in prompt


# =========================================================================
# STEP 10.3 RECURRING WEAKNESS & STRENGTH AGGREGATION TESTS
# =========================================================================

def test_recurrence_includes_current_session():
    """Requirement A: Past session + Current session aggregates to recurrence >= 2."""
    past_report = {
        "top_improvements": [{"title": "Database Indexing", "description": "Need B-Tree depth."}],
    }
    current_report = {
        "top_improvements": [{"title": "Database Indexing", "description": "Missed index scans."}],
    }

    weaknesses, strengths = aggregate_recurring_patterns([past_report, current_report])
    assert len(weaknesses) == 1
    assert "Database Indexing (2 sessions)" in weaknesses
    assert len(strengths) == 0


def test_recurrence_duplicate_within_single_session_counts_once():
    """Requirement B: Exact duplicate titles within one session report count only once."""
    report_with_dupes = {
        "top_improvements": [
            {"title": "Database Indexing"},
            {"title": "Database Indexing"},
        ],
    }
    weaknesses, _ = aggregate_recurring_patterns([report_with_dupes])
    # Count is 1, so threshold >= 2 is not met
    assert len(weaknesses) == 0


def test_recurrence_normalizes_case_whitespace_and_punctuation():
    """Requirement C: Case, repeated spaces, and punctuation variations aggregate."""
    report1 = {"top_improvements": [{"title": "Database Indexing"}]}
    report2 = {"top_improvements": [{"title": "  database   indexing:  "}]}

    weaknesses, _ = aggregate_recurring_patterns([report1, report2])
    assert len(weaknesses) == 1
    assert "Database Indexing (2 sessions)" in weaknesses


def test_recurrence_controlled_terminology_variations():
    """Requirement D: 'Database Indexing Strategies' vs 'Database Indexing' aggregate."""
    report1 = {"top_improvements": [{"title": "Database Indexing Strategies"}]}
    report2 = {"top_improvements": [{"title": "Database Indexing"}]}

    weaknesses, _ = aggregate_recurring_patterns([report1, report2])
    assert len(weaknesses) == 1
    assert "Database Indexing (2 sessions)" in weaknesses


def test_recurrence_known_cache_terminology_variation():
    """Requirement E: 'Cache Invalidation' vs 'Caching Expiration Policies' aggregate."""
    report1 = {"top_improvements": [{"title": "Cache Invalidation"}]}
    report2 = {"top_improvements": [{"title": "Caching Expiration Policies"}]}

    weaknesses, _ = aggregate_recurring_patterns([report1, report2])
    assert len(weaknesses) == 1
    assert "Cache Invalidation (2 sessions)" in weaknesses


def test_recurrence_unrelated_titles_do_not_merge():
    """Requirement F: Unrelated topics sharing a generic word (e.g. Strategies) do NOT merge."""
    report1 = {"top_improvements": [{"title": "SQL Indexing Strategies"}]}
    report2 = {"top_improvements": [{"title": "Caching Strategies"}]}

    weaknesses, _ = aggregate_recurring_patterns([report1, report2])
    assert len(weaknesses) == 0


def test_recurrence_weakness_and_strength_maps_remain_independent():
    """Requirement G: A weakness in Session 1 and strength in Session 2 do not cross-merge."""
    report1 = {"top_improvements": [{"title": "API Error Handling"}]}
    report2 = {"top_strengths": [{"title": "API Error Handling"}]}

    weaknesses, strengths = aggregate_recurring_patterns([report1, report2])
    # Each has count 1 in its own domain -> neither reaches threshold >= 2
    assert len(weaknesses) == 0
    assert len(strengths) == 0


def test_recurrence_safe_handling_of_malformed_reports():
    """Requirement H: Missing/malformed evaluation reports do not crash."""
    malformed_data = [
        None,
        {},
        {"top_improvements": None},
        "not_a_dict",
        {"top_improvements": [{"title": None}, {"invalid_key": 123}, "bad_item"]},
        {"top_strengths": None},
    ]
    weaknesses, strengths = aggregate_recurring_patterns(malformed_data)
    assert weaknesses == []
    assert strengths == []


def test_recurrence_preserves_human_readable_title():
    """Requirement I & J: Human-readable display is preserved and >= 2 threshold enforced."""
    report1 = {"top_strengths": [{"title": "RESTful API Design"}]}
    report2 = {"top_strengths": [{"title": "REST API Design"}]}
    report3 = {"top_strengths": [{"title": "Single Occurrence Strength"}]}

    _, strengths = aggregate_recurring_patterns([report1, report2, report3])
    assert len(strengths) == 1
    assert strengths[0] == "RESTful API Design (2 sessions)"


# =========================================================================
# STEP 10.4 RESUME & JOB DESCRIPTION CONTEXT INTEGRATION TESTS
# =========================================================================

def test_resume_context_renders_summary_skills_experience_projects_education():
    """Requirement A: Resume summary, skills, experience, projects, domains, education appear in prompt."""
    payload = CoachContextPayload(
        candidate_name="Sarah Connor",
        current_session={
            "target_role": "Distributed Systems Engineer",
            "seniority_level": "senior",
            "interview_focus": "Distributed Systems",
            "practice_mode": "full",
            "overall_score": 88,
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context={
            "summary": "8+ years building high-throughput distributed architectures in Python and Go.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Kafka", "Kubernetes"],
            "experience_years": 8.5,
            "experience": [
                {"role": "Lead Architect", "company": "Cyberdyne", "duration": "2021-Present"},
                {"role": "Senior Engineer", "company": "Tech Corp", "duration": "2017-2021"},
            ],
            "projects": [
                {"name": "Event Stream Engine", "description": "High-throughput Kafka ingest cluster"},
                {"name": "Distributed Cache", "description": "Consistent hashing key-value store"},
            ],
            "domains": ["Distributed Systems", "Cloud Infrastructure", "Backend"],
            "education": [
                {"institution": "MIT", "degree": "B.S. Computer Science", "graduation_year": "2017"}
            ],
        },
        jd_context={},
    )

    prompt = payload.to_prompt_context()

    assert "--- CANDIDATE RESUME CONTEXT ---" in prompt
    assert "Resume Summary: 8+ years building high-throughput distributed architectures in Python and Go." in prompt
    assert "Key Skills: Python, FastAPI, PostgreSQL, Redis, Kafka, Kubernetes" in prompt
    assert "Total Experience: 8.5 years" in prompt
    assert "Relevant Experience: Lead Architect at Cyberdyne (2021-Present); Senior Engineer at Tech Corp (2017-2021)" in prompt
    assert "Relevant Projects: Event Stream Engine (High-throughput Kafka ingest cluster); Distributed Cache (Consistent hashing key-value store)" in prompt
    assert "Domains: Distributed Systems, Cloud Infrastructure, Backend" in prompt
    assert "Education: B.S. Computer Science, MIT, 2017" in prompt


def test_resume_context_absent_renders_not_available():
    """Requirement B: Resume context is safely omitted/replaced with 'Not available' when absent."""
    payload = CoachContextPayload(
        candidate_name="John Doe",
        current_session={
            "target_role": "Backend Engineer",
            "seniority_level": "mid",
            "interview_focus": "Python",
            "practice_mode": "standard",
            "overall_score": 75,
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context=None,
        jd_context=None,
    )

    prompt = payload.to_prompt_context()

    assert "--- CANDIDATE RESUME CONTEXT ---" in prompt
    assert "Resume Context: Not available." in prompt


def test_jd_context_renders_role_skills_responsibilities_tech_requirements():
    """Requirement C: Target JD role, required skills, responsibilities, tech, requirements appear when available."""
    payload = CoachContextPayload(
        candidate_name="Ellen Ripley",
        current_session={
            "target_role": "Staff Platform Engineer",
            "seniority_level": "staff",
            "interview_focus": "Cloud Architecture",
            "practice_mode": "full",
            "overall_score": 92,
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context={},
        jd_context={
            "job_title": "Staff Platform Engineer",
            "required_skills": ["Python", "Go", "Distributed Systems", "Kubernetes"],
            "focus_skills": ["Service Mesh", "gRPC"],
            "core_responsibilities": [
                "Lead infrastructure reliability for multi-region clusters",
                "Define platform observability and latency SLO standards",
            ],
            "key_technologies": ["Kubernetes", "Istio", "Prometheus", "Terraform"],
            "experience_summary": "10+ years backend & platform engineering experience.",
        },
    )

    prompt = payload.to_prompt_context()

    assert "--- TARGET JOB DESCRIPTION CONTEXT ---" in prompt
    assert "Target Role: Staff Platform Engineer" in prompt
    assert "Required Skills: Python, Go, Distributed Systems, Kubernetes, Service Mesh, gRPC" in prompt
    assert "Key Responsibilities: Lead infrastructure reliability for multi-region clusters; Define platform observability and latency SLO standards" in prompt
    assert "Key Technologies: Kubernetes, Istio, Prometheus, Terraform" in prompt
    assert "Relevant Requirements: 10+ years backend & platform engineering experience." in prompt


def test_jd_context_absent_renders_not_available():
    """Requirement D: JD context safely handles missing data with 'Not available'."""
    payload = CoachContextPayload(
        candidate_name="Kyle Reese",
        current_session={
            "target_role": "Security Engineer",
            "seniority_level": "senior",
            "interview_focus": "AppSec",
            "practice_mode": "quick",
            "overall_score": 80,
        },
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context={},
        jd_context={},
    )

    prompt = payload.to_prompt_context()

    assert "--- TARGET JOB DESCRIPTION CONTEXT ---" in prompt
    assert "Job Description Context: Not available." in prompt


def test_resume_and_jd_context_do_not_overwrite_or_replace_interview_evidence():
    """Requirement E: Resume and JD context do not overwrite or replace interview transcript evidence or scores."""
    payload = CoachContextPayload(
        candidate_name="Neo Anderson",
        current_session={
            "target_role": "Principal Systems Architect",
            "seniority_level": "principal",
            "interview_focus": "System Design",
            "practice_mode": "standard",
            "overall_score": 90,
            "dimension_scores": {
                "relevance": 92,
                "correctness": 90,
                "keywords": 88,
                "clarity": 91,
                "confidence": 89,
            },
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "How do you design a zero-downtime database migration?",
                "candidate_answer": "Use expand and contract pattern with dual writing and background backfills.",
                "primary_concept": "Database Schema Migrations",
                "covered_concepts": ["Expand and contract", "Dual writing", "Backfill batching"],
                "missed_concepts": ["Shadow table verification"],
                "relevance_score": 95,
                "correctness_score": 92,
                "keywords_score": 88,
                "clarity_score": 90,
                "confidence_score": 86,
                "ideal_answer_comparison": "Excellent breakdown of online schema evolution.",
                "turn_feedback": "Accurate sequencing of dual writes.",
            }
        ],
        evaluation_report={
            "executive_summary": "Outstanding systems execution.",
            "top_strengths": [{"title": "Data Migration", "description": "Strong architectural foresight."}],
            "top_improvements": [{"title": "Data Verification", "description": "Include checksum validation."}],
        },
        historical_performance=[
            {
                "id": "past-1",
                "target_role": "Principal Systems Architect",
                "overall_score": 82,
                "dimension_scores": {"relevance": 85, "correctness": 80},
                "date": "2026-09-01",
            }
        ],
        recurring_weaknesses=["Cache Invalidation (2 sessions)"],
        recurring_strengths=["System Design Trade-offs (2 sessions)"],
        conversation_history=[],
        resume_context={
            "summary": "12+ years in large scale distributed systems.",
            "skills": ["Distributed Databases", "Go", "Python"],
        },
        jd_context={
            "job_title": "Principal Systems Architect",
            "required_skills": ["Distributed Databases", "CAP Theorem", "Zero Downtime Deployments"],
        },
    )

    prompt = payload.to_prompt_context()

    # Both Reference Contexts are present
    assert "--- CANDIDATE RESUME CONTEXT ---" in prompt
    assert "Resume Summary: 12+ years in large scale distributed systems." in prompt
    assert "--- TARGET JOB DESCRIPTION CONTEXT ---" in prompt
    assert "Required Skills: Distributed Databases, CAP Theorem, Zero Downtime Deployments" in prompt

    # Transcript & Turn Evidence remain completely intact
    assert "--- INTERVIEW TURNS & CANDIDATE ANSWERS ---" in prompt
    assert "[Turn 1]" in prompt
    assert "Question: How do you design a zero-downtime database migration?" in prompt
    assert "Candidate Answer: Use expand and contract pattern with dual writing and background backfills." in prompt
    assert "Primary Concept: Database Schema Migrations" in prompt
    assert "Covered Concepts: Expand and contract, Dual writing, Backfill batching" in prompt
    assert "Missed Concepts: Shadow table verification" in prompt
    assert "Scores: [Relevance: 95/100, Correctness: 92/100, Keywords: 88/100, Clarity: 90/100, Confidence: 86/100]" in prompt
    assert "Benchmark Comparison: Excellent breakdown of online schema evolution." in prompt
    assert "Evaluator Feedback: Accurate sequencing of dual writes." in prompt

    # Historical & Recurring patterns remain intact
    assert "--- HISTORICAL PERFORMANCE ACROSS PREVIOUS SESSIONS ---" in prompt
    assert "Detected Recurring Weaknesses: Cache Invalidation (2 sessions)" in prompt
    assert "Consistent Demonstrated Strengths: System Design Trade-offs (2 sessions)" in prompt


def test_large_raw_resume_and_jd_text_is_bounded_and_truncated():
    """Requirement F: Large raw resume/JD text is bounded and truncated safely."""
    huge_resume = "Candidate accomplished " + "extraordinary achievements " * 100
    huge_jd = "Target Company requires " + "exceptional qualifications " * 100

    truncated_res = _truncate_text(huge_resume, 200)
    assert len(truncated_res) <= 200 + len("... [truncated]")
    assert truncated_res.endswith("... [truncated]")

    truncated_jd = _truncate_text(huge_jd, 200)
    assert len(truncated_jd) <= 200 + len("... [truncated]")
    assert truncated_jd.endswith("... [truncated]")

    payload = CoachContextPayload(
        candidate_name="Raw Candidate",
        current_session={"target_role": "Backend Engineer", "overall_score": 70},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context={"raw_text": huge_resume},
        jd_context={"custom_job_desc": huge_jd},
    )

    prompt = payload.to_prompt_context()
    assert "Resume Text Summary:" in prompt
    assert "Job Description Summary:" in prompt
    assert "... [truncated]" in prompt


def test_malformed_and_none_parsed_resume_data_does_not_crash():
    """Requirement G: Malformed/None parsed resume fields do not crash context generation."""
    # Test _truncate_text with bad types
    assert _truncate_text(None) == ""
    assert _truncate_text(12345) == ""
    assert _truncate_text({}) == ""
    assert _truncate_text(["bad", "list"]) == ""

    payload = CoachContextPayload(
        candidate_name="Corrupted Resume Test",
        current_session={"target_role": "Backend Engineer"},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context={
            "summary": None,
            "skills": [None, "", 123, "ValidSkill"],
            "experience_years": "invalid_number",
            "experience": [None, "Valid string role", {"role": None, "company": None}],
            "projects": [None, {"name": None, "description": None}, 456],
            "domains": [None, "Backend", ""],
            "education": [None, {}, {"institution": "Tech U", "degree": None, "graduation_year": None}],
        },
        jd_context={},
    )

    prompt = payload.to_prompt_context()
    assert "Key Skills: 123, ValidSkill" in prompt
    assert "Relevant Experience: Valid string role" in prompt
    assert "Domains: Backend" in prompt
    assert "Education: Tech U" in prompt


def test_malformed_and_none_parsed_jd_data_does_not_crash():
    """Requirement H: Malformed/None parsed JD fields do not crash context generation."""
    payload = CoachContextPayload(
        candidate_name="Corrupted JD Test",
        current_session={"target_role": "Backend Engineer"},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        resume_context={},
        jd_context={
            "job_title": None,
            "target_role": None,
            "required_skills": [None, "", 999, "FastAPI"],
            "focus_skills": [None, ""],
            "core_responsibilities": [None, 123, "Build reliable microservices", ""],
            "key_technologies": [None, "", "PostgreSQL"],
            "relevant_requirements": None,
            "experience_summary": None,
        },
    )

    prompt = payload.to_prompt_context()
    assert "Required Skills: 999, FastAPI" in prompt
    assert "Key Responsibilities: 123; Build reliable microservices" in prompt
    assert "Key Technologies: PostgreSQL" in prompt


@pytest.mark.asyncio
async def test_coach_context_builder_user_scoped_resume_and_jd(db_session):
    """Requirement J: CoachContextBuilder enforces user-scoped data access for Resume and JD."""
    from app.models.resume import Resume
    from app.models.interview import InterviewSession
    from app.models.user import User

    # Create User A
    user_a = User(
        id="user-aaa-111",
        email="user_a@example.com",
        full_name="Alice UserA",
        hashed_password="hashed_pw_a",
    )
    # Create User B
    user_b = User(
        id="user-bbb-222",
        email="user_b@example.com",
        full_name="Bob UserB",
        hashed_password="hashed_pw_b",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Create Resume for User A
    resume_a = Resume(
        id="res-aaa-111",
        user_id="user-aaa-111",
        file_name="alice_resume.pdf",
        file_path="/resumes/alice_resume.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        raw_text="Alice raw resume text",
        parsed_data={
            "summary": "Alice is a Cloud Architect",
            "skills": ["AWS", "Terraform", "Python"],
        },
    )
    # Create Resume for User B
    resume_b = Resume(
        id="res-bbb-222",
        user_id="user-bbb-222",
        file_name="bob_resume.pdf",
        file_path="/resumes/bob_resume.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        raw_text="Bob raw resume text",
        parsed_data={
            "summary": "Bob is a Frontend Specialist",
            "skills": ["React", "CSS", "TypeScript"],
        },
    )
    db_session.add_all([resume_a, resume_b])
    await db_session.commit()

    # Create InterviewSession for User A
    session_a = InterviewSession(
        id="sess-aaa-111",
        user_id="user-aaa-111",
        resume_id="res-aaa-111",
        target_role="Cloud Architect",
        seniority_level="senior",
        interview_focus="Cloud Infrastructure",
        practice_mode="full",
        custom_job_desc="Looking for Senior Cloud Architect with AWS experience.",
        parsed_jd_data={
            "job_title": "Senior Cloud Architect",
            "required_skills": ["AWS", "Terraform"],
        },
        status="completed",
        overall_score=85,
    )
    db_session.add(session_a)
    await db_session.commit()

    builder = CoachContextBuilder()

    # Build context as User A
    payload_a = await builder.build_context(
        db=db_session,
        current_user=user_a,
        session_id="sess-aaa-111",
    )

    prompt_a = payload_a.to_prompt_context()

    # Assert User A's resume & JD are present
    assert "Alice is a Cloud Architect" in prompt_a
    assert "AWS, Terraform, Python" in prompt_a
    assert "Senior Cloud Architect" in prompt_a

    # Assert User B's resume data is NOT leaked into User A's context
    assert "Bob is a Frontend Specialist" not in prompt_a
    assert "React, CSS, TypeScript" not in prompt_a

    # Build context as User B querying User A's session -> should NOT fetch User A's session or resume
    payload_b = await builder.build_context(
        db=db_session,
        current_user=user_b,
        session_id="sess-aaa-111",
    )
    prompt_b = payload_b.to_prompt_context()

    # User B should only see their own resume and no session from User A
    assert "Bob is a Frontend Specialist" in prompt_b
    assert "React, CSS, TypeScript" in prompt_b
    assert "Alice is a Cloud Architect" not in prompt_b
    assert "sess-aaa-111" not in prompt_b


# =========================================================================
# STEP 10.7: TURN DURATION, PACING & FILLER METRICS TESTS
# =========================================================================

def test_classify_pacing_thresholds_and_boundaries():
    """Verify deterministic pacing classification across all threshold boundaries."""
    # Invalid / Unrecorded cases -> None
    assert classify_pacing(None) is None
    assert classify_pacing(0) is None
    assert classify_pacing(-1) is None
    assert classify_pacing(-50) is None
    assert classify_pacing("42") is None
    assert classify_pacing(True) is None
    assert classify_pacing(False) is None
    assert classify_pacing(45.5) is None

    # Very concise: 1 - 19s
    assert classify_pacing(1) == "Very concise"
    assert classify_pacing(10) == "Very concise"
    assert classify_pacing(19) == "Very concise"

    # Concise: 20 - 45s
    assert classify_pacing(20) == "Concise"
    assert classify_pacing(30) == "Concise"
    assert classify_pacing(45) == "Concise"

    # Moderate: 46 - 120s (standard technical/behavioral pacing limit)
    assert classify_pacing(46) == "Moderate"
    assert classify_pacing(80) == "Moderate"
    assert classify_pacing(120) == "Moderate"

    # Long: 121 - 180s (system design pacing limit)
    assert classify_pacing(121) == "Long"
    assert classify_pacing(150) == "Long"
    assert classify_pacing(180) == "Long"

    # Very long: > 180s
    assert classify_pacing(181) == "Very long"
    assert classify_pacing(240) == "Very long"
    assert classify_pacing(600) == "Very long"


def test_extract_filler_metrics_permutations():
    """Verify safe extraction of filler word count and density across diverse structures."""
    # 1. Standard filler_word_stats nested dictionary
    stats_turn = {"filler_word_stats": {"count": 4, "density": 3.2, "detected": ["um", "like"]}}
    c, d = _extract_filler_metrics(stats_turn)
    assert c == 4
    assert d == 3.2

    # 2. Nested within evaluation_data
    nested_turn = {"evaluation_data": {"filler_word_stats": {"count": 2, "density": 1.5}}}
    c, d = _extract_filler_metrics(nested_turn)
    assert c == 2
    assert d == 1.5

    # 3. Direct filler_count and filler_density
    direct_turn = {"filler_count": 5, "filler_density": 4.0}
    c, d = _extract_filler_metrics(direct_turn)
    assert c == 5
    assert d == 4.0

    # 4. filler_words_detected list in evaluation_data
    list_turn = {"evaluation_data": {"filler_words_detected": ["um", "uh", "actually"]}}
    c, d = _extract_filler_metrics(list_turn)
    assert c == 3
    assert d is None

    # 5. filler_words integer field
    int_turn = {"filler_words": 1}
    c, d = _extract_filler_metrics(int_turn)
    assert c == 1
    assert d is None

    # 6. Malformed or invalid data handled gracefully
    assert _extract_filler_metrics({}) == (None, None)
    assert _extract_filler_metrics(None) == (None, None)
    assert _extract_filler_metrics({"evaluation_data": "invalid string"}) == (None, None)
    assert _extract_filler_metrics({"filler_word_stats": {"count": -2, "density": -1.0}}) == (None, None)
    assert _extract_filler_metrics({"filler_count": "three", "filler_density": "high"}) == (None, None)
    assert _extract_filler_metrics({"filler_count": True, "filler_density": False}) == (None, None)


def test_to_prompt_context_turn_duration_pacing_and_filler_metrics():
    """Verify duration, pacing classification, and filler metrics are correctly rendered per turn."""
    payload = CoachContextPayload(
        candidate_name="Elena Rostova",
        current_session={
            "target_role": "Backend Architect",
            "seniority_level": "lead",
            "interview_focus": "Distributed Systems",
            "practice_mode": "full",
            "overall_score": 90,
            "dimension_scores": {
                "relevance": 92,
                "correctness": 90,
                "keywords": 88,
                "clarity": 91,
                "confidence": 89,
            },
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "How do you achieve consensus in distributed systems?",
                "candidate_answer": "We use Raft with leader election and log replication.",
                "primary_concept": "Distributed Consensus",
                "covered_concepts": ["Raft consensus", "Leader election"],
                "missed_concepts": ["Byzantine fault tolerance"],
                "relevance_score": 95,
                "correctness_score": 92,
                "keywords_score": 90,
                "clarity_score": 94,
                "confidence_score": 88,
                "turn_duration_sec": 42,
                "filler_count": 2,
                "filler_density": 1.8,
            },
            {
                "turn_index": 1,
                "question_text": "Explain CAP theorem trade-offs.",
                "candidate_answer": "Under network partition, you must choose consistency or availability.",
                "primary_concept": "CAP Theorem",
                "covered_concepts": ["PACELC theorem", "Partition tolerance"],
                "missed_concepts": [],
                "relevance_score": 90,
                "correctness_score": 88,
                "keywords_score": 86,
                "clarity_score": 89,
                "confidence_score": 90,
                "turn_duration_sec": 85,
                "filler_count": 0,
            },
            {
                "turn_index": 2,
                "question_text": "Design a globally distributed rate limiter.",
                "candidate_answer": "Use Redis cluster with Sliding Window Counter and local token buckets.",
                "primary_concept": "Rate Limiting",
                "covered_concepts": ["Sliding window counter", "Redis synchronization"],
                "missed_concepts": ["Clock skew compensation"],
                "relevance_score": 94,
                "correctness_score": 91,
                "keywords_score": 92,
                "clarity_score": 90,
                "confidence_score": 93,
                "turn_duration_sec": 160,
                # No filler metrics recorded
            },
            {
                "turn_index": 3,
                "question_text": "What is write amplification in LSM trees?",
                "candidate_answer": "LSM trees buffer in memory and flush to SSTables sequentially.",
                "primary_concept": "LSM Trees",
                "covered_concepts": ["MemTable flush", "Compaction"],
                "missed_concepts": ["Compaction write overhead"],
                "relevance_score": 88,
                "correctness_score": 85,
                "keywords_score": 80,
                "clarity_score": 82,
                "confidence_score": 84,
                "turn_duration_sec": 210,
                "filler_count": 6,
                "filler_density": 4.5,
            },
        ],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # Turn 1: 42s (Concise), 2 fillers (1.8% density)
    assert "Duration: 42 seconds" in prompt
    assert "Pacing: Concise" in prompt
    assert "Filler Words: 2 (1.8% density)" in prompt

    # Turn 2: 85s (Moderate), 0 fillers
    assert "Duration: 85 seconds" in prompt
    assert "Pacing: Moderate" in prompt
    assert "Filler Words: 0" in prompt

    # Turn 3: 160s (Long), unrecorded fillers
    assert "Duration: 160 seconds" in prompt
    assert "Pacing: Long" in prompt
    assert "Filler Words: Not recorded" in prompt

    # Turn 4: 210s (Very long), 6 fillers (4.5% density)
    assert "Duration: 210 seconds" in prompt
    assert "Pacing: Very long" in prompt
    assert "Filler Words: 6 (4.5% density)" in prompt


def test_to_prompt_context_missing_and_invalid_duration_safely_rendered():
    """Verify missing, zero, or negative duration safely renders 'Not recorded' without crashing."""
    payload = CoachContextPayload(
        candidate_name="Dev Candidate",
        current_session={
            "target_role": "Software Engineer",
            "seniority_level": "mid",
            "interview_focus": "Technical Core",
            "practice_mode": "quick",
            "overall_score": None,
            "dimension_scores": None,
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "What is polymorphism?",
                "candidate_answer": "Subtypes providing specific implementations.",
                "turn_duration_sec": None,  # Missing
            },
            {
                "turn_index": 1,
                "question_text": "What is encapsulation?",
                "candidate_answer": "Hiding internal state behind public interfaces.",
                "turn_duration_sec": 0,  # Zero duration (invalid)
            },
            {
                "turn_index": 2,
                "question_text": "What is inheritance?",
                "candidate_answer": "Reusing code across class hierarchies.",
                "turn_duration_sec": -15,  # Negative duration (invalid)
            },
            {
                "turn_index": 3,
                "question_text": "What is abstraction?",
                "candidate_answer": "Exposing only relevant high-level details.",
                "turn_duration_sec": "forty_seconds",  # Malformed string (invalid)
            },
        ],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
    )

    prompt = payload.to_prompt_context()

    # All 4 turns should safely render "Duration: Not recorded"
    assert prompt.count("Duration: Not recorded") == 4
    # Ensure invalid values are NEVER rendered as legitimate timing evidence
    assert "Duration: 0 seconds" not in prompt
    assert "Duration: -15 seconds" not in prompt
    assert "Duration: forty_seconds" not in prompt


@pytest.mark.asyncio
async def test_coach_context_builder_duration_and_filler_integration(db_session):
    """Verify CoachContextBuilder correctly pulls turn_duration_sec and filler stats from DB models."""
    from app.models.interview import InterviewQuestionTurn, InterviewSession
    from app.models.user import User

    user = User(
        id="user-dur-001",
        email="dur_user@example.com",
        full_name="Pacing Tester",
        hashed_password="hashed_pw_dur",
    )
    session = InterviewSession(
        id="sess-dur-001",
        user_id="user-dur-001",
        target_role="Database Specialist",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        overall_score=86,
    )
    db_session.add_all([user, session])
    await db_session.commit()

    # Create turns with duration and filler stats in evaluation_data
    turn_1 = InterviewQuestionTurn(
        id="turn-dur-001",
        session_id=session.id,
        turn_index=0,
        question_text="How do you optimize SQL query execution plans?",
        candidate_answer="By analyzing EXPLAIN plans and adding composite indexes on WHERE clauses.",
        turn_duration_sec=75,
        relevance_score=92,
        correctness_score=90,
        keywords_score=88,
        clarity_score=91,
        confidence_score=89,
        turn_score=90,
        evaluation_data={
            "primary_concept": "SQL Query Optimization",
            "covered_concepts": ["EXPLAIN plan analysis", "Composite indexes"],
            "missed_concepts": ["Index cardinality"],
            "turn_feedback": "Accurate indexing explanation.",
            "filler_word_stats": {
                "count": 3,
                "density": 2.2,
                "detected": ["um", "like", "basically"],
            },
        },
    )
    turn_2 = InterviewQuestionTurn(
        id="turn-dur-002",
        session_id=session.id,
        turn_index=1,
        question_text="What is the difference between clustered and non-clustered indexes?",
        candidate_answer="A clustered index defines physical table row ordering.",
        turn_duration_sec=14,  # Very concise (< 20s)
        relevance_score=85,
        correctness_score=82,
        keywords_score=80,
        clarity_score=84,
        confidence_score=80,
        turn_score=82,
        evaluation_data={
            "primary_concept": "Clustered Indexes",
            "covered_concepts": ["Physical row ordering"],
            "missed_concepts": ["B-tree leaf node structure"],
            "turn_feedback": "Brief answer.",
            "filler_word_stats": {
                "count": 0,
                "density": 0.0,
                "detected": [],
            },
        },
    )
    db_session.add_all([turn_1, turn_2])
    await db_session.commit()

    builder = CoachContextBuilder()
    payload = await builder.build_context(
        db=db_session,
        current_user=user,
        session_id=session.id,
    )

    # 1. Verify transcript_turns payload structure
    assert len(payload.transcript_turns) == 2
    t1 = payload.transcript_turns[0]
    assert t1["turn_duration_sec"] == 75
    assert t1["filler_count"] == 3
    assert t1["filler_density"] == 2.2

    t2 = payload.transcript_turns[1]
    assert t2["turn_duration_sec"] == 14
    assert t2["filler_count"] == 0
    assert t2["filler_density"] == 0.0

    # 2. Verify prompt string rendering
    prompt = payload.to_prompt_context()
    assert "Duration: 75 seconds" in prompt
    assert "Pacing: Moderate" in prompt
    assert "Filler Words: 3 (2.2% density)" in prompt

    assert "Duration: 14 seconds" in prompt
    assert "Pacing: Very concise" in prompt
    assert "Filler Words: 0 (0.0% density)" in prompt


def test_duration_and_pacing_do_not_alter_evaluation_scoring_or_trends():
    """Verify that adding duration, pacing, and filler context leaves all 5 score dimensions, trends, and resume/JD untouched."""
    payload = CoachContextPayload(
        candidate_name="Invariant Test Candidate",
        current_session={
            "target_role": "Principal Engineer",
            "seniority_level": "staff",
            "interview_focus": "System Design",
            "practice_mode": "full",
            "overall_score": 88,
            "dimension_scores": {
                "relevance": 92,
                "correctness": 87,
                "keywords": 85,
                "clarity": 89,
                "confidence": 87,
            },
        },
        transcript_turns=[
            {
                "turn_index": 0,
                "question_text": "Explain distributed transaction handling.",
                "candidate_answer": "Two-phase commit coordinates across resource managers with prepare and commit phases.",
                "primary_concept": "Two-Phase Commit",
                "covered_concepts": ["Coordinator prepare phase", "Commit phase lock release"],
                "missed_concepts": ["Blocking coordinator failure mode"],
                "relevance_score": 92,
                "correctness_score": 87,
                "keywords_score": 85,
                "clarity_score": 89,
                "confidence_score": 87,
                "turn_duration_sec": 95,
                "filler_count": 1,
                "filler_density": 0.9,
            }
        ],
        evaluation_report={
            "executive_summary": "Strong architectural depth with solid transaction mechanics.",
            "top_strengths": [{"title": "2PC Protocol", "description": "Mastery of phase semantics."}],
            "top_improvements": [{"title": "Saga Pattern", "description": "Recommend asynchronous compensations.", "actionable_recommendation": "Study Choreography vs Orchestration."}],
        },
        historical_performance=[
            {
                "target_role": "Senior Engineer",
                "overall_score": 75,
                "dimension_scores": {"relevance": 80, "correctness": 75, "keywords": 70, "clarity": 78, "confidence": 72},
                "date": "2026-03-01",
            }
        ],
        recurring_weaknesses=["Saga Pattern (2 sessions)"],
        recurring_strengths=["2PC Protocol (2 sessions)"],
        conversation_history=[],
        resume_context={"summary": "Principal Engineer with 12 years in distributed systems."},
        jd_context={"target_role": "Principal Engineer", "required_skills": ["Distributed Transactions", "Kafka"]},
    )

    prompt = payload.to_prompt_context()

    # Scores remain exact
    assert "Current Session Overall Score: 88/100" in prompt
    assert "Scores: [Relevance: 92/100, Correctness: 87/100, Keywords: 85/100, Clarity: 89/100, Confidence: 87/100]" in prompt

    # Trends remain exact
    assert "Overall Score Trend:\n75 → 88\nNet Change: +13 points\nDirection: Improving" in prompt
    assert "- Relevance: 80 → 92 (+12, Improving)" in prompt
    assert "- Correctness: 75 → 87 (+12, Improving)" in prompt
    assert "- Keywords: 70 → 85 (+15, Improving)" in prompt
    assert "- Clarity: 78 → 89 (+11, Improving)" in prompt
    assert "- Confidence: 72 → 87 (+15, Improving)" in prompt

    # Recurrence remains exact
    assert "Detected Recurring Weaknesses: Saga Pattern (2 sessions)" in prompt
    assert "Consistent Demonstrated Strengths: 2PC Protocol (2 sessions)" in prompt

    # Resume & JD context remain exact
    assert "Principal Engineer with 12 years in distributed systems." in prompt
    assert "Distributed Transactions, Kafka" in prompt

    # Duration and pacing are present without interfering with the above
    assert "Duration: 95 seconds" in prompt
    assert "Pacing: Moderate" in prompt
    assert "Filler Words: 1 (0.9% density)" in prompt


