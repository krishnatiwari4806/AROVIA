"""Local NLP and rule-based evaluation heuristics (₹0 Zero Cost)."""

import re
from typing import Any, Dict, List

# Regex pattern matching common hesitation markers and filler phrases
FILLER_WORDS_PATTERN = re.compile(
    r"\b(um|uh|er|ah|like|you know|sort of|kind of|i guess|i think maybe|basically|honestly|actually|probably|not sure)\b",
    re.IGNORECASE,
)


def analyze_speech_confidence(text: str) -> Dict[str, Any]:
    """Analyze filler word density and hesitation markers in candidate response text.

    Args:
        text: Candidate's transcribed or typed answer text.

    Returns:
        Dict with filler_count, total_words, filler_density, detected_fillers, and heuristic_confidence_score (0-100).
    """
    if not text or not text.strip():
        return {
            "filler_count": 0,
            "total_words": 0,
            "filler_density": 0.0,
            "detected_fillers": [],
            "heuristic_confidence_score": 50,
        }

    words = text.strip().split()
    total_words = len(words)

    # Find all filler matches
    matches: List[str] = [m.group(0).lower() for m in FILLER_WORDS_PATTERN.finditer(text)]
    filler_count = len(matches)

    # Calculate filler percentage density
    filler_density = (filler_count / max(1, total_words)) * 100.0

    # Heuristic penalty: 100 base, subtract 8 points per 1% filler density
    # e.g., 0% fillers -> 100, 3% fillers -> 76, 8% fillers -> 36, >=12% fillers -> 0
    raw_score = 100.0 - (filler_density * 8.0)
    heuristic_score = max(0, min(100, round(raw_score)))

    return {
        "filler_count": filler_count,
        "total_words": total_words,
        "filler_density": round(filler_density, 2),
        "detected_fillers": matches,
        "heuristic_confidence_score": heuristic_score,
    }
