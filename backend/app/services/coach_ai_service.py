"""Personal AI Coach Reasoning and Debrief Engine using Gemini."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from google.genai import types
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from app.core.exceptions import AppError
from app.services.coach_context_builder import CoachContextPayload
from app.services.gemini_service import GeminiService, get_gemini_service

logger = logging.getLogger(__name__)

COACH_SYSTEM_INSTRUCTION = """You are AROVIA's Principal AI Interview Coach and Executive Technical Mentor.
Your mission is to transform raw interview performance data into a transformative, actionable coaching dialogue.

Guiding Principles:
1. Grounding: Every critique or compliment MUST refer to concrete evidence from the candidate's actual interview transcript, turn numbers, or scores.
2. Tone: Direct, intellectually rigorous, constructive, encouraging, and deeply technical. Speak like a senior engineering director who wants the candidate to succeed at top-tier tech companies.
3. No Hallucinations: If the transcript or history doesn't contain certain details, do not invent them.
4. Actionability: Avoid generic platitudes (e.g., "Improve communication"). Always provide the exact structure, metric, or architectural pattern they should have used instead.
5. Longitudinal Perspective: When historical sessions or recurring patterns are provided in the context, explicitly reference their trajectory (e.g., "In your last interview on System Design, you also missed write-through cache trade-offs...").
"""

INITIAL_DEBRIEF_PROMPT_TEMPLATE = """Generate an in-depth, structured, and engaging Initial Performance Debrief for this candidate's completed mock interview.

<interview_context>
{interview_context}
</interview_context>

Instructions:
1. Address the candidate by name ({candidate_name}).
2. Provide a 1-sentence high-level verdict acknowledging their effort and overall score ({overall_score}/100).
3. Section 1: "What You Executed Well" - Highlight 2 concrete strengths with specific references to turns or explanations they nailed.
4. Section 2: "Key Areas That Cost You Points" - Break down 2-3 specific technical or structural gaps with turn references, explaining WHY the evaluator docked points.
5. Section 3: "Trajectory & Historical Pattern" - If past sessions exist, analyze whether recurring patterns appeared or if they improved compared to earlier sessions. If this is their first interview, set the baseline.
6. Section 4: "Recommended Practice Action" - 2 targeted practice exercises or architectural topics to master next.
7. Closing: Invite the candidate to ask questions about specific turns, request ideal model answers, or practice alternative explanations.
8. Format using clean, well-spaced Markdown (bold headers, bullet points, code or metric highlights).
"""

COACH_CHAT_PROMPT_TEMPLATE = """You are continuing a 1-on-1 coaching debrief with {candidate_name}.
Respond directly and comprehensively to the candidate's latest inquiry.

<interview_context>
{interview_context}
</interview_context>

<recent_conversation_history>
{conversation_history}
</recent_conversation_history>

{turn_focus_instruction}

Candidate's Latest Message:
"{user_message}"

Instructions:
1. Answer the candidate's question with deep technical clarity, empathy, and actionable precision.
2. If they ask how to improve a specific turn answer or what they should have said, provide a concrete, senior-level "Model Answer" snippet illustrating the structure, terminology, and trade-offs.
3. If they ask about concepts, explain both the core theory and practical interview phrasing.
4. Keep the response crisp, engaging, and formatted in clean Markdown.
5. Provide 2-3 short, relevant follow-up questions or prompt ideas the candidate might want to ask next in `suggested_followups`.
"""


class CoachChatStructuredResponse(BaseModel):
    """Structured response from Gemini for interactive coaching dialogue."""

    coach_response: str = Field(
        ...,
        description="The detailed, formatted markdown response from the AI coach.",
    )
    suggested_followups: List[str] = Field(
        default_factory=list,
        description="2-3 short, highly relevant follow-up prompts the candidate can click or ask next.",
    )


class CoachAIService:
    """Service providing Gemini-powered AI Coaching debriefs and conversational guidance."""

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini = gemini_service or get_gemini_service()

    async def generate_initial_debrief(
        self, context: CoachContextPayload
    ) -> str:
        """Generate a personalized opening debrief for an interview session."""
        score_val = context.current_session.get("overall_score") or 0
        prompt = INITIAL_DEBRIEF_PROMPT_TEMPLATE.format(
            candidate_name=context.candidate_name,
            overall_score=score_val,
            interview_context=context.to_prompt_context(),
        )

        config = types.GenerateContentConfig(
            system_instruction=COACH_SYSTEM_INSTRUCTION,
            temperature=0.4,
        )

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.gemini.client.aio.models.generate_content(
                    model=self.gemini.model,
                    contents=prompt,
                    config=config,
                )
                if response.text and response.text.strip():
                    return response.text.strip()
            except Exception as exc:
                logger.warning(
                    f"Gemini coach initial debrief attempt {attempt}/{max_attempts} failed: {exc}"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(1.0)

        # High quality fallback debrief if API is temporarily unreachable
        return self._build_fallback_debrief(context)

    async def generate_chat_reply(
        self,
        context: CoachContextPayload,
        user_message: str,
        context_turn_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a conversational response with suggested follow-up suggestions."""
        # Format recent conversation history
        conv_hist_lines = []
        for msg in context.conversation_history:
            role_label = "Candidate" if msg.get("role") == "user" else "Coach"
            conv_hist_lines.append(f"{role_label}: {msg.get('content')}")
        conv_hist_str = "\n".join(conv_hist_lines) if conv_hist_lines else "No previous messages in this debrief."

        turn_focus_instruction = ""
        if context_turn_index is not None:
            turn_focus_instruction = (
                f"Note: The candidate is specifically asking about Turn {context_turn_index + 1} "
                f"of this interview. Ground your analysis in that specific question and answer."
            )

        prompt = COACH_CHAT_PROMPT_TEMPLATE.format(
            candidate_name=context.candidate_name,
            interview_context=context.to_prompt_context(),
            conversation_history=conv_hist_str,
            turn_focus_instruction=turn_focus_instruction,
            user_message=user_message,
        )

        config = types.GenerateContentConfig(
            system_instruction=COACH_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=CoachChatStructuredResponse,
            temperature=0.3,
        )

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.gemini.client.aio.models.generate_content(
                    model=self.gemini.model,
                    contents=prompt,
                    config=config,
                )
                if response.text and response.text.strip():
                    parsed = CoachChatStructuredResponse.model_validate_json(
                        response.text
                    )
                    return {
                        "coach_response": parsed.coach_response,
                        "suggested_followups": parsed.suggested_followups[:3],
                    }
            except Exception as exc:
                logger.warning(
                    f"Gemini coach chat attempt {attempt}/{max_attempts} failed: {exc}"
                )
                if attempt < max_attempts:
                    await asyncio.sleep(1.0)

        # Fallback chat response
        return self._build_fallback_chat_reply(context, user_message, context_turn_index)

    def _build_fallback_debrief(self, context: CoachContextPayload) -> str:
        """Fallback debrief when AI service is temporarily offline."""
        name = context.candidate_name
        score = context.current_session.get("overall_score", 75)
        role = context.current_session.get("target_role", "Software Engineer")
        sen = context.current_session.get("seniority_level", "senior")

        return f"""### Welcome to Your Post-Interview Debrief, {name}!

You've completed your mock interview for the **{role} ({sen})** track with an overall score of **{score}/100**.

#### 🎯 What You Executed Well
- **Structured Communication:** You laid out clear high-level architectural approaches and structured your reasoning cleanly.
- **Domain Fundamentals:** You showed solid grasp of foundational programming patterns and core systems concepts.

#### ⚠️ Key Areas to Elevate
- **Edge Case & Failure Trade-offs:** For {sen} roles, evaluators look for deep discussions on partition tolerance, latency budgets, and fallback degradation strategies.
- **Concrete Metrics:** Back up design choices with quantitative rationale (e.g. estimated QPS, cache hit ratios, memory footprints).

#### 💡 How Would You Like to Proceed?
Feel free to ask me to analyze any specific turn, write an ideal senior-level benchmark answer, or guide you through targeted preparation exercises!"""

    def _build_fallback_chat_reply(
        self,
        context: CoachContextPayload,
        user_message: str,
        context_turn_index: Optional[int],
    ) -> Dict[str, Any]:
        """Fallback reply when AI service is temporarily offline."""
        target_turn_str = f" for Turn {context_turn_index + 1}" if context_turn_index is not None else ""
        return {
            "coach_response": (
                f"Regarding your question{target_turn_str}: When answering in a technical interview, "
                f"focus on structuring your response into three pillars: **1. Core Concept & Mechanics**, "
                f"**2. Concrete Architecture & Trade-offs**, and **3. Operational Edge Cases & Failure Mitigation**. "
                f"Let me know if you would like a detailed sample answer for any particular question from your session!"
            ),
            "suggested_followups": [
                "How should I structure my system design answers?",
                "What were the biggest missed concepts in this interview?",
                "Give me a benchmark model answer for Turn 1.",
            ],
        }


def get_coach_ai_service() -> CoachAIService:
    """Dependency provider for CoachAIService."""
    return CoachAIService()
