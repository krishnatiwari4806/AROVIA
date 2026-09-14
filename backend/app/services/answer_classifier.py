"""Deterministic Answer Quality Classification Engine.

Provides authoritative, deterministic classification of candidate answers prior to LLM evaluation.
Detects EMPTY, PASS/SKIP, and pure NON_ANSWER while guaranteeing that short valid answers (e.g. 'PostgreSQL.')
and nuanced/hedged answers (e.g. 'I don't know the exact syntax, but I would use Redis caching...')
are never falsely classified as pure non-answers.
"""

from enum import Enum
import logging
import re
from typing import List, Optional, Set, Tuple

from app.schemas.evaluation import AnswerClassificationResult, AnswerQualityTier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PATTERN DICTIONARIES
# ---------------------------------------------------------------------------

PASS_SKIP_PHRASES: Set[str] = {
    "pass",
    "skip",
    "pass please",
    "please pass",
    "skip please",
    "please skip",
    "next question",
    "next question please",
    "please next question",
    "skip this question",
    "pass this question",
    "skip this",
    "pass this",
    "next please",
    "skip kar do",
    "chhod do",
    "aage badho",
    "agla sawal",
    "skip this question please",
    "pass this question please",
    "skip this please",
    "pass this please",
    "skip it",
    "pass it",
}

NON_ANSWER_EXACT_OR_PREFIX: List[str] = [
    # English
    "idk",
    "i don't know",
    "i dont know",
    "i do not know",
    "don't know",
    "dont know",
    "no idea",
    "not sure",
    "i am not sure",
    "i'm not sure",
    "im not sure",
    "i have no idea",
    "have no idea",
    "i have no clue",
    "have no clue",
    "no clue",
    "i can't answer that",
    "i cannot answer that",
    "i cant answer that",
    "can't answer that",
    "cannot answer that",
    "i can't answer",
    "i cannot answer",
    "cant answer",
    "can't answer",
    "cannot answer",
    "i don't remember",
    "i dont remember",
    "dont remember",
    "don't remember",
    "i do not remember",
    "i haven't worked with this",
    "i haven't worked with",
    "havent worked with",
    "haven't worked with",
    "not familiar with this",
    "not familiar",
    "i have no experience with this",
    "no experience with this",
    "never worked on this",
    "never worked with this",
    "i am not aware",
    "not aware",
    "no answer",
    "no comments",
    "i have no answer",
    # Hindi / Hinglish
    "mujhe nahi pata",
    "mujhe nahi pta",
    "mujhe nhi pata",
    "mujhe nhi pta",
    "pata nahi",
    "pta nahi",
    "pata nhi",
    "pta nhi",
    "nahi pata",
    "nhi pata",
    "nahi pta",
    "nhi pta",
    "nahi janta",
    "nahi jaanta",
    "kuch nahi pata",
    "kuch nhi pta",
    "idea nahi hai",
    "koi idea nahi",
    "koi idea nahi hai",
    "yaad nahi hai",
    "mujhe yaad nahi",
    "yaad nahi",
    "main nahi janta",
    "maine ispar kaam nahi kiya",
    "is baare mein nahi pata",
]

# Polite filler additions that don't add technical content
POLITE_FILLERS: Set[str] = {
    "sorry",
    "sir",
    "maam",
    "madam",
    "please",
    "thank you",
    "thanks",
    "at all",
    "right now",
    "to be honest",
    "honestly",
    "actually",
    "about this",
    "on this topic",
    "for this",
    "yaar",
    "bhai",
}

# Substantive conjunctions indicating hedged but legitimate answers
SUBSTANTIVE_CONNECTORS: List[str] = [
    "but",
    "however",
    "although",
    "though",
    "instead",
    "lekin",
    "par",
    "magar",
    "kyunki",
    "because",
    "based on",
    "i would",
    "i will",
    "we can",
    "we could",
    "we would",
    "in my experience",
    "from what i know",
    "as far as i know",
    "main",
    "hum",
    "use kar",
    "use kiya",
    "approach yeh",
]


def normalize_answer_text(text: Optional[str]) -> str:
    """Normalize raw answer text: strip apostrophes (don't -> dont), remove punctuation, collapse whitespace."""
    if not text:
        return ""
    # Strip apostrophes first so "don't" -> "dont", "i'm" -> "im"
    cleaned = re.sub(r"['’`]", "", text.strip().lower())
    # Replace remaining punctuation with space
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return " ".join(cleaned.split())


def is_empty_answer(text: Optional[str]) -> bool:
    """Check if candidate answer is completely empty, whitespace only, or punctuation only."""
    if text is None:
        return True
    stripped = text.strip()
    if not stripped:
        return True
    # Strip non-alphanumeric characters; if nothing remains, consider it empty/unusable
    alphanumeric_only = re.sub(r"[^\w]", "", stripped)
    return len(alphanumeric_only) == 0


def is_pure_pass_or_skip(normalized_text: str) -> Optional[str]:
    """Check if normalized text is an explicit request to pass or skip."""
    clean = normalize_answer_text(normalized_text)
    for phrase in PASS_SKIP_PHRASES:
        if clean == normalize_answer_text(phrase):
            return phrase
    return None


def is_pure_non_answer(normalized_text: str) -> Tuple[bool, Optional[str]]:
    """Determine whether normalized text is a pure, explicit non-answer.
    
    Guarantees anti-overmatching: answers with substantive contrast clauses
    (e.g., 'I don't know the exact syntax, but I would use Redis because...')
    are recognized as partial/evaluable answers, NOT pure non-answers.
    """
    clean = normalize_answer_text(normalized_text)
    words = clean.split()
    total_words = len(words)

    if total_words == 0:
        return False, None

    # Check for substantive connectors
    has_substantive_connector = False
    for conn in SUBSTANTIVE_CONNECTORS:
        norm_conn = normalize_answer_text(conn)
        if f" {norm_conn} " in f" {clean} ":
            has_substantive_connector = True
            break

    # If the answer contains a substantive connector and has sufficient depth, it's not a pure non-answer
    if has_substantive_connector and total_words >= 6:
        return False, None

    # If answer is substantially long (> 14 words), treat as evaluable even if it started with 'not sure'
    if total_words > 14:
        return False, None

    # Check against non-answer patterns
    for pattern in NON_ANSWER_EXACT_OR_PREFIX:
        pattern_norm = normalize_answer_text(pattern)
        pattern_words = pattern_norm.split()

        # 1. Exact match
        if clean == pattern_norm:
            return True, pattern

        # 2. Pattern with polite fillers (e.g. "i dont know sorry", "sorry no idea sir")
        if pattern_norm in clean:
            # Check remaining words outside the pattern
            remaining_words = [
                w for w in words if w not in pattern_words and w not in POLITE_FILLERS
            ]
            # If all other words are polite fillers and word count is short (<= 8), it's a pure non-answer
            if len(remaining_words) == 0 or (len(remaining_words) <= 2 and total_words <= 8 and not has_substantive_connector):
                return True, pattern

    return False, None


def is_short_valid_answer(text: Optional[str]) -> bool:
    """Check if candidate answer is concise (1-5 words) yet valid and substantive.
    
    Examples: 'PostgreSQL.', 'GET.', 'Pandas.', 'Redis.', 'TCP.', 'Docker.'
    """
    if is_empty_answer(text):
        return False
    norm = normalize_answer_text(text)
    if is_pure_pass_or_skip(norm):
        return False
    pure_na, _ = is_pure_non_answer(norm)
    if pure_na:
        return False

    words = norm.split()
    return 1 <= len(words) <= 5


def classify_answer_deterministically(
    candidate_answer: Optional[str],
    question_text: Optional[str] = None,
) -> Optional[AnswerClassificationResult]:
    """Perform authoritative deterministic classification of candidate answer.
    
    Returns an `AnswerClassificationResult` if the answer is unambiguously EMPTY, PASS, or NON_ANSWER.
    Returns None if the answer contains content requiring semantic judgment (e.g. STRONG, PARTIAL, WEAK, INCORRECT, IRRELEVANT).
    """
    # 1. Empty / Whitespace only
    if is_empty_answer(candidate_answer):
        return AnswerClassificationResult(
            answer_quality_tier=AnswerQualityTier.EMPTY,
            normalized_answer="",
            is_non_answer=True,
            is_empty=True,
            is_short_but_valid=False,
            classification_reason="Candidate submitted an empty, blank, or unusable response.",
            confidence=1.0,
            evidence=["empty_input"],
        )

    norm = normalize_answer_text(candidate_answer)

    # 2. Explicit Pass / Skip
    matched_pass = is_pure_pass_or_skip(norm)
    if matched_pass:
        return AnswerClassificationResult(
            answer_quality_tier=AnswerQualityTier.PASS,
            normalized_answer=norm,
            is_non_answer=True,
            is_empty=False,
            is_short_but_valid=False,
            classification_reason="Candidate explicitly requested to pass or skip the question.",
            confidence=1.0,
            evidence=[matched_pass],
        )

    # 3. Pure Non-Answer ('I don't know', 'no idea', etc.)
    is_na, matched_pattern = is_pure_non_answer(norm)
    if is_na and matched_pattern:
        return AnswerClassificationResult(
            answer_quality_tier=AnswerQualityTier.NON_ANSWER,
            normalized_answer=norm,
            is_non_answer=True,
            is_empty=False,
            is_short_but_valid=False,
            classification_reason="Candidate explicitly stated they do not know, lack knowledge, or cannot answer.",
            confidence=1.0,
            evidence=[matched_pattern],
        )

    # Not deterministically a non-answer/empty/pass -> returns None so semantic engine evaluates it
    return None


def classify_candidate_answer(
    candidate_answer: Optional[str],
    question_text: Optional[str] = None,
    semantic_tier: Optional[AnswerQualityTier] = None,
    semantic_reason: Optional[str] = None,
) -> AnswerClassificationResult:
    """Full classification pipeline combining deterministic safety checks with semantic result."""
    # Run deterministic safety checks first
    det_result = classify_answer_deterministically(
        candidate_answer=candidate_answer,
        question_text=question_text,
    )
    if det_result is not None:
        return det_result

    # If candidate answer is short but valid
    norm = normalize_answer_text(candidate_answer)
    short_valid = is_short_valid_answer(candidate_answer)

    assigned_tier = semantic_tier or (
        AnswerQualityTier.STRONG if short_valid else AnswerQualityTier.PARTIAL
    )
    reason = semantic_reason or (
        "Concise, direct technical response." if short_valid else "Candidate provided a technical response evaluated for domain depth."
    )

    return AnswerClassificationResult(
        answer_quality_tier=assigned_tier,
        normalized_answer=norm,
        is_non_answer=False,
        is_empty=False,
        is_short_but_valid=short_valid,
        classification_reason=reason,
        confidence=0.9 if semantic_tier else 0.75,
        evidence=["substantive_response"],
    )


def is_non_answer(text: Optional[str]) -> bool:
    """Check if candidate text is classified as non-answer, empty, or pass/skip."""
    classification = classify_answer_deterministically(text)
    if classification is None:
        return False
    return bool(classification.is_non_answer or classification.is_empty)
