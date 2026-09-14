"""Reference Answers, Expected Concepts, and Evaluation Rubrics Engine.

Provides authoritative, evidence-based reference benchmarks, structured expected concepts
with importance tiers (CORE vs SUPPORTING), and intent-calibrated evaluation rubrics for mock interview turns.
Guarantees zero candidate-answer contamination and strict prompt-injection resistance.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.evaluation import (
    ConceptImportance,
    EvaluationRubric,
    EvidenceCategory,
    ExpectedConcept,
    QuestionReferencePayload,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CURATED DETERMINISTIC EXPECTED CONCEPTS & RUBRICS FOR QUESTION ARTIFACTS
# ---------------------------------------------------------------------------

CURATED_QUESTION_CONCEPTS: Dict[str, List[Tuple[str, ConceptImportance, str]]] = {
    # Relational Database Fundamentals
    "primary key": [
        ("Primary Key Row Uniqueness", ConceptImportance.CORE, "Uniquely identifies each row in a database table."),
        ("Entity Integrity & Uniqueness Constraint", ConceptImportance.CORE, "Enforces database-level entity integrity and prevents duplicate keys."),
        ("Not-Null Constraint Enforcement", ConceptImportance.SUPPORTING, "Columns composing a primary key cannot hold NULL values."),
        ("Foreign Key Reference Target & Indexing", ConceptImportance.SUPPORTING, "Serves as the target for relational foreign keys and default indexing."),
    ],
    # HTTP & REST API Fundamentals
    "http semantics & idempotency": [
        ("Idempotency semantics of PUT", ConceptImportance.CORE, "PUT completely replaces resource representation idempotently."),
        ("Partial update semantics of PATCH", ConceptImportance.CORE, "PATCH modifies specific fields without full resource replacement."),
        ("Payload schema validation", ConceptImportance.SUPPORTING, "Handling optional/missing fields safely with schema validators."),
    ],
    "http get": [
        ("Idempotent & Safe Retrieval", ConceptImportance.CORE, "GET method retrieves resource representation without modifying server state."),
        ("Query Parameter Filtering", ConceptImportance.SUPPORTING, "Passes search and filter parameters via URL query strings."),
    ],
    "hash table complexity": [
        ("Hash table lookup average time complexity is O(1) constant time", ConceptImportance.CORE, "Average time complexity for key lookup in a hash table is O(1) constant time."),
    ],
    "hash table lookup": [
        ("Hash table lookup average time complexity is O(1) constant time", ConceptImportance.CORE, "Average time complexity for key lookup in a hash table is O(1) constant time."),
    ],
    "database transactions & acid": [
        ("ACID Properties (Atomicity, Consistency, Isolation, Durability)", ConceptImportance.CORE, "Guarantees transactional integrity across multiple operations."),
        ("Transaction rollback mechanisms", ConceptImportance.CORE, "Automatic rollback to clean up uncommitted writes upon failure."),
        ("Isolation levels and concurrency anomalies", ConceptImportance.SUPPORTING, "Dirty reads, non-repeatable reads, and phantom read prevention."),
    ],
    "exception handling": [
        ("Runtime Error Interception", ConceptImportance.CORE, "Catches runtime exceptions using try-except or try-catch blocks to prevent crashes."),
        ("Graceful Error Recovery & Logging", ConceptImportance.SUPPORTING, "Logs diagnostic error details and returns safe fallback responses."),
    ],
    "centralized exception handling": [
        ("Global exception middleware", ConceptImportance.CORE, "Intercepting unhandled exceptions uniformly before sending response."),
        ("Information leakage prevention", ConceptImportance.CORE, "Masking raw stack traces, internal paths, and DB schemas from public clients."),
        ("Standard HTTP error response schemas", ConceptImportance.SUPPORTING, "Returning predictable JSON error objects with clear status codes."),
    ],
    "database indexing & query performance": [
        ("B-Tree index structure and lookups", ConceptImportance.CORE, "Logarithmic search time O(log N) on indexed columns."),
        ("Write overhead of indexes", ConceptImportance.CORE, "Every insert/update/delete requires updating index trees."),
        ("Composite index column order (Prefix Rule)", ConceptImportance.SUPPORTING, "Leftmost prefix matching for compound indexes."),
    ],
    "relational schema normalization": [
        ("Eliminating data redundancy", ConceptImportance.CORE, "Decomposing tables to store each fact in exactly one place."),
        ("Preventing update, insert, and delete anomalies", ConceptImportance.CORE, "Avoiding inconsistent states during row updates."),
        ("Normal forms (1NF, 2NF, 3NF)", ConceptImportance.SUPPORTING, "Atomic values, full functional dependency, and transitive dependency removal."),
    ],
    "database normalization": [
        ("Eliminating data redundancy", ConceptImportance.CORE, "Decomposing tables to store each fact in exactly one place."),
        ("Preventing update, insert, and delete anomalies", ConceptImportance.CORE, "Avoiding inconsistent states during row updates."),
        ("Normal forms (1NF, 2NF, 3NF)", ConceptImportance.SUPPORTING, "Atomic values, full functional dependency, and transitive dependency removal."),
    ],
    "asynchronous programming & concurrency": [
        ("Event loop and non-blocking I/O", ConceptImportance.CORE, "Single-threaded event loop delegating I/O without blocking threads."),
        ("Async/await cooperative multitasking", ConceptImportance.CORE, "Yielding control during network/disk wait times."),
        ("CPU-bound vs I/O-bound trade-offs", ConceptImportance.SUPPORTING, "Async is optimal for I/O; CPU-bound tasks require process pools."),
    ],
    "caching strategies & cache invalidation": [
        ("Sub-millisecond in-memory lookups (Redis/Memcached)", ConceptImportance.CORE, "Serving hot reads directly from RAM."),
        ("Cache invalidation patterns (Cache-Aside, Write-Through)", ConceptImportance.CORE, "Strategies for synchronizing cache with persistent store."),
        ("Cache stampede and TTL eviction", ConceptImportance.SUPPORTING, "Preventing thundering herd on cache miss using locks/probabilistic TTL."),
    ],
}


def sanitize_untrusted_text(text: Optional[str]) -> str:
    """Sanitize untrusted candidate, resume, or JD text to prevent prompt injection and delimiter breakout."""
    if not text:
        return ""
    # Strip dangerous instruction injection keywords and control tags
    sanitized = re.sub(
        r"(ignore\s+(all\s+)?previous\s+instructions|system\s+instruction|system\s+prompt|disregard\s+instructions|override\s+evaluation|give\s+100|rate\s+100|---\s*system:)",
        "[REDACTED_INJECTION_ATTEMPT]",
        text,
        flags=re.IGNORECASE,
    )
    # Strip markdown block breakout tags
    sanitized = re.sub(r"```", "'''", sanitized)
    sanitized = re.sub(r"</?[a-zA-Z0-9_-]+>", "", sanitized)
    return sanitized.strip()


def extract_expected_concepts_from_text(
    ideal_answer: str,
    primary_concept: str,
    intent: str = "core_skill",
) -> List[ExpectedConcept]:
    """Deterministically extract structured ExpectedConcept items with CORE and SUPPORTING tiers."""
    concepts: List[ExpectedConcept] = []
    seen_names: Set[str] = set()

    safe_ideal = ideal_answer if isinstance(ideal_answer, str) else ""
    safe_primary = primary_concept if isinstance(primary_concept, str) else ""

    # 1. Check curated registry first
    norm_primary = safe_primary.strip().lower()
    if norm_primary:
        for key, curated_list in CURATED_QUESTION_CONCEPTS.items():
            if key in norm_primary or norm_primary in key:
                for name, imp, desc in curated_list:
                    seen_names.add(name.lower())
                    concepts.append(
                        ExpectedConcept(concept=name, importance=imp, description=desc)
                    )
            if concepts:
                return concepts

    # 2. Deterministically parse clauses from ideal_answer
    if safe_ideal and safe_ideal.strip():
        # Split on sentence boundaries and list markers
        clauses = re.split(r"[.;\n]|,\s*(?:while|whereas|including|such as|and|covering)\s*", safe_ideal)
        for idx, clause in enumerate(clauses):
            c_clean = clause.strip()
            # Must be a substantive phrase (2 to 14 words)
            words = c_clean.split()
            if 2 <= len(words) <= 14:
                # Clean leading prepositions/conjunctions
                c_clean = re.sub(r"^(and|while|whereas|including|such as|using|covering|to|for|with)\s+", "", c_clean, flags=re.IGNORECASE)
                c_clean = c_clean.capitalize()
                if c_clean.lower() not in seen_names and len(c_clean) >= 6:
                    seen_names.add(c_clean.lower())
                    # First 2 parsed clauses are CORE, subsequent are SUPPORTING
                    imp = ConceptImportance.CORE if len(concepts) < 2 else ConceptImportance.SUPPORTING
                    concepts.append(
                        ExpectedConcept(
                            concept=c_clean,
                            importance=imp,
                            description=f"Technical detail: {c_clean}",
                        )
                    )
            if len(concepts) >= 4:
                break

    # 3. Add Primary Concept as CORE if specific and not generic placeholder
    if safe_primary and safe_primary.strip() and safe_primary.strip() not in ("Engineering Competency", "Targeted Probing Analysis"):
        primary_clean = safe_primary.strip()
        if primary_clean.lower() not in seen_names:
            seen_names.add(primary_clean.lower())
            concepts.insert(
                0,
                ExpectedConcept(
                    concept=primary_clean,
                    importance=ConceptImportance.CORE,
                    description=f"Core conceptual understanding of {primary_clean}.",
                ),
            )
    elif not concepts and safe_primary:
        concepts.append(
            ExpectedConcept(
                concept=safe_primary.strip(),
                importance=ConceptImportance.CORE,
                description=f"Core conceptual understanding of {safe_primary.strip()}.",
            )
        )

    return concepts


def build_rubric_for_intent(
    intent: str,
    question_text: str,
    ideal_answer: str,
    primary_concept: str,
    expected_concepts: List[ExpectedConcept],
) -> EvaluationRubric:
    """Construct an intent-calibrated evaluation rubric with clear tier characteristics."""
    norm_intent = (intent or "core_skill").lower().strip()

    if norm_intent in ("resume_project", "project_deep_dive", "project_architecture"):
        return EvaluationRubric(
            question_intent="project_deep_dive",
            expected_knowledge="Architecture breakdown, component boundaries, data flow, candidate ownership, and trade-offs.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Clearly articulates component architecture, data flow, and technology choices.",
                "Demonstrates authentic ownership by explaining implementation decisions, trade-offs, and failure handling.",
                "Explains edge-case handling, performance bottlenecks, and concrete outcomes.",
            ],
            partial_indicators=[
                "Describes high-level tech stack and responsibilities but lacks architectural depth or failure mitigation details.",
                "Mentions the chosen solution without explaining the underlying trade-offs or technical challenges.",
            ],
            weak_indicators=[
                "Provides vague or generic summary with unsubstantiated claims or buzzwords without demonstrable system design understanding or clear individual contribution.",
            ],
            incorrect_indicators=[
                "Misrepresents fundamental technology behaviors or claims technically contradictory implementations.",
            ],
            irrelevant_indicators=[
                "Discusses unrelated projects or technologies not requested in the prompt.",
            ],
        )

    elif norm_intent in ("work_experience", "production_milestone"):
        return EvaluationRubric(
            question_intent="work_experience",
            expected_knowledge="Production engineering capability, incident mitigation, operational metrics, and reliability.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Structures response logically (problem context, technical root-cause, mitigation, and measurable results).",
                "Demonstrates strong production engineering instincts (observability, rollback safety, latency budgets).",
            ],
            partial_indicators=[
                "Explains the problem at a high level but omits concrete technical troubleshooting steps or operational impact.",
            ],
            weak_indicators=[
                "Generic recitation of routine job duties without deep engineering ownership or problem-solving evidence.",
            ],
            incorrect_indicators=[
                "Describes unsafe production practices or factually flawed recovery approaches.",
            ],
            irrelevant_indicators=[
                "Evades the operational challenge question and discusses unrelated topics.",
            ],
        )

    elif norm_intent in ("system_design", "scenario", "practical_scenario"):
        return EvaluationRubric(
            question_intent=norm_intent,
            expected_knowledge="Scalability trade-offs, bottleneck identification, data consistency, caching, and fault isolation.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Employs hypothesis-driven triage, observability, log/metric analysis, and systematic root-cause isolation.",
                "Analyzes horizontal vs vertical scalability, database read/write bottlenecks, and caching invalidation.",
                "Proposes resilient mitigations with clear trade-offs and zero-regression testing.",
            ],
            partial_indicators=[
                "Proposes standard fixes (e.g. 'add more servers' or 'add caching') without analyzing root causes or trade-offs.",
            ],
            weak_indicators=[
                "Guesses random components without structured diagnostic reasoning or architectural justification.",
            ],
            incorrect_indicators=[
                "Proposes architectures that introduce single points of failure, data corruption, or distributed deadlocks.",
            ],
            irrelevant_indicators=[
                "Ignores the scenario constraints and describes unrelated tools.",
            ],
        )

    elif norm_intent in ("behavioral", "leadership", "collaboration"):
        return EvaluationRubric(
            question_intent="behavioral",
            expected_knowledge="Engineering collaboration, conflict resolution, technical ownership, decision reasoning, and reflection.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Articulates clear context, specific personal ownership, decisive constructive actions, and quantifiable impact with mature reflection and growth takeaways.",
                "Demonstrates mature engineering empathy, constructive feedback incorporation, and retrospection.",
            ],
            partial_indicators=[
                "Describes team achievements without clarifying candidate's individual ownership or actions.",
            ],
            weak_indicators=[
                "Vague hypothetical answers rather than concrete lived engineering experiences.",
            ],
            incorrect_indicators=[
                "Exhibits blame-shifting, lack of accountability, or destructive team dynamics.",
            ],
            irrelevant_indicators=[
                "Answers an unrelated prompt.",
            ],
        )

    elif norm_intent in ("follow_up", "probing"):
        return EvaluationRubric(
            question_intent="follow_up",
            expected_knowledge="Specific deep-dive into the concrete mechanism, edge case, or trade-off raised in the probe.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Directly answers the targeted follow-up question with specific technical mechanisms and concrete patterns.",
                "Explains the underlying trade-off, edge case, or failure condition without dodging.",
            ],
            partial_indicators=[
                "Acknowledges the probed area but gives a surface-level response without mechanical depth.",
            ],
            weak_indicators=[
                "Repeats the initial core answer without providing any additional technical detail requested by the probe.",
            ],
            incorrect_indicators=[
                "Provides factually erroneous technical claims regarding the probed mechanism.",
            ],
            irrelevant_indicators=[
                "Pivots away from the follow-up question to an unrelated topic.",
            ],
        )

    else:
        # Default: CORE_SKILL / JD_REQUIREMENT / TECHNICAL_CORE
        return EvaluationRubric(
            question_intent="core_skill",
            expected_knowledge="Deep technical understanding of domain protocols, data structures, algorithms, and production performance patterns.",
            expected_concepts=expected_concepts,
            strong_indicators=[
                "Technically accurate explanation of underlying mechanisms, internals, and execution flows.",
                "Addresses edge cases, performance implications, and practical production constraints.",
                "Concise and direct for factual questions (e.g. HTTP verbs, database types).",
            ],
            partial_indicators=[
                "Identifies main concepts and happy-path usage but omits internal mechanics or edge-case trade-offs.",
            ],
            weak_indicators=[
                "Vague dictionary definition without practical engineering depth or syntax clarity.",
            ],
            incorrect_indicators=[
                "States factually wrong definitions, incorrect algorithmic complexities, or invalid API semantics.",
            ],
            irrelevant_indicators=[
                "Explains a completely different framework, tool, or domain.",
            ],
        )


class ReferenceEvaluatorService:
    """Service governing evaluation reference payloads, expected concepts, and rubrics."""

    def resolve_reference_for_turn(
        self,
        question_text: Optional[str] = None,
        ideal_answer: Optional[str] = None,
        primary_concept: Optional[str] = None,
        question_intent: Optional[str] = None,
        question_id: Optional[str] = None,
        is_follow_up: bool = False,
        is_candidate_specific: bool = False,
        target_role: str = "Software Engineer",
        seniority_level: str = "mid",
        turn: Optional[Any] = None,
        parsed_jd_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
        focus_skills: Optional[List[str]] = None,
    ) -> QuestionReferencePayload:
        """Construct or resolve an authoritative QuestionReferencePayload.
        
        Zero Candidate Contamination: candidate_answer is NEVER accepted or used in reference generation.
        """
        # Handle case where turn object is passed as first positional argument
        if turn is None and question_text is not None and not isinstance(question_text, str) and hasattr(question_text, "question_text"):
            turn = question_text
            question_text = None

        if turn is not None:
            raw_q = getattr(turn, "question_text", "")
            if isinstance(raw_q, str) and raw_q.strip():
                question_text = question_text or raw_q

            raw_ia = getattr(turn, "ideal_answer", None)
            if isinstance(raw_ia, str) and raw_ia.strip():
                ideal_answer = ideal_answer or raw_ia

            raw_pc = getattr(turn, "primary_concept", None)
            if isinstance(raw_pc, str) and raw_pc.strip():
                primary_concept = primary_concept or raw_pc

            if getattr(turn, "question_type", None) == "follow_up":
                is_follow_up = True
            
            q_meta = getattr(turn, "question_metadata", None) or {}
            if isinstance(q_meta, dict):
                if not question_intent:
                    q_int = q_meta.get("question_intent") or q_meta.get("intent")
                    if isinstance(q_int, str) and q_int.strip():
                        question_intent = q_int
                if not primary_concept:
                    p_c = q_meta.get("primary_concept") or q_meta.get("competency")
                    if isinstance(p_c, str) and p_c.strip():
                        primary_concept = p_c
                if not ideal_answer:
                    i_a = q_meta.get("ideal_answer") or q_meta.get("reference_answer")
                    if isinstance(i_a, str) and i_a.strip():
                        ideal_answer = i_a
                if q_meta.get("is_candidate_specific"):
                    is_candidate_specific = True

            if not is_candidate_specific:
                ctx_id = getattr(turn, "context_item_id", None)
                if isinstance(ctx_id, str) and ctx_id.strip():
                    is_candidate_specific = True

        safe_q_str = question_text if isinstance(question_text, str) else ""
        clean_q = sanitize_untrusted_text(safe_q_str) or "Technical interview question."
        safe_intent_str = question_intent if isinstance(question_intent, str) else ""
        intent = "follow_up" if is_follow_up else (safe_intent_str or "core_skill")

        # Baseline reference answer
        safe_ia_str = ideal_answer if isinstance(ideal_answer, str) else ""
        ref_ans = (
            safe_ia_str.strip()
            if safe_ia_str and safe_ia_str.strip()
            else f"Senior-level benchmark response for {clean_q} covering core technical principles, architectural trade-offs, and failure handling."
        )

        safe_pc_str = primary_concept if isinstance(primary_concept, str) else ""
        prim_concept = (
            safe_pc_str.strip()
            if safe_pc_str and safe_pc_str.strip()
            else ("Targeted Probing Analysis" if is_follow_up else "Engineering Competency")
        )

        expected_concepts = extract_expected_concepts_from_text(
            ideal_answer=ref_ans,
            primary_concept=prim_concept,
            intent=intent,
        )

        rubric = build_rubric_for_intent(
            intent=intent,
            question_text=clean_q,
            ideal_answer=ref_ans,
            primary_concept=prim_concept,
            expected_concepts=expected_concepts,
        )

        source = "question_bank" if question_id else (
            "planner_archetype" if is_candidate_specific else "curated_deterministic"
        )

        return QuestionReferencePayload(
            question_id=question_id,
            question_text=clean_q,
            question_intent=intent,
            reference_answer=ref_ans,
            primary_concept=prim_concept,
            expected_concepts=expected_concepts,
            rubric=rubric,
            source=source,
            is_candidate_specific=is_candidate_specific,
        )


def get_reference_evaluator_service() -> ReferenceEvaluatorService:
    """Dependency provider for ReferenceEvaluatorService."""
    return ReferenceEvaluatorService()
