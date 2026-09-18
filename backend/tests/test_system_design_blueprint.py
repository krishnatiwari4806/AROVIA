"""Unit and Integration Tests for System Design Reference Architecture Blueprints."""

import pytest
from app.schemas.evaluation import (
    ArchitectureEdge,
    ArchitectureNode,
    QuestionReferencePayload,
    SystemDesignReferenceArchitecture,
    TurnEvaluationResponse,
)
from app.services.reference_evaluator import (
    SYSTEM_DESIGN_BLUEPRINT_CATALOG,
    SYSTEM_DESIGN_SCENARIO_ALIASES,
    ReferenceEvaluatorService,
    get_reference_evaluator_service,
    resolve_system_design_blueprint,
)


def test_system_design_catalog_contains_curated_blueprints():
    """Verify that the catalog contains all 8 curated System Design scenarios."""
    expected_keys = [
        "sys.sr.ratelimit.core.01",
        "sys.sr.collab.core.01",
        "be.sr.event.core.01",
        "be.sr.data.core.01",
        "be.sr.ha.core.01",
        "sys.mid.url.core.01",
        "sys.mid.notify.core.01",
        "be.sr.arch.core.01",
    ]
    for key in expected_keys:
        assert key in SYSTEM_DESIGN_BLUEPRINT_CATALOG, f"Missing scenario {key} in catalog"
        bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG[key]
        assert isinstance(bp, SystemDesignReferenceArchitecture)
        assert len(bp.nodes) >= 3, f"{key} has too few nodes"
        assert len(bp.edges) >= 2, f"{key} has too few edges"
        assert len(bp.key_tradeoffs) >= 2, f"{key} has too few key_tradeoffs"
        assert len(bp.failure_considerations) >= 2, f"{key} has too few failure_considerations"
        assert len(bp.scaling_considerations) >= 2, f"{key} has too few scaling_considerations"
        assert bp.title, f"{key} has empty title"
        assert bp.description, f"{key} has empty description"


def test_system_design_node_and_edge_integrity():
    """Verify node and edge IDs match valid references."""
    for key, bp in SYSTEM_DESIGN_BLUEPRINT_CATALOG.items():
        node_ids = {node.id for node in bp.nodes}
        for edge in bp.edges:
            assert edge.source in node_ids, f"Edge source {edge.source} not in nodes of {key}"
            assert edge.target in node_ids, f"Edge target {edge.target} not in nodes of {key}"
            assert edge.mode in ("sync", "async"), f"Invalid edge mode {edge.mode} in {key}"


def test_resolve_blueprint_by_exact_and_alias_id():
    """Verify blueprint resolution by question ID and probe aliases."""
    # Core ID
    bp_rate = resolve_system_design_blueprint(question_id="sys.sr.ratelimit.core.01")
    assert bp_rate is not None
    assert bp_rate.scenario_id == "sys.sr.ratelimit.core.01"

    # Probe alias
    bp_rate_probe = resolve_system_design_blueprint(question_id="sys.sr.ratelimit.probe.01")
    assert bp_rate_probe is not None
    assert bp_rate_probe.scenario_id == "sys.sr.ratelimit.core.01"

    # Outbox probe alias
    bp_event_probe = resolve_system_design_blueprint(question_id="be.sr.event.probe.01")
    assert bp_event_probe is not None
    assert bp_event_probe.scenario_id == "be.sr.event.core.01"


def test_resolve_blueprint_by_keywords():
    """Verify semantic keyword resolution when question_id is missing or custom."""
    bp_collab = resolve_system_design_blueprint(
        question_id=None,
        question_text="How do you handle real-time collaborative editing conflicts in Google Docs using CRDTs?",
        primary_concept="Real-time Systems",
    )
    assert bp_collab is not None
    assert bp_collab.scenario_id == "sys.sr.collab.core.01"

    bp_url = resolve_system_design_blueprint(
        question_id=None,
        question_text="Design a URL shortener service like TinyURL that can handle high throughput Base62 hashes.",
        primary_concept="Key Generation",
    )
    assert bp_url is not None
    assert bp_url.scenario_id == "sys.mid.url.core.01"


def test_resolve_blueprint_returns_none_for_technical_core_and_behavioral():
    """Verify that non-system-design questions return None (graceful hiding)."""
    # Technical Core
    bp_http = resolve_system_design_blueprint(
        question_id="be.jr.api.core.01",
        question_text="What is the difference between PUT and PATCH in REST APIs?",
        primary_concept="HTTP Semantics",
    )
    assert bp_http is None

    # React Hooks
    bp_react = resolve_system_design_blueprint(
        question_id="fe.jr.state.core.01",
        question_text="How does the useEffect dependency array work in React?",
        primary_concept="React Hooks",
    )
    assert bp_react is None

    # Behavioral
    bp_behav = resolve_system_design_blueprint(
        question_id="behav.jr.collab.core.01",
        question_text="Tell me about a time you received constructive feedback on a pull request.",
        primary_concept="Receiving Feedback",
    )
    assert bp_behav is None


def test_reference_evaluator_service_attaches_blueprint():
    """Verify ReferenceEvaluatorService.resolve_reference_for_turn integrates blueprint."""
    svc = get_reference_evaluator_service()

    # System Design turn
    ref_sys = svc.resolve_reference_for_turn(
        question_id="sys.sr.ratelimit.core.01",
        question_text="How would you design a globally distributed rate limiter?",
        primary_concept="Distributed Rate Limiting",
        question_intent="system_design",
    )
    assert ref_sys.architecture_blueprint is not None
    assert ref_sys.architecture_blueprint.scenario_id == "sys.sr.ratelimit.core.01"

    # Technical Core turn
    ref_tech = svc.resolve_reference_for_turn(
        question_id="be.jr.api.core.01",
        question_text="Difference between PUT and PATCH?",
        primary_concept="HTTP Semantics",
        question_intent="core_skill",
    )
    assert ref_tech.architecture_blueprint is None


def test_turn_evaluation_response_schema_roundtrip():
    """Verify TurnEvaluationResponse serializes and deserializes architecture_blueprint."""
    bp = SYSTEM_DESIGN_BLUEPRINT_CATALOG["sys.sr.ratelimit.core.01"]
    resp = TurnEvaluationResponse(
        id="turn-123",
        session_id="session-456",
        turn_index=1,
        question_type="scenario",
        question_text="Design a distributed rate limiter",
        candidate_answer="I would use Redis with sliding window lua scripts and edge gateways.",
        relevance_score=90,
        correctness_score=90,
        keywords_score=85,
        clarity_score=90,
        confidence_score=90,
        turn_score=89,
        covered_concepts=["Sliding window", "Redis Lua"],
        missed_concepts=[],
        architecture_blueprint=bp,
    )
    dumped = resp.model_dump()
    assert dumped["architecture_blueprint"] is not None
    assert dumped["architecture_blueprint"]["scenario_id"] == "sys.sr.ratelimit.core.01"
    assert len(dumped["architecture_blueprint"]["nodes"]) >= 3
