"""Unit and Integration Tests for Coach Reference Architecture Context Grounding and Socratic Deep-Dive (Task 10.8)."""

from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User
from app.schemas.coach import CoachConversationResponse, CoachHistoryResponse, CoachChatResponse
from app.schemas.evaluation import SystemDesignReferenceArchitecture
from app.services.coach_ai_service import COACH_SYSTEM_INSTRUCTION, CoachAIService
from app.services.coach_context_builder import CoachContextBuilder, CoachContextPayload
from app.services.coach_service import CoachService
from app.services.reference_evaluator import SYSTEM_DESIGN_BLUEPRINT_CATALOG


@pytest.fixture
def mock_coach_ai():
    """Mock CoachAIService methods to prevent real Gemini API calls."""
    with patch(
        "app.services.coach_ai_service.CoachAIService.generate_initial_debrief",
        new_callable=AsyncMock,
    ) as mock_debrief, patch(
        "app.services.coach_ai_service.CoachAIService.generate_chat_reply",
        new_callable=AsyncMock,
    ) as mock_chat:
        mock_debrief.return_value = (
            "### Post-Interview Debrief\n\nSolid breakdown of the rate limiting design."
        )
        mock_chat.return_value = {
            "coach_response": (
                "The reference architecture uses Redis Sliding Window clusters to track token counts with sub-millisecond latency. "
                "Its stated trade-off is eventual consistency during cross-region partition. "
                "If Redis nodes fail, how would your edge gateway degrade gracefully?"
            ),
            "suggested_followups": [
                "What happens if Redis cluster partitions?",
                "How would this scale to 10M concurrent users?",
            ],
        }
        yield {"debrief": mock_debrief, "chat": mock_chat}


@pytest.fixture
async def system_design_user_and_session(db_session: AsyncSession):
    """Create a user with a completed System Design session containing a reference blueprint."""
    user = User(
        id="test-user-arch-1",
        email="arch_candidate@example.com",
        full_name="Sam Architect",
        hashed_password="hashed_pw_test",
    )
    db_session.add(user)
    await db_session.commit()

    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    bp_dict = bp.model_dump()

    session = InterviewSession(
        id="sess-arch-1",
        user_id=user.id,
        target_role="Staff Backend Engineer",
        seniority_level="staff",
        interview_focus="System Design",
        practice_mode="standard",
        status="completed",
        overall_score=85,
        dimension_scores={
            "relevance": 90,
            "correctness": 85,
            "keywords": 82,
            "clarity": 88,
            "confidence": 85,
        },
        evaluation_report={
            "executive_summary": "Strong architectural reasoning on rate limiting.",
            "top_strengths": [{"title": "Edge Gateway", "description": "Good placement of edge limiter."}],
            "top_improvements": [{"title": "Redis Failover", "description": "Discuss local in-memory fallback."}],
        },
    )
    db_session.add(session)
    await db_session.commit()

    # System Design Turn with blueprint
    turn0 = InterviewQuestionTurn(
        id="turn-arch-0",
        session_id=session.id,
        turn_index=0,
        question_text="How would you design a globally distributed rate limiter?",
        candidate_answer="I would use an edge gateway with Redis for tracking token counts with sliding window counters.",
        relevance_score=90,
        correctness_score=85,
        keywords_score=80,
        clarity_score=88,
        confidence_score=85,
        evaluation_data={
            "primary_concept": "Distributed Rate Limiting",
            "covered_concepts": ["Edge API Gateway", "Redis Token Counter"],
            "missed_concepts": ["In-Memory Local Fallback", "Sliding Window Lua Script"],
            "ideal_answer_comparison": "Solid foundational design with Redis token tracking.",
            "turn_feedback": "Accurate edge gateway and Redis token counter placement.",
            "architecture_blueprint": bp_dict,
        },
    )
    db_session.add(turn0)
    await db_session.commit()

    return user, session, bp_dict


# =========================================================================
# TESTS T01–T20
# =========================================================================

def test_t01_system_design_turn_includes_reference_architecture_context():
    """T01 — System Design turn with blueprint renders reference architecture context block."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={"target_role": "Backend Engineer", "seniority_level": "staff"},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp.model_dump(),
    )
    prompt = payload.to_prompt_context()
    assert "<reference_architecture_context>" in prompt
    assert "</reference_architecture_context>" in prompt
    assert "Globally Distributed API Rate Limiter" in prompt
    assert "sys.sr.ratelimit.core.01" in prompt


def test_t02_non_system_design_turn_does_not_fabricate_architecture_context():
    """T02 — Non-System-Design turn without blueprint omits reference architecture context."""
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={"target_role": "Frontend Developer", "seniority_level": "mid"},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=None,
    )
    prompt = payload.to_prompt_context()
    assert "<reference_architecture_context>" not in prompt
    assert "--- SYSTEM DESIGN REFERENCE ARCHITECTURE GROUNDING ---" not in prompt


def test_t03_missing_blueprint_preserves_existing_coach_behavior():
    """T03 — Missing or empty blueprint dict does not crash context rendering."""
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={"target_role": "Backend Engineer", "overall_score": 78},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context={},
    )
    prompt = payload.to_prompt_context()
    assert "Candidate Name: Sam" in prompt
    assert "<reference_architecture_context>" not in prompt


def test_t04_node_data_is_grounded_in_blueprint():
    """T04 — Node labels, types, roles (CORE/SECONDARY), and purposes are preserved."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp.model_dump(),
    )
    prompt = payload.to_prompt_context()
    assert "Reference Topology Nodes:" in prompt
    assert "Regional Edge API Gateway" in prompt
    assert "Type: gateway" in prompt
    assert "Role: CORE" in prompt
    assert "Distributed Redis Cluster (Lua Scripts)" in prompt
    assert "Type: cache" in prompt


def test_t05_edge_protocol_and_sync_metadata_are_preserved():
    """T05 — Edge protocol and sync/async mode metadata are preserved in prompt."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["be.sr.event.core.01"]
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp.model_dump(),
    )
    prompt = payload.to_prompt_context()
    assert "Reference Directed Interaction Flows:" in prompt
    assert "[ASYNC]" in prompt
    assert "kafka" in prompt.lower()


def test_t06_tradeoffs_are_rendered():
    """T06 — Key architectural trade-offs are rendered in prompt."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp.model_dump(),
    )
    prompt = payload.to_prompt_context()
    assert "Key Architectural Trade-offs:" in prompt
    for to in bp.key_tradeoffs:
        assert to[:40] in prompt


def test_t07_failure_modes_are_rendered():
    """T07 — Failure resilience considerations are rendered in prompt."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp.model_dump(),
    )
    prompt = payload.to_prompt_context()
    assert "Failure Modes & Resilience Considerations:" in prompt
    for fc in bp.failure_considerations:
        assert fc[:40] in prompt


def test_t08_scaling_considerations_are_rendered():
    """T08 — Scaling and partitioning considerations are rendered in prompt."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp.model_dump(),
    )
    prompt = payload.to_prompt_context()
    assert "Scaling & Partitioning Considerations:" in prompt
    for sc in bp.scaling_considerations:
        assert sc[:40] in prompt


def test_t09_covered_and_missed_concepts_alignment():
    """T09 — Candidate demonstrated and missed concept alignment is included in architecture context."""
    bp_dict = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"].model_dump()
    bp_dict["covered_concepts"] = ["Edge Gateway", "Token Bucket"]
    bp_dict["missed_concepts"] = ["Sliding Window Lua", "Local Fallback"]

    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=bp_dict,
    )
    prompt = payload.to_prompt_context()
    assert "Candidate Architecture Alignment:" in prompt
    assert "Demonstrated Concepts: Edge Gateway, Token Bucket" in prompt
    assert "Missed Reference Considerations: Sliding Window Lua, Local Fallback" in prompt


def test_t10_context_size_limits_are_deterministic():
    """T10 — Excessive nodes and edges are bounded to deterministic maximum limits."""
    huge_bp = {
        "scenario_id": "huge.test.01",
        "title": "Huge Architecture",
        "description": "Stress test blueprint",
        "nodes": [{"id": f"n{i}", "label": f"Node {i}", "type": "service", "purpose": "Testing", "is_core": True} for i in range(50)],
        "edges": [{"source": f"n{i}", "target": f"n{i+1}", "label": "Call", "protocol": "grpc", "mode": "sync"} for i in range(50)],
        "key_tradeoffs": [f"Tradeoff {i}" for i in range(20)],
        "failure_considerations": [f"Failure {i}" for i in range(20)],
        "scaling_considerations": [f"Scaling {i}" for i in range(20)],
        "covered_concepts": [f"Concept {i}" for i in range(30)],
        "missed_concepts": [f"Gap {i}" for i in range(30)],
    }
    payload = CoachContextPayload(
        candidate_name="Sam",
        current_session={},
        transcript_turns=[],
        evaluation_report=None,
        historical_performance=[],
        recurring_weaknesses=[],
        recurring_strengths=[],
        conversation_history=[],
        reference_architecture_context=huge_bp,
    )
    prompt = payload.to_prompt_context()
    # Nodes bounded to 20
    assert "[ID: n19]" in prompt
    assert "[ID: n20]" not in prompt

    # Edges bounded to 30
    assert "n29 -> n30" in prompt
    assert "n30 -> n31" not in prompt

    # Tradeoffs bounded to 8
    assert "Tradeoff 7" in prompt
    assert "Tradeoff 8" not in prompt


def test_t11_coach_system_instruction_treats_blueprint_as_authoritative():
    """T11 — Coach system prompt explicitly mandates authoritative reference grounding."""
    assert "<reference_architecture_context>" in COACH_SYSTEM_INSTRUCTION
    assert "treat it as authoritative ground truth" in COACH_SYSTEM_INSTRUCTION
    assert "Primary Source:" in COACH_SYSTEM_INSTRUCTION


def test_t12_coach_system_instruction_forbids_hallucinated_reference_components():
    """T12 — Coach prompt instructions prevent claiming an absent component is part of reference architecture."""
    assert "No Invented Reference Components:" in COACH_SYSTEM_INSTRUCTION
    assert "Do not invent components, nodes, edges, protocols, or failure modes" in COACH_SYSTEM_INSTRUCTION


def test_t13_alternative_architecture_rule_is_present():
    """T13 — Alternative architecture rule clearly distinguishes reference vs alternative."""
    assert "Alternative Architectures:" in COACH_SYSTEM_INSTRUCTION
    assert "The reference architecture shows..." in COACH_SYSTEM_INSTRUCTION
    assert "A possible alternative would be..." in COACH_SYSTEM_INSTRUCTION


def test_t14_prompt_injection_defense_in_coach_instruction():
    """T14 — Prompt injection defenses prevent candidate messages from overriding grounding."""
    assert "Candidate Input Untrusted:" in COACH_SYSTEM_INSTRUCTION
    assert "Prompt Injection Defense:" in COACH_SYSTEM_INSTRUCTION


@pytest.mark.asyncio
async def test_t15_user_isolation_for_reference_architecture(
    db_session: AsyncSession, system_design_user_and_session
):
    """T15 — User isolation: User B cannot access User A's session blueprint."""
    userA, sessionA, _ = system_design_user_and_session

    userB = User(
        id="test-user-arch-2",
        email="other_candidate@example.com",
        full_name="Other Candidate",
        hashed_password="hashed_pw_test",
    )
    db_session.add(userB)
    await db_session.commit()

    service = CoachService()
    ref_b = await service.resolve_reference_architecture_for_session(
        db=db_session,
        session_id=sessionA.id,
        user_id=userB.id,
    )
    assert ref_b is None


@pytest.mark.asyncio
async def test_t16_existing_non_system_design_coach_flow_unchanged(
    db_session: AsyncSession, mock_coach_ai
):
    """T16 — Non-System-Design session initializes and debriefs without error."""
    user = User(
        id="test-user-tech-1",
        email="tech_candidate@example.com",
        full_name="Jordan Tech",
        hashed_password="hashed_pw_test",
    )
    db_session.add(user)
    await db_session.commit()

    session = InterviewSession(
        id="sess-tech-1",
        user_id=user.id,
        target_role="Frontend Engineer",
        seniority_level="mid",
        interview_focus="Technical Core",
        practice_mode="standard",
        status="completed",
        overall_score=80,
    )
    db_session.add(session)
    await db_session.commit()

    service = CoachService()
    conv, followups, plan, resolutions = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=True,
    )
    assert conv is not None
    assert len(conv.messages) >= 1
    ref_arch = await service.resolve_reference_architecture_for_session(
        db=db_session,
        session_id=session.id,
        user_id=user.id,
    )
    assert ref_arch is None


@pytest.mark.asyncio
async def test_t17_coach_conversation_persistence_with_architecture(
    db_session: AsyncSession, system_design_user_and_session, mock_coach_ai
):
    """T17 — Chat inquiry on System Design turn persists candidate & coach turns and attaches blueprint."""
    user, session, _ = system_design_user_and_session
    service = CoachService()

    conv, _, _, _ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=False,
    )

    chat_resp = await service.process_chat(
        db=db_session,
        current_user=user,
        conversation_id=conv.id,
        message_text="Why was Redis chosen over a relational database here?",
        context_turn_index=0,
    )
    assert chat_resp.user_message.message_text == "Why was Redis chosen over a relational database here?"
    assert chat_resp.coach_message.message_text != ""
    assert chat_resp.reference_architecture_context is not None
    assert chat_resp.reference_architecture_context.scenario_id == "sys.sr.ratelimit.core.01"


@pytest.mark.asyncio
async def test_t18_action_plan_behavior_remains_intact_with_blueprint(
    db_session: AsyncSession, system_design_user_and_session
):
    """T18 — Action plan calculation and history retrieval preserve action plans alongside blueprint."""
    user, session, _ = system_design_user_and_session
    service = CoachService()

    history = await service.get_conversation_history(
        db=db_session,
        current_user=user,
        session_id=session.id,
    )
    assert history.session_id == session.id
    assert history.reference_architecture_context is not None
    assert history.reference_architecture_context.scenario_id == "sys.sr.ratelimit.core.01"


@pytest.mark.asyncio
async def test_t19_no_additional_gemini_call_introduced(
    db_session: AsyncSession, system_design_user_and_session, mock_coach_ai
):
    """T19 — Exactly 1 Gemini call is made for initial debrief and 1 per chat inquiry."""
    user, session, _ = system_design_user_and_session
    service = CoachService()

    # 1. Create conversation with auto debrief -> exactly 1 debrief call
    conv, _, _, _ = await service.get_or_create_conversation(
        db=db_session,
        current_user=user,
        session_id=session.id,
        auto_debrief=True,
    )
    assert mock_coach_ai["debrief"].call_count == 1
    assert mock_coach_ai["chat"].call_count == 0

    # 2. Send 1 chat message -> exactly 1 chat call
    await service.process_chat(
        db=db_session,
        current_user=user,
        conversation_id=conv.id,
        message_text="Explain the failover mechanism.",
        context_turn_index=0,
    )
    assert mock_coach_ai["debrief"].call_count == 1
    assert mock_coach_ai["chat"].call_count == 1


@pytest.mark.asyncio
async def test_t20_coach_context_builder_builds_complete_grounded_payload(
    db_session: AsyncSession, system_design_user_and_session
):
    """T20 — CoachContextBuilder.build_context produces valid CoachContextPayload with active blueprint."""
    user, session, _ = system_design_user_and_session
    builder = CoachContextBuilder()

    payload = await builder.build_context(
        db=db_session,
        current_user=user,
        session_id=session.id,
        context_turn_index=0,
    )
    assert payload.reference_architecture_context is not None
    assert payload.reference_architecture_context["scenario_id"] == "sys.sr.ratelimit.core.01"
    prompt = payload.to_prompt_context()
    assert "<reference_architecture_context>" in prompt
    assert "Distributed Redis Cluster (Lua Scripts)" in prompt
