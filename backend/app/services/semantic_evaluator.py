"""Semantic Evaluation Engine — Relevance, Technical Correctness & Concept Coverage.

Provides deterministic and explainable semantic analysis of candidate answers
against authoritative reference answers, expected concepts, and intent-calibrated rubrics.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.evaluation import (
    AnswerQualityTier,
    CompletenessLevel,
    ConceptEvidence,
    ConceptImportance,
    EvidenceCategory,
    ExpectedConcept,
    QuestionReferencePayload,
    SemanticEvaluationResult,
)
from app.services.answer_classifier import (
    classify_answer_deterministically,
    is_short_valid_answer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Multilingual & Technical Keyword Normalization Lexicon
# ---------------------------------------------------------------------------

MULTILINGUAL_CONCEPT_MAP: Dict[str, List[str]] = {
    "uniqueness": [
        "uniquely", "unique", "uniqueness", "row uniquely", "record uniquely",
        "har row ko uniquely", "unique identify", "pehchan", "ek ek row", "alag alag",
    ],
    "redundancy": [
        "redundancy", "duplicate", "duplication", "duplicate data", "repeat",
        "redundant", "data duplicate", "duplicate hatata", "duplicate remove",
    ],
    "anomaly": [
        "anomaly", "anomalies", "update anomaly", "delete anomaly", "insert anomaly",
        "inconsistency", "data corruption", "galat update", "inconsistent state",
    ],
    "idempotent": [
        "idempotent", "idempotency", "same result", "multiple times", "no side effects",
        "kitni baar bhi call", "same state", "repeat call",
    ],
    "http_methods": [
        "get", "put", "post", "patch", "delete", "head", "options",
    ],
    "exception": [
        "exception", "try-except", "try except", "try catch", "try-catch",
        "error handle", "error handling", "crash prevent", "intercept", "error aaye toh",
    ],
    "indexing": [
        "index", "indexing", "b-tree", "btree", "binary tree", "lookup",
        "faster lookup", "query speed", "fast retrieve", "jaldi search", "search tree",
    ],
    "caching": [
        "cache", "caching", "redis", "memcached", "in-memory", "ram lookup",
        "cache aside", "write through", "fast serve", "hit ratio",
    ],
    "concurrency": [
        "async", "await", "coroutine", "event loop", "non-blocking", "multithreading",
        "race condition", "mutex", "lock", "concurrency", "pool", "pooling", "connection pool",
    ],
    "observability": [
        "metrics", "logs", "traces", "tracing", "grafana", "prometheus", "opentelemetry",
        "apm", "latency", "dashboard", "alert", "cpu spike", "bottleneck", "profiling",
    ],
    "conflict_resolution": [
        "conflict", "disagreement", "disagree", "debate", "differing", "clash",
        "argument", "opposing", "difference of opinion", "matbhed",
    ],
    "data_driven": [
        "benchmark", "benchmarking", "benchmarked", "metric", "metrics", "data",
        "prototype", "latency", "measurement", "test", "load test", "proof of concept",
    ],
    "collaboration": [
        "resolution", "resolve", "resolved", "collaborative", "collaboration",
        "consensus", "agreed", "agreement", "aligned", "alignment", "settled",
    ],
    "resilience": [
        "circuit breaker", "fallback", "retry", "retries", "exponential backoff",
        "jitter", "rate limit", "throttling", "bulkhead",
    ],
    "batching": [
        "batch", "batching", "batched", "bulk", "bulk insert", "bulk inserts", "batched inserts", "chunks",
    ],
    "saga": [
        "saga", "sagas", "saga pattern", "choreography", "orchestration", "compensating transaction", "compensating transactions",
    ],
}

STOP_WORDS = {
    "in", "on", "at", "to", "is", "of", "an", "or", "as", "by", "if", "so", "be", "do",
    "we", "my", "he", "it", "no", "up", "the", "and", "for", "with", "that", "this",
    "from", "when", "into", "using", "such", "than", "then", "pattern", "patterns",
    "mechanism", "mechanisms", "principles", "principle", "handling", "structure",
}

CONTRADICTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"(primary key|pk).*(allows?|permit|permits?|accepts?|can have|can contain).*(duplicate|duplicates|null|nulls)", re.IGNORECASE),
        "Claim that primary key allows duplicate or null values contradicts relational integrity constraints.",
    ),
    (
        re.compile(r"(put).*(never|not|isn'?t|cannot be|is not).*(idempotent)", re.IGNORECASE),
        "Claim that HTTP PUT is not idempotent contradicts RFC 9110 HTTP semantics.",
    ),
    (
        re.compile(r"(index|indexing).*(makes?|accelerates?|speeds? up).*(write|insert|update|delete).*faster", re.IGNORECASE),
        "Claim that database indexes accelerate write/insert operations contradicts index tree update overhead.",
    ),
    (
        re.compile(r"(normalization).*(increases?|creates?|adds?|causes?).*(redundancy|duplicate|duplicates)", re.IGNORECASE),
        "Claim that normalization increases redundancy contradicts database normalization principles.",
    ),
    (
        re.compile(r"(get|http get).*(modifi|chang|updat|delet|creat|mutat|drop|destroy|is used to (delete|mutate|modify|change|update|create|drop|destroy)).*(database|server state|resource|table|records?|data)", re.IGNORECASE),
        "Claim that GET request mutates server state contradicts safe/idempotent HTTP retrieval semantics.",
    ),
]


def _normalize_text_for_matching(text: str) -> str:
    """Normalize text by lowering, removing punctuation, and standardizing whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


COMMON_NON_TECHNICAL_WORDS = {
    "data", "fast", "help", "helps", "make", "makes", "used", "uses",
    "work", "works", "good", "call", "calls", "test", "time", "take", "need",
}


def _is_concept_supported_in_text(concept: ExpectedConcept, answer_text: str) -> Tuple[bool, Optional[str]]:
    """Determine whether an expected concept is semantically demonstrated in candidate answer."""
    norm_ans = _normalize_text_for_matching(answer_text)
    if not norm_ans:
        return False, None

    concept_name = concept.concept
    norm_concept = _normalize_text_for_matching(concept_name)
    concept_words = norm_concept.split()
    ans_words = norm_ans.split()

    # 1. Exact phrase match
    if norm_concept in norm_ans:
        return True, concept_name

    # 2. Short valid answer direct concept entity match (e.g., candidate answered "GET", concept is "HTTP GET", "O(1)")
    if is_short_valid_answer(answer_text):
        if norm_ans and (norm_ans == norm_concept or f" {norm_ans} " in f" {norm_concept} " or f" {norm_concept} " in f" {norm_ans} "):
            return True, concept_name
        for syn_list in MULTILINGUAL_CONCEPT_MAP.values():
            if any(syn == norm_ans for syn in syn_list) and any(syn in norm_concept for syn in syn_list):
                return True, concept_name

    # 3. Compound concept sub-clause matching (e.g. "Exponential backoff, circuit breaker", "Saga pattern with compensating transactions")
    sub_clauses = [p.strip() for p in re.split(r"[,;/|]+|\b(?:with|using|for|via)\b", concept_name, flags=re.IGNORECASE) if p.strip()]
    if len(sub_clauses) > 1:
        for clause in sub_clauses:
            norm_clause = _normalize_text_for_matching(clause)
            if norm_clause and norm_clause in norm_ans:
                return True, clause
            clause_sig = [w for w in norm_clause.split() if len(w) >= 3 and w not in STOP_WORDS and w not in COMMON_NON_TECHNICAL_WORDS]
            if clause_sig:
                matches = [
                    w for w in clause_sig
                    if any((w == aw or (len(w) >= 4 and len(aw) >= 4 and aw not in COMMON_NON_TECHNICAL_WORDS and (w.startswith(aw[:4]) or aw.startswith(w[:4])))) for aw in ans_words)
                ]
                threshold = len(clause_sig) if len(clause_sig) <= 2 else max(2, len(clause_sig) - 1)
                if len(matches) >= threshold:
                    return True, clause

    # 4. Check multilingual & semantic synonym mappings
    for group_key, synonyms in MULTILINGUAL_CONCEPT_MAP.items():
        # If this expected concept relates to the group
        if any(syn in norm_concept for syn in synonyms):
            for syn in synonyms:
                if syn in norm_ans:
                    return True, syn
                syn_words = syn.split()
                if len(syn_words) == 1 and len(syn) >= 4 and syn not in COMMON_NON_TECHNICAL_WORDS:
                    # Single word synonym stemming match
                    if any((aw == syn or (len(aw) >= 4 and aw not in COMMON_NON_TECHNICAL_WORDS and (aw.startswith(syn[:4]) or syn.startswith(aw[:4])))) for aw in ans_words):
                        return True, syn
                elif len(syn_words) > 1:
                    # Multi-word phrase must have all non-stop words present
                    sig_syn = [w for w in syn_words if w not in STOP_WORDS and w not in COMMON_NON_TECHNICAL_WORDS]
                    if sig_syn and all(w in ans_words for w in sig_syn):
                        return True, syn

    # 5. Keyword & Stem overlap match
    sig_words = [w for w in concept_words if len(w) >= 3 and w not in STOP_WORDS and w not in COMMON_NON_TECHNICAL_WORDS]
    if sig_words:
        matches = []
        for w in sig_words:
            if w in ans_words:
                matches.append(w)
            elif len(w) >= 4 and any((len(aw) >= 4 and aw not in COMMON_NON_TECHNICAL_WORDS and (aw.startswith(w[:4]) or w.startswith(aw[:4]))) for aw in ans_words):
                matches.append(w)

        threshold = len(sig_words) if len(sig_words) <= 2 else max(2, len(sig_words) - 1)
        if len(matches) >= threshold:
            return True, " ".join(matches)

    return False, None


def _detect_contradictions_in_text(answer_text: str) -> List[str]:
    """Identify explicit factual or conceptual contradictions in candidate answer."""
    contradictions = []
    for pattern, explanation in CONTRADICTION_PATTERNS:
        if pattern.search(answer_text):
            contradictions.append(explanation)
    return contradictions


def _detect_unsupported_claims_in_text(answer_text: str, is_candidate_specific: bool = False) -> List[str]:
    """Identify unverified empirical claims (e.g. ungrounded benchmark percentages)."""
    unsupported = []
    # Match empirical claims like "improved by 90%", "handled 10 million QPS" when not verified
    perc_match = re.search(r"(\b\d{2,3}%\b|\b\d+\s*(?:million|m|k)\s*(?:qps|tps|users)\b)", answer_text, re.IGNORECASE)
    if perc_match and not is_candidate_specific:
        unsupported.append(f"Empirical metric '{perc_match.group(0)}' is unverified from baseline reference.")
    return unsupported


def _determine_semantic_relevance(
    candidate_answer: str,
    question_text: str,
    reference_payload: QuestionReferencePayload,
) -> Tuple[bool, str]:
    """Assess whether candidate response directly and substantively addresses the question prompt."""
    norm_ans = _normalize_text_for_matching(candidate_answer)
    norm_q = _normalize_text_for_matching(question_text)
    norm_ref = _normalize_text_for_matching(reference_payload.reference_answer)

    if not norm_ans:
        return False, "Answer is empty."

    # 1. Prompt Injection & Adversarial Bypass Detection
    injection_patterns = [
        r"ignore (all )?(previous|above) instructions",
        r"give (score|me) 100",
        r"disregard (all )?instructions",
        r"system prompt",
        r"act as (an? )?ai evaluator",
        r"output 100/100",
        r"you must rate this (strong|100)",
    ]
    if any(re.search(pat, candidate_answer, re.IGNORECASE) for pat in injection_patterns):
        return False, "Response contains prompt injection instructions rather than genuine candidate answer."

    # 2. Short valid responses like "GET." or "O(1)"
    if is_short_valid_answer(candidate_answer):
        return True, "Concise factual answer directly targeting question entity."

    # 3. Check if ANY expected concept is directly supported
    for ec in reference_payload.expected_concepts:
        supported, _ = _is_concept_supported_in_text(ec, candidate_answer)
        if supported:
            return True, f"Response directly addresses expected concept '{ec.concept}'."

    # 4. Intro and background question awareness
    is_intro_q = any(t in norm_q for t in ["yourself", "background", "introduce", "intro", "experience", "journey", "walk me through", "tell me about"])
    if is_intro_q and len(norm_ans.split()) >= 3:
        return True, "Candidate provided professional background introduction."

    # 5. Check if candidate is explicitly answering a completely different domain
    # Example: React answer for SQL database normalization
    frontend_terms = {"react", "vue", "angular", "css", "html", "jsx", "tailwind", "dom", "component"}
    sql_terms = {"database", "sql", "table", "relational", "normalization", "index", "primary key", "foreign key", "acid", "postgres", "postgresql"}
    
    is_q_sql = any(t in norm_q or t in norm_ref for t in sql_terms)
    is_ans_frontend = any(t in norm_ans for t in frontend_terms)
    is_ans_sql = any(t in norm_ans for t in sql_terms)

    if is_q_sql and is_ans_frontend and not is_ans_sql:
        return False, "Response discusses frontend UI frameworks instead of database architecture requested in prompt."

    # 6. Check for meaningful topic overlap with stem matching
    q_words = [w for w in norm_q.split() if len(w) >= 3 and w not in STOP_WORDS and w not in {"what", "how", "explain", "describe", "which", "when", "your"}]
    ref_words = [w for w in norm_ref.split() if len(w) >= 3 and w not in STOP_WORDS]
    ans_words = [w for w in norm_ans.split() if len(w) >= 2 and w not in STOP_WORDS]
    
    q_matched = [w for w in q_words if any((w == aw or (len(w) >= 4 and len(aw) >= 4 and (w.startswith(aw[:4]) or aw.startswith(w[:4])))) for aw in ans_words)]
    ref_matched = [w for w in ref_words if any((w == aw or (len(w) >= 4 and len(aw) >= 4 and (w.startswith(aw[:4]) or aw.startswith(w[:4])))) for aw in ans_words)]

    # 7. Check multilingual concept triggers
    for group_key, synonyms in MULTILINGUAL_CONCEPT_MAP.items():
        if any(syn in norm_q or syn in norm_ref for syn in synonyms[:3]):
            if any(syn in norm_ans for syn in synonyms):
                return True, f"Response demonstrates direct domain alignment with {group_key} concepts."

    if len(q_matched) >= 1 or len(ref_matched) >= 1:
        return True, "Response directly addresses core entities in prompt or reference answer."

    # 8. If general technical response for project deep-dive
    if reference_payload.is_candidate_specific and len(norm_ans.split()) >= 4:
        return True, "Candidate provided contextual implementation details for project prompt."

    return False, "Response does not demonstrate meaningful conceptual overlap with the question."


class SemanticEvaluatorEngine:
    """Core evaluation engine performing multi-dimensional evidence extraction and tiering."""

    def evaluate_turn_semantics(
        self,
        candidate_answer: str,
        reference_payload: QuestionReferencePayload,
        question_text: str = "",
        interview_focus: str = "Technical Core",
    ) -> SemanticEvaluationResult:
        """Run complete semantic evaluation pipeline for a candidate turn."""
        q_text = question_text or reference_payload.question_text
        det_class = classify_answer_deterministically(candidate_answer, question_text=q_text)

        # 1. Non-Answer Hard Gate (Phase 4.1 Preservation)
        if det_class is not None and det_class.is_non_answer:
            all_missed = [c.concept for c in reference_payload.expected_concepts]
            if not all_missed and reference_payload.primary_concept:
                all_missed = [reference_payload.primary_concept]

            concept_evidence = [
                ConceptEvidence(
                    concept=c.concept,
                    importance=c.importance,
                    evidence_status=EvidenceCategory.MISSING,
                    notes="Candidate stated they do not know or passed this question.",
                )
                for c in reference_payload.expected_concepts
            ]

            return SemanticEvaluationResult(
                is_relevant=False,
                relevance_reason="Candidate stated non-answer (e.g. 'I don't know' / 'pass').",
                is_correct=False,
                correctness_reason="No technical knowledge demonstrated.",
                completeness=CompletenessLevel.NONE,
                completeness_reason="Zero expected concepts covered due to non-answer.",
                concept_evidence=concept_evidence,
                covered_concepts=[],
                missed_concepts=all_missed,
                contradicted_claims=[],
                unsupported_claims=[],
                assigned_tier=det_class.answer_quality_tier,
                classification_reason=det_class.classification_reason,
                reference_answer=reference_payload.reference_answer,
            )

        # 2. Empty Answer Gate
        if det_class is not None and det_class.is_empty:
            all_missed = [c.concept for c in reference_payload.expected_concepts]
            concept_evidence = [
                ConceptEvidence(
                    concept=c.concept,
                    importance=c.importance,
                    evidence_status=EvidenceCategory.MISSING,
                    notes="Candidate provided empty response.",
                )
                for c in reference_payload.expected_concepts
            ]
            return SemanticEvaluationResult(
                is_relevant=False,
                relevance_reason="Response is empty or whitespace.",
                is_correct=False,
                correctness_reason="No response provided.",
                completeness=CompletenessLevel.NONE,
                completeness_reason="Empty response.",
                concept_evidence=concept_evidence,
                covered_concepts=[],
                missed_concepts=all_missed,
                contradicted_claims=[],
                unsupported_claims=[],
                assigned_tier=AnswerQualityTier.EMPTY,
                classification_reason="Candidate submitted an empty response.",
                reference_answer=reference_payload.reference_answer,
            )

        # 3. Relevance Assessment
        is_relevant, rel_reason = _determine_semantic_relevance(
            candidate_answer=candidate_answer,
            question_text=q_text,
            reference_payload=reference_payload,
        )

        if not is_relevant:
            concept_evidence = [
                ConceptEvidence(
                    concept=c.concept,
                    importance=c.importance,
                    evidence_status=EvidenceCategory.IRRELEVANT,
                    notes="Response addresses unrelated subject matter.",
                )
                for c in reference_payload.expected_concepts
            ]
            return SemanticEvaluationResult(
                is_relevant=False,
                relevance_reason=rel_reason,
                is_correct=False,
                correctness_reason="Off-topic answer cannot demonstrate correctness for this question.",
                completeness=CompletenessLevel.NONE,
                completeness_reason="Irrelevant answer covers zero expected concepts.",
                concept_evidence=concept_evidence,
                covered_concepts=[],
                missed_concepts=[c.concept for c in reference_payload.expected_concepts],
                contradicted_claims=[],
                unsupported_claims=[],
                assigned_tier=AnswerQualityTier.IRRELEVANT,
                classification_reason="Answer is off-topic and discusses unrelated technologies.",
                reference_answer=reference_payload.reference_answer,
            )

        # 4. Technical Contradictions & Unsupported Claims
        contradictions = _detect_contradictions_in_text(candidate_answer)
        unsupported = _detect_unsupported_claims_in_text(
            candidate_answer, is_candidate_specific=reference_payload.is_candidate_specific
        )

        # 5. Concept Evidence Extraction
        concept_evidence: List[ConceptEvidence] = []
        covered_concepts: List[str] = []
        missed_concepts: List[str] = []
        core_covered = 0
        core_total = 0

        for ec in reference_payload.expected_concepts:
            if ec.importance == ConceptImportance.CORE:
                core_total += 1

            # Check for direct contradiction against this concept
            is_contradicted = any(
                _normalize_text_for_matching(ec.concept) in _normalize_text_for_matching(c_expl)
                for c_expl in contradictions
            )

            if is_contradicted:
                concept_evidence.append(
                    ConceptEvidence(
                        concept=ec.concept,
                        importance=ec.importance,
                        evidence_status=EvidenceCategory.CONTRADICTED,
                        notes="Candidate statements directly contradict this expected concept.",
                    )
                )
                missed_concepts.append(ec.concept)
                continue

            supported, quote = _is_concept_supported_in_text(ec, candidate_answer)
            if supported:
                concept_evidence.append(
                    ConceptEvidence(
                        concept=ec.concept,
                        importance=ec.importance,
                        evidence_status=EvidenceCategory.SUPPORTED,
                        candidate_quote=quote,
                        notes=f"Demonstrated understanding of {ec.concept}.",
                    )
                )
                covered_concepts.append(ec.concept)
                if ec.importance == ConceptImportance.CORE:
                    core_covered += 1
            else:
                concept_evidence.append(
                    ConceptEvidence(
                        concept=ec.concept,
                        importance=ec.importance,
                        evidence_status=EvidenceCategory.MISSING,
                        notes="Concept was not addressed in response.",
                    )
                )
                missed_concepts.append(ec.concept)

        # 6. Correctness Assessment
        norm_q = _normalize_text_for_matching(q_text)
        is_intro_q = any(t in norm_q for t in ["yourself", "background", "introduce", "intro", "experience", "journey", "walk me through", "tell me about"])
        if is_intro_q and len(candidate_answer.split()) >= 3 and len(contradictions) == 0:
            is_correct = True
            corr_reason = "Candidate provided appropriate background introduction."
            if not covered_concepts:
                primary_intro = reference_payload.primary_concept or "Candidate Introduction"
                covered_concepts.append(primary_intro)
                core_covered = 1
                core_total = 1
                concept_evidence = [
                    ConceptEvidence(
                        concept=primary_intro,
                        importance=ConceptImportance.CORE,
                        evidence_status=EvidenceCategory.SUPPORTED,
                        candidate_quote=candidate_answer[:80],
                        notes="Candidate provided clear professional introduction.",
                    )
                ]
                missed_concepts = []
        else:
            is_correct = (len(contradictions) == 0) and bool(covered_concepts)
            if not is_correct:
                if contradictions:
                    corr_reason = f"Contains technical contradictions: {'; '.join(contradictions)}"
                else:
                    corr_reason = "No expected technical concepts demonstrated in response."
            else:
                corr_reason = "Technical statements align with domain principles and expected concepts."

        # 7. Completeness & Concept Ratio Assessment
        total_concepts = len(reference_payload.expected_concepts) or 1
        coverage_ratio = len(covered_concepts) / total_concepts
        core_ratio = (core_covered / core_total) if core_total > 0 else coverage_ratio

        # 8. Short Valid Answer Handling (e.g. "GET.", "O(1)", "PostgreSQL.")
        # A short answer is only COMPLETE if the reference requires a single fact (core_total <= 1 or core_ratio >= 0.8).
        # A short partial answer to a multi-concept question falls through to PARTIAL.
        if is_short_valid_answer(candidate_answer) and is_correct and (core_total <= 1 or core_ratio >= 0.8) and core_covered >= 1:
            return SemanticEvaluationResult(
                is_relevant=True,
                relevance_reason="Direct concise answer to factual prompt.",
                is_correct=True,
                correctness_reason="Factual answer is technically accurate.",
                completeness=CompletenessLevel.COMPLETE,
                completeness_reason="Concise answer completely satisfies factual question requirements.",
                concept_evidence=concept_evidence,
                covered_concepts=covered_concepts or [reference_payload.primary_concept],
                missed_concepts=[],
                contradicted_claims=[],
                unsupported_claims=[],
                assigned_tier=AnswerQualityTier.STRONG,
                classification_reason="Concise, valid technical response directly answering the prompt.",
                reference_answer=reference_payload.reference_answer,
            )

        if not is_correct:
            completeness = CompletenessLevel.INSUFFICIENT
            if contradictions:
                comp_reason = f"Answer contains factual contradictions: {'; '.join(contradictions)}"
                tier = AnswerQualityTier.INCORRECT
                tier_reason = f"Technically incorrect claims: {'; '.join(contradictions)}"
            elif not is_relevant:
                completeness = CompletenessLevel.NONE
                comp_reason = "Irrelevant answer covering zero expected concepts."
                tier = AnswerQualityTier.IRRELEVANT
                tier_reason = "Answer is off-topic and discusses unrelated matter."
            else:
                comp_reason = "Vague or superficial attempt without substantive concept coverage."
                tier = AnswerQualityTier.WEAK
                tier_reason = "Answer lacks technical substance and fails to demonstrate expected concepts."
        elif core_ratio >= 0.8:
            completeness = CompletenessLevel.COMPLETE
            comp_reason = "Demonstrated comprehensive coverage of core expected concepts."
            tier = AnswerQualityTier.STRONG
            tier_reason = "Relevant, accurate, and substantively complete technical response."
        elif core_ratio >= 0.4 or covered_concepts:
            completeness = CompletenessLevel.PARTIAL
            comp_reason = "Covered foundational concepts but omitted critical trade-offs or anomalies."
            tier = AnswerQualityTier.PARTIAL
            tier_reason = "Relevant and partially correct, but missing deeper mechanics or edge cases."
        else:
            completeness = CompletenessLevel.INSUFFICIENT
            comp_reason = "Vague or superficial attempt without substantive concept coverage."
            tier = AnswerQualityTier.WEAK
            tier_reason = "Shallow explanation with insufficient technical depth for this question."

        return SemanticEvaluationResult(
            is_relevant=is_relevant,
            relevance_reason=rel_reason,
            is_correct=is_correct,
            correctness_reason=corr_reason,
            completeness=completeness,
            completeness_reason=comp_reason,
            concept_evidence=concept_evidence,
            covered_concepts=covered_concepts,
            missed_concepts=missed_concepts,
            contradicted_claims=contradictions,
            unsupported_claims=unsupported,
            assigned_tier=tier,
            classification_reason=tier_reason,
            reference_answer=reference_payload.reference_answer,
        )


def get_semantic_evaluator_engine() -> SemanticEvaluatorEngine:
    """Dependency provider for SemanticEvaluatorEngine."""
    return SemanticEvaluatorEngine()
