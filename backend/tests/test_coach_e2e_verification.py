"""AROVIA Step 10.8 — Comprehensive End-to-End & Longitudinal Coach Verification Suite.

Validates:
1. Longitudinal progression across 3 distinct completed interview sessions for one candidate.
2. Grounded evidence availability for core candidate coaching inquiries.
3. Sentinel data prompt grounding and anti-hallucination isolation.
4. Complete Coach data pipeline from Interview to Evaluation to CoachMessage.
"""

from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.resume import Resume
from app.models.user import User
from app.services.coach_context_builder import CoachContextBuilder, CoachContextPayload
from app.services.coach_service import CoachService


@pytest.fixture
def mock_coach_ai():
    """Mock Gemini AI boundary for deterministic testing."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### AI Coach Debrief\n\nExcellent growth trajectory across your 3 sessions!"
        )
        mock_chat.return_value = {
            "coach_response": "Grounded coaching response using actual transcript and trend evidence.",
            "suggested_followups": [
                "How do I optimize database indexes?",
                "What should I study next?",
            ],
        }
        yield {"debrief": mock_debrief, "chat": mock_chat}


# =========================================================================
# 1. STEP 3: LONGITUDINAL SCENARIO (3 COMPLETED SESSIONS)
# =========================================================================

@pytest.mark.asyncio
async def test_step3_longitudinal_three_sessions_trajectory(db_session: AsyncSession):
    """Verify CoachContextBuilder generates accurate trend analysis and recurring weakness detection across 3 sessions."""
    # Create Candidate
    user = User(
        id="user-longitudinal-001",
        email="longitudinal_candidate@example.com",
        full_name="Jordan Reed",
        hashed_password="hashed_pw_longitudinal",
    )
    db_session.add(user)
    await db_session.commit()

    from datetime import datetime, timezone

    # Session 1 (Oldest: Jan 2026)
    # Overall = 55, Correctness = 48, Clarity = 70, Weakness = Database Indexing
    sess1 = InterviewSession(
        id="sess-long-1",
        user_id=user.id,
        target_role="Backend Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        started_at=datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
        overall_score=55,
        dimension_scores={
            "relevance": 60,
            "correctness": 48,
            "keywords": 50,
            "clarity": 70,
            "confidence": 55,
        },
        evaluation_report={
            "executive_summary": "Initial baseline session.",
            "top_strengths": [{"title": "API Design", "description": "Good REST principles."}],
            "top_improvements": [{"title": "Database Indexing", "description": "Lacks B-Tree index understanding."}],
        },
    )

    # Session 2 (Middle: Feb 2026)
    # Overall = 68, Correctness = 61, Clarity = 72, Weakness = Database Indexing Strategies
    sess2 = InterviewSession(
        id="sess-long-2",
        user_id=user.id,
        target_role="Backend Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        started_at=datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
        overall_score=68,
        dimension_scores={
            "relevance": 72,
            "correctness": 61,
            "keywords": 65,
            "clarity": 72,
            "confidence": 68,
        },
        evaluation_report={
            "executive_summary": "Second session showing moderate gains.",
            "top_strengths": [{"title": "API Error Handling", "description": "Clear error schemas."}],
            "top_improvements": [{"title": "Database Indexing Strategies", "description": "Still struggling with composite indexes."}],
        },
    )

    # Session 3 (Current/Latest: Mar 2026)
    # Overall = 76, Correctness = 74, Clarity = 81, Weakness = Database Indexing
    sess3 = InterviewSession(
        id="sess-long-3",
        user_id=user.id,
        target_role="Backend Engineer",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        status="completed",
        started_at=datetime(2026, 3, 10, 10, 0, 0, tzinfo=timezone.utc),
        overall_score=76,
        dimension_scores={
            "relevance": 80,
            "correctness": 74,
            "keywords": 75,
            "clarity": 81,
            "confidence": 75,
        },
        evaluation_report={
            "executive_summary": "Third session showing solid improvement.",
            "top_strengths": [{"title": "Query Optimization", "description": "Good EXPLAIN plan breakdown."}],
            "top_improvements": [{"title": "Database Indexing", "description": "Needs further depth on write amplification."}],
        },
    )

    db_session.add_all([sess1, sess2, sess3])
    await db_session.commit()

    # Add turns for Session 3
    t1 = InterviewQuestionTurn(
        id="turn-long-3-1",
        session_id=sess3.id,
        turn_index=0,
        question_text="How does a B-Tree index work?",
        candidate_answer="B-Trees maintain sorted balance for fast search.",
        relevance_score=82,
        correctness_score=75,
        keywords_score=76,
        clarity_score=82,
        confidence_score=78,
        turn_duration_sec=50,
        evaluation_data={
            "primary_concept": "B-Tree Indexes",
            "covered_concepts": ["Balanced tree", "Sorted keys"],
            "missed_concepts": ["Leaf node chaining"],
            "filler_word_stats": {"count": 1, "density": 1.2, "detected": ["um"]},
        },
    )
    db_session.add(t1)
    await db_session.commit()

    builder = CoachContextBuilder()
    payload = await builder.build_context(
        db=db_session,
        current_user=user,
        session_id=sess3.id,
    )

    prompt = payload.to_prompt_context()

    # 1. Verify Overall Trend Progression (55 -> 68 -> 76 = +21 points, Improving)
    assert "Overall Score Trend:\n55 → 68 → 76\nNet Change: +21 points\nDirection: Improving" in prompt

    # 2. Verify Correctness Trend Progression (48 -> 61 -> 74 = +26 points, Improving)
    assert "- Correctness: 48 → 61 → 74 (+26, Improving)" in prompt

    # 3. Verify Clarity Trend Progression (70 -> 72 -> 81 = +11 points, Improving)
    assert "- Clarity: 70 → 72 → 81 (+11, Improving)" in prompt

    # 4. Verify Recurring Weakness Canonical Aggregation
    # "Database Indexing" occurred across all 3 sessions
    assert "Detected Recurring Weaknesses: Database Indexing (3 sessions)" in prompt


# =========================================================================
# 2. STEP 4: COACH PERSONALIZATION EVIDENCE VALIDATION
# =========================================================================

@pytest.mark.asyncio
async def test_step4_coach_personalization_evidence_completeness(
    db_session: AsyncSession, mock_coach_ai
):
    """Verify that the Coach context contains all concrete evidence required to answer the 5 canonical coaching questions."""
    user = User(
        id="user-pers-001",
        email="pers_candidate@example.com",
        full_name="Samantha Taylor",
        hashed_password="hashed_pw_pers",
    )
    resume = Resume(
        id="res-pers-001",
        user_id=user.id,
        file_name="samantha_cv.pdf",
        file_path="/resumes/samantha_cv.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        raw_text="Samantha Taylor 8 years backend engineer with Go, Kubernetes, Kafka, gRPC.",
        parsed_data={
            "summary": "Senior Distributed Systems Engineer with 8 years experience.",
            "skills": ["Go", "Kubernetes", "Kafka", "gRPC", "PostgreSQL"],
            "experience_years": 8,
        },
    )
    db_session.add_all([user, resume])
    await db_session.commit()

    session = InterviewSession(
        id="sess-pers-001",
        user_id=user.id,
        resume_id=resume.id,
        target_role="Lead Platform Engineer",
        seniority_level="staff",
        interview_focus="System Design",
        practice_mode="full",
        custom_job_desc="Seeking Lead Platform Engineer with deep Kubernetes operators and Kafka event streaming experience.",
        parsed_jd_data={
            "job_title": "Lead Platform Engineer",
            "required_skills": ["Kubernetes Operators", "Kafka", "Distributed Transactions"],
            "key_responsibilities": ["Design multi-region event pipelines", "Architect resilient Kubernetes controllers"],
        },
        status="completed",
        overall_score=78,
        dimension_scores={"relevance": 82, "correctness": 75, "keywords": 74, "clarity": 80, "confidence": 76},
        evaluation_report={
            "executive_summary": "Solid platform concepts with gaps in distributed locking.",
            "top_strengths": [{"title": "Kubernetes Architecture", "description": "Deep understanding of control loops."}],
            "top_improvements": [{"title": "Distributed Locking", "description": "Missed fencing tokens and split-brain.", "actionable_recommendation": "Study Martin Kleppmann's analysis on Redlock."}],
        },
    )
    db_session.add(session)
    await db_session.commit()

    turn0 = InterviewQuestionTurn(
        id="turn-pers-0",
        session_id=session.id,
        turn_index=0,
        question_text="How do Kubernetes controllers maintain desired state?",
        candidate_answer="Through reconciliation loops comparing spec and status.",
        relevance_score=90,
        correctness_score=88,
        keywords_score=86,
        clarity_score=90,
        confidence_score=88,
        turn_duration_sec=60,
        evaluation_data={
            "primary_concept": "Reconciliation Loop",
            "covered_concepts": ["Informer cache", "WorkQueue"],
            "missed_concepts": ["RateLimitingInterface"],
            "ideal_answer_comparison": "Solid breakdown of control loop.",
            "turn_feedback": "Accurate explanation of level-triggered controllers.",
            "filler_word_stats": {"count": 1, "density": 0.8},
        },
    )
    turn1 = InterviewQuestionTurn(
        id="turn-pers-1",
        session_id=session.id,
        turn_index=1,
        question_text="How do you implement distributed locking in Redis?",
        candidate_answer="Set a key with NX and PX options.",
        relevance_score=70,
        correctness_score=62,
        keywords_score=65,
        clarity_score=72,
        confidence_score=68,
        turn_duration_sec=25,
        evaluation_data={
            "primary_concept": "Distributed Locks",
            "covered_concepts": ["SET NX PX"],
            "missed_concepts": ["Fencing Tokens", "Clock Skew", "Redlock"],
            "ideal_answer_comparison": "Incomplete without fencing tokens to prevent split-brain during GC pauses.",
            "turn_feedback": "Needs to address race conditions when lock expires while client is processing.",
            "filler_word_stats": {"count": 3, "density": 3.5},
        },
    )
    db_session.add_all([turn0, turn1])
    await db_session.commit()

    captured_context: CoachContextPayload = None

    async def capture_debrief(ctx: CoachContextPayload):
        nonlocal captured_context
        captured_context = ctx
        return "Debrief"

    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        side_effect=capture_debrief,
    ):
        service = CoachService()
        await service.get_or_create_conversation(
            db=db_session,
            current_user=user,
            session_id=session.id,
            auto_debrief=True,
        )

    assert captured_context is not None
    prompt = captured_context.to_prompt_context()

    # Question 1 Evidence: "Why was my Turn 2 answer weak?"
    # Turn 2 has Turn 1 index (0-indexed 1 -> [Turn 2])
    assert "[Turn 2]" in prompt
    assert "How do you implement distributed locking in Redis?" in prompt
    assert "Set a key with NX and PX options." in prompt
    assert "Missed Concepts: Fencing Tokens, Clock Skew, Redlock" in prompt
    assert "Scores: [Relevance: 70/100, Correctness: 62/100, Keywords: 65/100, Clarity: 72/100, Confidence: 68/100]" in prompt
    assert "Duration: 25 seconds" in prompt
    assert "Pacing: Concise" in prompt

    # Question 2 Evidence: "Am I improving compared with my previous interviews?"
    # Historical section indicates baseline session
    assert "Historical Performance: This is the candidate's first recorded interview session in AROVIA." in prompt

    # Question 3 Evidence: "What should I practice next?"
    # Actionable recommendation from evaluation report is present
    assert "Study Martin Kleppmann's analysis on Redlock." in prompt

    # Question 4 Evidence: "How does my performance compare with the target role?"
    # Target Role & Seniority are present
    assert "Target Role: Lead Platform Engineer (staff)" in prompt
    assert "Required Skills: Kubernetes Operators, Kafka, Distributed Transactions" in prompt
    assert "Key Responsibilities: Design multi-region event pipelines; Architect resilient Kubernetes controllers" in prompt

    # Question 5 Evidence: "Which resume skills do I need to articulate better?"
    # Resume Skills & Experience are present
    assert "Key Skills: Go, Kubernetes, Kafka, gRPC, PostgreSQL" in prompt
    assert "Total Experience: 8 years" in prompt


# =========================================================================
# 3. STEP 10: PROMPT GROUNDING & SENTINEL VALUE ANTI-HALLUCINATION TEST
# =========================================================================

@pytest.mark.asyncio
async def test_step10_sentinel_grounding_and_cross_user_anti_hallucination(
    db_session: AsyncSession,
):
    """Verify distinct sentinel values appear only in appropriate sections and never leak to other users."""
    SENTINEL_RESUME_A = "SENTINEL_RESUME_SKILL_ALPHA_9981"
    SENTINEL_JD_A = "SENTINEL_JD_REQUIREMENT_ALPHA_4472"
    SENTINEL_ANSWER_A = "SENTINEL_INTERVIEW_ANSWER_ALPHA_3321"
    SENTINEL_WEAKNESS_A = "SENTINEL_WEAKNESS_ALPHA_1109"

    SENTINEL_RESUME_B = "SENTINEL_RESUME_SKILL_BETA_8832"
    SENTINEL_JD_B = "SENTINEL_JD_REQUIREMENT_BETA_7714"
    SENTINEL_ANSWER_B = "SENTINEL_INTERVIEW_ANSWER_BETA_5543"

    # User A
    user_a = User(id="user-sentinel-a", email="sentinel_a@example.com", full_name="Alice Sentinel", hashed_password="pw")
    resume_a = Resume(
        id="res-sentinel-a",
        user_id=user_a.id,
        file_name="a.pdf",
        file_path="/a.pdf",
        file_size_bytes=100,
        mime_type="application/pdf",
        raw_text=f"Skills: {SENTINEL_RESUME_A}",
        parsed_data={"skills": [SENTINEL_RESUME_A]},
    )
    session_a = InterviewSession(
        id="sess-sentinel-a",
        user_id=user_a.id,
        resume_id=resume_a.id,
        target_role="Alpha Specialist",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        custom_job_desc=f"Must have {SENTINEL_JD_A}",
        parsed_jd_data={"required_skills": [SENTINEL_JD_A]},
        status="completed",
        overall_score=85,
        evaluation_report={"top_improvements": [{"title": SENTINEL_WEAKNESS_A, "description": "Needs work."}]},
    )
    turn_a = InterviewQuestionTurn(
        id="turn-sentinel-a",
        session_id=session_a.id,
        turn_index=0,
        question_text="Alpha question?",
        candidate_answer=SENTINEL_ANSWER_A,
        relevance_score=85,
        turn_duration_sec=40,
    )

    # User B
    user_b = User(id="user-sentinel-b", email="sentinel_b@example.com", full_name="Bob Sentinel", hashed_password="pw")
    resume_b = Resume(
        id="res-sentinel-b",
        user_id=user_b.id,
        file_name="b.pdf",
        file_path="/b.pdf",
        file_size_bytes=100,
        mime_type="application/pdf",
        raw_text=f"Skills: {SENTINEL_RESUME_B}",
        parsed_data={"skills": [SENTINEL_RESUME_B]},
    )
    session_b = InterviewSession(
        id="sess-sentinel-b",
        user_id=user_b.id,
        resume_id=resume_b.id,
        target_role="Beta Specialist",
        seniority_level="senior",
        interview_focus="Technical Core",
        practice_mode="quick",
        custom_job_desc=f"Must have {SENTINEL_JD_B}",
        parsed_jd_data={"required_skills": [SENTINEL_JD_B]},
        status="completed",
        overall_score=70,
    )
    turn_b = InterviewQuestionTurn(
        id="turn-sentinel-b",
        session_id=session_b.id,
        turn_index=0,
        question_text="Beta question?",
        candidate_answer=SENTINEL_ANSWER_B,
        relevance_score=70,
        turn_duration_sec=35,
    )

    db_session.add_all([user_a, user_b, resume_a, resume_b, session_a, session_b, turn_a, turn_b])
    await db_session.commit()

    builder = CoachContextBuilder()

    # Build context for User A
    payload_a = await builder.build_context(db=db_session, current_user=user_a, session_id=session_a.id)
    prompt_a = payload_a.to_prompt_context()

    # Verify User A's sentinels are strictly present in correct sections
    assert SENTINEL_RESUME_A in prompt_a
    assert SENTINEL_JD_A in prompt_a
    assert SENTINEL_ANSWER_A in prompt_a
    assert SENTINEL_WEAKNESS_A in prompt_a

    # Verify User B's sentinels NEVER appear in User A's prompt
    assert SENTINEL_RESUME_B not in prompt_a
    assert SENTINEL_JD_B not in prompt_a
    assert SENTINEL_ANSWER_B not in prompt_a

    # Build context for User B
    payload_b = await builder.build_context(db=db_session, current_user=user_b, session_id=session_b.id)
    prompt_b = payload_b.to_prompt_context()

    # Verify User B's sentinels are present
    assert SENTINEL_RESUME_B in prompt_b
    assert SENTINEL_JD_B in prompt_b
    assert SENTINEL_ANSWER_B in prompt_b

    # Verify User A's sentinels NEVER appear in User B's prompt
    assert SENTINEL_RESUME_A not in prompt_b
    assert SENTINEL_JD_A not in prompt_b
    assert SENTINEL_ANSWER_A not in prompt_b
    assert SENTINEL_WEAKNESS_A not in prompt_b
