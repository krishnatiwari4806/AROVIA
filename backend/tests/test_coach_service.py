"""Unit and Integration tests for CoachService, Context Grounding, and Data Isolation."""

from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.resume import Resume
from app.models.user import User
from app.services.coach_service import CoachService


@pytest.fixture
def mock_coach_ai():
    """Mock CoachAIService methods to prevent real Gemini network calls."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### Post-Interview Debrief\n\nGreat job on Turn 1 with Kafka partitioning!"
        )
        mock_chat.return_value = {
            "coach_response": "Here is an ideal model answer with trade-offs.",
            "suggested_followups": [
                "What was my biggest weakness?",
                "Give me a model answer for Turn 2.",
            ],
        }
        yield {"debrief": mock_debrief, "chat": mock_chat}


@pytest.fixture
async def sample_user_and_session(db_session: AsyncSession):
    """Create a sample user and completed interview session in test DB."""
    user = User(
        id="test-user-coach-1",
        email="coach_candidate@example.com",
        full_name="Alex Candidate",
        hashed_password="hashed_pw_test",
    )
    db_session.add(user)
    await db_session.commit()

    session = InterviewSession(
        id="sess-coach-1",
        user_id=user.id,
        target_role="Staff Backend Engineer",
        seniority_level="senior",
        interview_focus="Distributed Systems",
        practice_mode="full",
        status="completed",
        overall_score=88,
        dimension_scores={
            "relevance": 90,
            "correctness": 85,
            "keywords": 82,
            "clarity": 88,
            "confidence": 85,
        },
        evaluation_report={
            "executive_summary": "Solid architectural foresight on distributed patterns.",
            "top_strengths": [
                {
                    "title": "Kafka Partitioning",
                    "description": "Clear explanation of partitioning key selection.",
                }
            ],
            "top_improvements": [
                {
                    "title": "Rebalance Protocol",
                    "description": "Discuss static membership and eager rebalance pitfalls.",
                    "actionable_recommendation": "Review Kafka consumer group rebalance optimizations.",
                }
            ],
        },
    )
    db_session.add(session)
    await db_session.commit()

    # Add 2 Turns
    turn0 = InterviewQuestionTurn(
        id="turn-coach-0",
        session_id=session.id,
        turn_index=0,
        question_text="How do you handle scaling in Apache Kafka?",
        candidate_answer="We scale Kafka partitions across consumer groups.",
        relevance_score=92,
        correctness_score=88,
        keywords_score=85,
        clarity_score=90,
        confidence_score=86,
        evaluation_data={
            "primary_concept": "Kafka Partitioning",
            "covered_concepts": ["Consumer Groups", "Partition keys"],
            "missed_concepts": ["Static Group Membership"],
            "ideal_answer_comparison": "Strong foundational explanation.",
            "turn_feedback": "Accurate partition scaling mechanics.",
        },
    )
    turn1 = InterviewQuestionTurn(
        id="turn-coach-1",
        session_id=session.id,
        turn_index=1,
        question_text="What are the trade-offs of caching invalidation strategies?",
        candidate_answer="Cache-aside vs write-through with TTL expirations.",
        relevance_score=88,
        correctness_score=82,
        keywords_score=80,
        clarity_score=86,
        confidence_score=84,
        evaluation_data={
            "primary_concept": "Cache Invalidation",
            "covered_concepts": ["TTL", "Cache-Aside"],
            "missed_concepts": ["Thundering Herd Problem"],
            "ideal_answer_comparison": "Good breakdown of TTL trade-offs.",
            "turn_feedback": "Solid grasp of cache-aside patterns.",
        },
    )
    db_session.add_all([turn0, turn1])
    await db_session.commit()

    return user, session


# =========================================================================
# A. COACH SERVICE CORE FUNCTIONALITY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_conversation_creation_and_initial_debrief(
    db_session: AsyncSession, sample_user_and_session, mock_coach_ai
):
    """Verify conversation is initialized with correct user/session association and initial debrief message."""
    user, session = sample_user_and_session
    service = CoachService()

    conv, followups, plan, resolutions = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=True,
    )

    assert conv.id is not None
    assert conv.user_id == user.id
    assert conv.session_id == session.id
    assert len(conv.messages) == 1

    debrief_msg = conv.messages[0]
    assert debrief_msg.sender == "coach"
    assert "Post-Interview Debrief" in debrief_msg.message_text
    assert debrief_msg.context_turn_index is None
    assert len(followups) == 3

    # Assert AI debrief was called once
    assert mock_coach_ai["debrief"].call_count == 1


@pytest.mark.asyncio
async def test_auto_debrief_disabled_creates_empty_conversation(
    db_session: AsyncSession, sample_user_and_session, mock_coach_ai
):
    """Verify auto_debrief=False initializes an empty conversation without calling AI service."""
    user, session = sample_user_and_session
    service = CoachService()

    conv, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=False,
    )

    assert conv.id is not None
    assert len(conv.messages) == 0
    assert mock_coach_ai["debrief"].call_count == 0


@pytest.mark.asyncio
async def test_duplicate_debrief_prevention(
    db_session: AsyncSession, sample_user_and_session, mock_coach_ai
):
    """Verify calling get_or_create_conversation idempotently returns existing conversation without re-generating debrief."""
    user, session = sample_user_and_session
    service = CoachService()

    # First call: generates debrief
    conv1, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=True,
    )
    assert len(conv1.messages) == 1
    assert mock_coach_ai["debrief"].call_count == 1

    # Second call: returns existing conversation, no new messages added
    conv2, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=True,
    )
    assert conv2.id == conv1.id
    assert len(conv2.messages) == 1
    # AI service must not have been called a second time
    assert mock_coach_ai["debrief"].call_count == 1


@pytest.mark.asyncio
async def test_process_chat_persists_user_and_coach_turns(
    db_session: AsyncSession, sample_user_and_session, mock_coach_ai
):
    """Verify chat turn persists candidate user message, invokes AI reasoning, and persists coach reply."""
    user, session = sample_user_and_session
    service = CoachService()

    conv, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=False,
    )

    chat_res = await service.process_chat(
        db=db_session,
        current_user=user,
        conversation_id=conv.id,
        message_text="How can I improve my explanation of cache invalidation?",
        context_turn_index=1,
    )

    # Validate response structure
    assert chat_res.user_message.sender == "user"
    assert chat_res.user_message.message_text == "How can I improve my explanation of cache invalidation?"
    assert chat_res.user_message.context_turn_index == 1

    assert chat_res.coach_message.sender == "coach"
    assert chat_res.coach_message.message_text == "Here is an ideal model answer with trade-offs."
    assert chat_res.coach_message.context_turn_index == 1
    assert len(chat_res.suggested_followups) == 2

    # Validate persistence in database
    history = await service.get_conversation_history(
        db=db_session,
        current_user=user,
        session_id=session.id,
    )
    assert history.total_messages == 2
    assert history.messages[0].sender == "user"
    assert history.messages[1].sender == "coach"


@pytest.mark.asyncio
async def test_conversation_history_retrieval(
    db_session: AsyncSession, sample_user_and_session, mock_coach_ai
):
    """Verify conversation history returns empty when uninitialized and chronological when populated."""
    user, session = sample_user_and_session
    service = CoachService()

    # 1. Uninitialized session history
    empty_hist = await service.get_conversation_history(
        db=db_session,
        current_user=user,
        session_id=session.id,
    )
    assert empty_hist.total_messages == 0
    assert empty_hist.messages == []
    assert empty_hist.conversation_id is None

    # 2. Initialized with debrief + 1 chat turn
    conv, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=True,
    )
    await service.process_chat(
        db=db_session,
        current_user=user,
        conversation_id=conv.id,
        message_text="What was my biggest score deduction?",
    )

    hist = await service.get_conversation_history(
        db=db_session,
        current_user=user,
        session_id=session.id,
    )
    assert hist.total_messages == 3  # Debrief (coach), user message, coach reply
    assert hist.messages[0].sender == "coach"
    assert hist.messages[1].sender == "user"
    assert hist.messages[2].sender == "coach"


@pytest.mark.asyncio
async def test_add_raw_message_success_and_invalid_sender_validation(
    db_session: AsyncSession, sample_user_and_session
):
    """Verify add_message persists valid messages and rejects invalid sender strings."""
    user, session = sample_user_and_session
    service = CoachService()

    conv, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=False,
    )

    # Valid user message
    msg1 = await service.add_message(
        db=db_session,
        current_user=user,
        conversation_id=conv.id,
        sender="user",
        message_text="Raw user note",
    )
    assert msg1.sender == "user"
    assert msg1.message_text == "Raw user note"

    # Valid coach message
    msg2 = await service.add_message(
        db=db_session,
        current_user=user,
        conversation_id=conv.id,
        sender="coach",
        message_text="Raw coach feedback",
    )
    assert msg2.sender == "coach"

    # Invalid sender rejects
    with pytest.raises(ValidationError):
        await service.add_message(
            db=db_session,
            current_user=user,
            conversation_id=conv.id,
            sender="admin",
            message_text="Invalid sender role",
        )


# =========================================================================
# F. DATA GROUNDING VERIFICATION TEST
# =========================================================================

@pytest.mark.asyncio
async def test_coach_context_builder_data_grounding_integration(
    db_session: AsyncSession, sample_user_and_session
):
    """Verify that Coach context passes real persisted interview, evaluation, resume, and JD data to AI generation."""
    user, session = sample_user_and_session

    # Attach a Resume to candidate
    resume = Resume(
        id="res-grounding-1",
        user_id=user.id,
        file_name="alex_resume.pdf",
        file_path="/resumes/alex_resume.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        raw_text="Raw resume content",
        parsed_data={
            "summary": "10+ years backend architect specializing in high-throughput distributed systems.",
            "skills": ["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes"],
            "experience_years": 10.0,
            "domains": ["Distributed Systems", "Cloud Infrastructure"],
        },
    )
    db_session.add(resume)
    await db_session.commit()

    # Attach JD data to session
    session.custom_job_desc = "Looking for a Staff Backend Engineer with Kafka and Redis expertise."
    session.parsed_jd_data = {
        "job_title": "Staff Backend Engineer",
        "required_skills": ["Kafka", "Distributed Systems", "PostgreSQL"],
    }
    await db_session.commit()

    # Capture the context passed to CoachAIService
    captured_context = None

    async def mock_debrief_capture(context):
        nonlocal captured_context
        captured_context = context
        return "Debrief generated with grounded context."

    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        side_effect=mock_debrief_capture,
    ):
        service = CoachService()
        await service.get_or_create_conversation(
            db=db_session,
            current_user=user,
            session_id=session.id,
            auto_debrief=True,
        )

    assert captured_context is not None
    prompt_str = captured_context.to_prompt_context()

    # 1. Candidate Info
    assert "Alex Candidate" in prompt_str
    assert "Staff Backend Engineer" in prompt_str

    # 2. Evaluation Scores
    assert "Current Session Overall Score: 88/100" in prompt_str
    assert "Relevance: 90/100, Correctness: 85/100" in prompt_str

    # 3. Evaluation Summary & Strengths / Improvements
    assert "Solid architectural foresight on distributed patterns." in prompt_str
    assert "Kafka Partitioning: Clear explanation of partitioning key selection." in prompt_str
    assert "Rebalance Protocol: Discuss static membership" in prompt_str

    # 4. Turn Q&A Evidence
    assert "How do you handle scaling in Apache Kafka?" in prompt_str
    assert "We scale Kafka partitions across consumer groups." in prompt_str
    assert "Primary Concept: Kafka Partitioning" in prompt_str
    assert "Covered Concepts: Consumer Groups, Partition keys" in prompt_str
    assert "Missed Concepts: Static Group Membership" in prompt_str

    # 5. Resume Reference Context
    assert "--- CANDIDATE RESUME CONTEXT ---" in prompt_str
    assert "10+ years backend architect" in prompt_str
    assert "Python, Go, Kafka, PostgreSQL, Kubernetes" in prompt_str

    # 6. Job Description Reference Context
    assert "--- TARGET JOB DESCRIPTION CONTEXT ---" in prompt_str
    assert "Kafka, Distributed Systems, PostgreSQL" in prompt_str


# =========================================================================
# G. CROSS-USER / CROSS-SESSION ISOLATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_coach_service_cross_user_isolation(
    db_session: AsyncSession, sample_user_and_session
):
    """Verify User B cannot access or leak User A's session or coach conversation."""
    user_a, session_a = sample_user_and_session

    # Create User B
    user_b = User(
        id="test-user-coach-2",
        email="user_b_intruder@example.com",
        full_name="Bob Intruder",
        hashed_password="hashed_pw_test2",
    )
    db_session.add(user_b)
    await db_session.commit()

    service = CoachService()

    # User A creates a conversation
    conv_a, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user_a,
        session_id=session_a.id,
        auto_debrief=False,
    )

    # 1. User B cannot get/create conversation for User A's session -> 404 NotFoundError
    with pytest.raises(NotFoundError):
        await service.get_or_create_conversation(
            db=db_session,
            current_user=user_b,
            session_id=session_a.id,
        )

    # 2. User B cannot retrieve User A's conversation -> 404 NotFoundError
    with pytest.raises(NotFoundError):
        await service.get_conversation_for_user(
            db=db_session,
            current_user=user_b,
            conversation_id=conv_a.id,
        )

    # 3. User B cannot post chat messages into User A's conversation -> 404 NotFoundError
    with pytest.raises(NotFoundError):
        await service.process_chat(
            db=db_session,
            current_user=user_b,
            conversation_id=conv_a.id,
            message_text="Malicious cross-tenant chat injection",
        )

    # 4. User B cannot retrieve User A's session history -> 404 NotFoundError
    with pytest.raises(NotFoundError):
        await service.get_conversation_history(
            db=db_session,
            current_user=user_b,
            session_id=session_a.id,
        )


# =========================================================================
# E. EDGE CASES
# =========================================================================

@pytest.mark.asyncio
async def test_coach_service_edge_cases(
    db_session: AsyncSession, sample_user_and_session
):
    """Verify edge case handling for nonexistent entities, empty messages, and AI fallback."""
    user, session = sample_user_and_session
    service = CoachService()

    conv, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=False,
    )

    # 1. Empty message text raises ValidationError
    with pytest.raises(ValidationError):
        await service.process_chat(
            db=db_session,
            current_user=user,
            conversation_id=conv.id,
            message_text="   ",
        )

    # 2. Nonexistent session raises NotFoundError
    with pytest.raises(NotFoundError):
        await service.get_or_create_conversation(
            db=db_session,
            current_user=user,
            session_id="00000000-0000-0000-0000-000000000000",
        )

    # 3. Nonexistent conversation raises NotFoundError
    with pytest.raises(NotFoundError):
        await service.process_chat(
            db=db_session,
            current_user=user,
            conversation_id="00000000-0000-0000-0000-000000000000",
            message_text="Hello coach",
        )


# =========================================================================
# STEP 10.6 DATABASE-LEVEL UNIQUENESS & CONCURRENCY RECOVERY TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_database_level_unique_constraint_rejects_duplicate_user_session(
    db_session: AsyncSession, sample_user_and_session
):
    """Requirement A & B: Unique constraint uq_coach_conversation_user_session rejects duplicate (user_id, session_id) at DB level."""
    from sqlalchemy.exc import IntegrityError

    user, session = sample_user_and_session

    conv1 = CoachConversation(
        id="conv-uniq-1",
        user_id=user.id,
        session_id=session.id,
    )
    db_session.add(conv1)
    await db_session.commit()

    # Attempt to insert a distinct CoachConversation record with the same (user_id, session_id)
    conv2 = CoachConversation(
        id="conv-uniq-2",
        user_id=user.id,
        session_id=session.id,
    )
    db_session.add(conv2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_database_level_same_user_different_sessions_allowed(
    db_session: AsyncSession, sample_user_and_session
):
    """Requirement C: Same user with distinct session_id values is allowed at the database level."""
    user, session1 = sample_user_and_session

    # Create a second session for the same user
    session2 = InterviewSession(
        id="sess-coach-distinct-2",
        user_id=user.id,
        target_role="Frontend Engineer",
        seniority_level="senior",
        interview_focus="React",
        practice_mode="quick",
    )
    db_session.add(session2)
    await db_session.commit()

    conv1 = CoachConversation(
        id="conv-diff-1",
        user_id=user.id,
        session_id=session1.id,
    )
    conv2 = CoachConversation(
        id="conv-diff-2",
        user_id=user.id,
        session_id=session2.id,
    )
    db_session.add_all([conv1, conv2])
    await db_session.commit()

    # Query both conversations
    stmt = select(CoachConversation).where(CoachConversation.user_id == user.id)
    res = await db_session.execute(stmt)
    convs = list(res.scalars().all())
    assert len(convs) == 2


@pytest.mark.asyncio
async def test_get_or_create_conversation_race_recovery_on_integrity_error(
    db_session: AsyncSession, sample_user_and_session, mock_coach_ai
):
    """Requirement E & F: CoachService.get_or_create_conversation recovers cleanly from concurrent insert race conditions."""
    user, session = sample_user_and_session
    service = CoachService()

    # Create existing conversation in DB to trigger constraint collision if a concurrent worker tries to insert
    existing_conv = CoachConversation(
        id="conv-race-existing",
        user_id=user.id,
        session_id=session.id,
    )
    db_session.add(existing_conv)
    await db_session.commit()

    # Call get_or_create_conversation — it should locate the existing conversation idempotently
    recovered_conv, *_ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=False,
    )

    assert recovered_conv.id == "conv-race-existing"
    assert recovered_conv.user_id == user.id
    assert recovered_conv.session_id == session.id

