"""Conversational Bridge Engine for Phase 4.5.

Generates concise, natural, context-grounded transition phrases between interview turns.
Ensures seamless, human-like dialogue flow without fabricating technologies, tools, or candidate achievements.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.candidate_context import CandidateContext
from app.services.question_planner import QuestionIntent

logger = logging.getLogger(__name__)


class BridgeType(str, Enum):
    """Categorization of conversational transitions."""

    INTRO_TO_FIRST_CORE = "intro_to_first_core"
    INTRO_TO_CORE_1 = "intro_to_first_core"
    PROJECT_TO_TECHNICAL = "project_to_technical"
    PROJECT_TO_FOLLOWUP = "project_to_followup"
    PROJECT_TO_PROJECT_FOLLOWUP = "project_to_followup"
    TECHNICAL_TO_TECHNICAL = "technical_to_technical"
    TECHNICAL_TO_SCENARIO = "technical_to_scenario"
    TECHNICAL_TO_BEHAVIORAL = "technical_to_behavioral"
    BEHAVIORAL_TO_TECHNICAL = "behavioral_to_technical"
    JD_TO_PRACTICAL = "jd_to_practical"
    SKILL_TO_DEEP_DIVE = "skill_to_deep_dive"
    SKILL_TO_DEEPER = "skill_to_deep_dive"
    FOLLOWUP_TO_NEXT_CORE = "followup_to_next_core"
    DIRECT = "direct"


# Clean language-specific transition templates grounded in verified parameters
BRIDGE_TEMPLATES: Dict[str, Dict[BridgeType, List[str]]] = {
    "en": {
        BridgeType.INTRO_TO_FIRST_CORE: [
            "Thanks for sharing that background.",
            "Great, thanks for walking me through your background.",
            "Thank you for the introduction.",
        ],
        BridgeType.PROJECT_TO_TECHNICAL: [
            "That gives me a clear picture of your work on {prev_topic}. Shifting to the underlying technical layer,",
            "Thanks for walking through {prev_topic}. Let's dive deeper into related architectural mechanics:",
            "Good breakdown of {prev_topic}. Looking at the core technical requirements for this role,",
        ],
        BridgeType.PROJECT_TO_FOLLOWUP: [
            "Staying with {prev_topic} for a moment,",
            "Building directly on what you just shared about {prev_topic},",
            "To go one level deeper on {prev_topic},",
        ],
        BridgeType.TECHNICAL_TO_TECHNICAL: [
            "Understood. Moving forward to our next area,",
            "That makes sense. Let's look at another core aspect of the system:",
            "Great. Shifting our focus to {next_topic},",
        ],
        BridgeType.TECHNICAL_TO_SCENARIO: [
            "With those fundamentals in place, let's look at a realistic production scenario.",
            "Now let's apply this in a practical system scenario.",
            "Let's put this into a real-world architectural context.",
        ],
        BridgeType.TECHNICAL_TO_BEHAVIORAL: [
            "Thanks. Moving from architectural mechanics to engineering collaboration,",
            "Let's now touch on team dynamics and technical decision-making.",
        ],
        BridgeType.BEHAVIORAL_TO_TECHNICAL: [
            "Thanks for sharing how you navigated that situation. Let's return to technical design:",
            "That's a helpful perspective. Let's jump back into system architecture:",
        ],
        BridgeType.JD_TO_PRACTICAL: [
            "Looking specifically at the requirements for this role with {next_topic},",
            "This role emphasizes hands-on capability with {next_topic}. Let's explore that area:",
        ],
        BridgeType.SKILL_TO_DEEP_DIVE: [
            "Given your experience with {prev_topic}, let's examine key production trade-offs:",
            "Building on your background in {prev_topic},",
        ],
        BridgeType.FOLLOWUP_TO_NEXT_CORE: [
            "Thanks for clarifying that point. Let's move on to our next core topic:",
            "That clarifies the picture. Shifting gears to the next area,",
            "Good clarification. Let's advance to the next technical area:",
        ],
    },
    "hi": {
        BridgeType.INTRO_TO_FIRST_CORE: [
            "Apna background share karne ke liye dhanyawad. Chaliye ab pehle technical discussion par chalte hain.",
            "Introduction ke liye shukriya. Aayiye technical assessment shuru karte hain.",
        ],
        BridgeType.PROJECT_TO_TECHNICAL: [
            "{prev_topic} ke baare mein batane ke liye dhanyawad. Ab iske technical architecture ki taraf aate hain:",
            "{prev_topic} par aapke kaam ko samajhne ke baad, chaliye core technical concepts par focus karte hain:",
        ],
        BridgeType.PROJECT_TO_FOLLOWUP: [
            "{prev_topic} par thoda aur detail mein discuss karte hain,",
            "Aapne jo {prev_topic} ke baare mein bataya, usi ko aage badhate hue,",
        ],
        BridgeType.TECHNICAL_TO_TECHNICAL: [
            "Theek hai. Ab hum agle technical topic ki taraf badhte hain:",
            "Samajh gaya. Chaliye ab {next_topic} ke aspect ko dekhte hain:",
        ],
        BridgeType.TECHNICAL_TO_SCENARIO: [
            "In fundamentals ke baad, chaliye ek practical production scenario par baat karte hain.",
            "Ab aayiye ek real-world system scenario ko dekhte hain.",
        ],
        BridgeType.TECHNICAL_TO_BEHAVIORAL: [
            "Technical architecture ke baad, chaliye team collaboration aur decision making par baat karte hain.",
        ],
        BridgeType.BEHAVIORAL_TO_TECHNICAL: [
            "Us situation ko explain karne ke liye dhanyawad. Chaliye wapas system design par aate hain:",
        ],
        BridgeType.JD_TO_PRACTICAL: [
            "Is role ke requirements ko dekhte hue, {next_topic} par practical focus karte hain:",
        ],
        BridgeType.SKILL_TO_DEEP_DIVE: [
            "{prev_topic} mein aapke background ko dekhte hue, aayiye iske production trade-offs par baat karte hain:",
        ],
        BridgeType.FOLLOWUP_TO_NEXT_CORE: [
            "Point clarify karne ke liye dhanyawad. Chaliye ab agle core topic par chalte hain:",
            "Clarification ke liye shukriya. Aayiye agle technical area ki taraf badhte hain:",
        ],
    },
    "hinglish": {
        BridgeType.INTRO_TO_FIRST_CORE: [
            "Thanks for sharing that background! Let's start with our first technical discussion.",
            "Great, thanks for the intro! Aab hum technical topics start karte hain.",
        ],
        BridgeType.PROJECT_TO_TECHNICAL: [
            "That gives me a clear picture of your work on {prev_topic}. Shifting to the technical side of things,",
            "Thanks for explaining {prev_topic}. Let's dive deeper into related architectural mechanics:",
        ],
        BridgeType.PROJECT_TO_FOLLOWUP: [
            "{prev_topic} ke baare mein ek quick follow-up explore karte hain,",
            "Building directly on what you just shared about {prev_topic},",
        ],
        BridgeType.TECHNICAL_TO_TECHNICAL: [
            "Makes sense. Moving on to our next topic,",
            "Got it. Aab hum {next_topic} ke technical side ko dekhte hain:",
        ],
        BridgeType.TECHNICAL_TO_SCENARIO: [
            "Now let's apply this in a practical system scenario.",
            "Aab ek real-world production problem scenario explore karte hain.",
        ],
        BridgeType.TECHNICAL_TO_BEHAVIORAL: [
            "Thanks. Technical mechanics ke baad, let's talk about engineering collaboration.",
        ],
        BridgeType.BEHAVIORAL_TO_TECHNICAL: [
            "Thanks for sharing that experience! Let's jump back into system architecture:",
        ],
        BridgeType.JD_TO_PRACTICAL: [
            "This role requires solid hands-on capability in {next_topic}. Let's explore that:",
        ],
        BridgeType.SKILL_TO_DEEP_DIVE: [
            "Given your experience with {prev_topic}, let's examine production trade-offs:",
        ],
        BridgeType.FOLLOWUP_TO_NEXT_CORE: [
            "Thanks for clarifying that point! Let's move on to our next core topic:",
            "Good clarification. Aab hum agle core area ki taraf proceed karte hain:",
        ],
    },
}


class ConversationalBridgeEngine:
    """Generates natural, grounded bridge phrases between interview turns."""

    def determine_bridge_type(
        self,
        prev_intent: Optional[str],
        next_intent: Optional[str],
        is_follow_up: bool = False,
        prior_turn_was_followup: bool = False,
        turn_index: int = 1,
    ) -> BridgeType:
        """Categorize the transition between turns."""
        if is_follow_up:
            return BridgeType.PROJECT_TO_FOLLOWUP

        if prior_turn_was_followup:
            return BridgeType.FOLLOWUP_TO_NEXT_CORE

        if turn_index == 1 or prev_intent == "introduction":
            return BridgeType.INTRO_TO_FIRST_CORE

        prev_intent_str = str(prev_intent or "").lower()
        next_intent_str = str(next_intent or "").lower()

        if "project" in prev_intent_str and "scenario" in next_intent_str:
            return BridgeType.TECHNICAL_TO_SCENARIO
        if "project" in prev_intent_str:
            return BridgeType.PROJECT_TO_TECHNICAL
        if "behavioral" in prev_intent_str:
            return BridgeType.BEHAVIORAL_TO_TECHNICAL
        if "behavioral" in next_intent_str:
            return BridgeType.TECHNICAL_TO_BEHAVIORAL
        if "scenario" in next_intent_str:
            return BridgeType.TECHNICAL_TO_SCENARIO
        if "jd" in next_intent_str:
            return BridgeType.JD_TO_PRACTICAL
        if "skill" in prev_intent_str or "work" in prev_intent_str:
            return BridgeType.SKILL_TO_DEEP_DIVE

        return BridgeType.TECHNICAL_TO_TECHNICAL

    def generate_bridge(
        self,
        bridge_type: Optional[BridgeType] = None,
        prev_intent: Optional[str] = None,
        prev_topic: Optional[str] = None,
        next_intent: Optional[str] = None,
        next_topic: Optional[str] = None,
        candidate_answer: Optional[str] = None,
        language: Optional[str] = None,
        preferred_language: str = "en",
        is_follow_up: bool = False,
        prior_turn_was_followup: bool = False,
        turn_index: int = 1,
        variant_seed: int = 0,
    ) -> str:
        """Generate a clean, grounded conversational bridge phrase.
        
        Guarantees:
        1. No hallucinated tools, companies, or architectures.
        2. Clean language rendering matching preferred_language.
        3. Returns natural, non-repetitive transitions.
        """
        lang = (language or preferred_language or "en").lower().strip()
        if lang not in BRIDGE_TEMPLATES:
            lang = "en"

        if bridge_type is None:
            bridge_type = self.determine_bridge_type(
                prev_intent=prev_intent,
                next_intent=next_intent,
                is_follow_up=is_follow_up,
                prior_turn_was_followup=prior_turn_was_followup,
                turn_index=turn_index,
            )

        templates = BRIDGE_TEMPLATES[lang].get(bridge_type, BRIDGE_TEMPLATES["en"].get(bridge_type, []))
        if not templates:
            return ""

        # Select template deterministically by variant_seed to prevent repetition
        idx = variant_seed % len(templates)
        raw_template = templates[idx]

        # Format with sanitized known topics
        safe_prev_topic = (prev_topic or "your project").strip()
        safe_next_topic = (next_topic or "system architecture").strip()

        formatted = raw_template.format(
            prev_topic=safe_prev_topic,
            next_topic=safe_next_topic,
        )
        return formatted.strip()


_bridge_engine = ConversationalBridgeEngine()


def get_conversational_bridge_engine() -> ConversationalBridgeEngine:
    """Dependency provider for ConversationalBridgeEngine."""
    return _bridge_engine
