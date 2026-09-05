"""Personal AI Coach context builder and longitudinal performance aggregator."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewQuestionTurn, InterviewSession
from app.models.user import User

logger = logging.getLogger(__name__)


class CoachContextPayload:
    """Enriched data container provided to the AI Coach reasoning engine."""

    def __init__(
        self,
        candidate_name: str,
        current_session: Dict[str, Any],
        transcript_turns: List[Dict[str, Any]],
        evaluation_report: Optional[Dict[str, Any]],
        historical_performance: List[Dict[str, Any]],
        recurring_weaknesses: List[str],
        recurring_strengths: List[str],
        conversation_history: List[Dict[str, str]],
    ):
        self.candidate_name = candidate_name
        self.current_session = current_session
        self.transcript_turns = transcript_turns
        self.evaluation_report = evaluation_report
        self.historical_performance = historical_performance
        self.recurring_weaknesses = recurring_weaknesses
        self.recurring_strengths = recurring_strengths
        self.conversation_history = conversation_history

    def to_prompt_context(self) -> str:
        """Render a concise, high-signal formatted text prompt block for Gemini."""
        parts = []

        # 1. Candidate & Target Role
        parts.append(f"Candidate Name: {self.candidate_name}")
        parts.append(
            f"Target Role: {self.current_session.get('target_role', 'Software Engineer')} "
            f"({self.current_session.get('seniority_level', 'senior')})"
        )
        parts.append(f"Interview Focus: {self.current_session.get('interview_focus', 'Technical Core')}")
        parts.append(f"Practice Mode: {self.current_session.get('practice_mode', 'standard')}")

        # 2. Evaluation Scores & Summary
        if self.current_session.get("overall_score") is not None:
            parts.append(f"Current Session Overall Score: {self.current_session.get('overall_score')}/100")

        dim_scores = self.current_session.get("dimension_scores") or {}
        if dim_scores:
            dim_str = ", ".join([f"{k.capitalize()}: {v}/100" for k, v in dim_scores.items()])
            parts.append(f"Dimension Scores: {dim_str}")

        if self.evaluation_report:
            exec_summary = self.evaluation_report.get("executive_summary")
            if exec_summary:
                parts.append(f"\nExecutive Evaluation Summary:\n{exec_summary}")

            strengths = self.evaluation_report.get("top_strengths") or []
            if strengths:
                parts.append("\nKey Evaluated Strengths:")
                for s in strengths[:4]:
                    title = s.get("title", "")
                    desc = s.get("description", "")
                    parts.append(f"- {title}: {desc}")

            improvements = self.evaluation_report.get("top_improvements") or []
            if improvements:
                parts.append("\nKey Evaluated Areas for Improvement:")
                for imp in improvements[:4]:
                    title = imp.get("title", "")
                    desc = imp.get("description", "")
                    rec = imp.get("actionable_recommendation", "")
                    parts.append(f"- {title}: {desc} (Recommended Action: {rec})")

        # 3. Turn-by-Turn Q&A & Scores
        parts.append("\n--- INTERVIEW TURNS & CANDIDATE ANSWERS ---")
        for turn in self.transcript_turns:
            t_idx = turn.get("turn_index", 0)
            q_text = turn.get("question_text", "")
            ans_text = turn.get("candidate_answer", "(No answer recorded)")
            ideal_comp = turn.get("ideal_answer_comparison") or ""
            feedback = turn.get("turn_feedback") or ""
            rel = turn.get("relevance_score")
            corr = turn.get("correctness_score")
            clar = turn.get("clarity_score")
            scores_str = f"Scores: [Relevance: {rel}/100, Correctness: {corr}/100, Clarity: {clar}/100]" if rel is not None else ""

            parts.append(f"\n[Turn {t_idx + 1}]")
            parts.append(f"Question: {q_text}")
            parts.append(f"Candidate Answer: {ans_text}")
            if scores_str:
                parts.append(scores_str)
            if ideal_comp:
                parts.append(f"Benchmark Comparison: {ideal_comp}")
            if feedback:
                parts.append(f"Evaluator Feedback: {feedback}")

        # 4. Longitudinal Performance & Pattern Detection
        if self.historical_performance:
            parts.append("\n--- HISTORICAL PERFORMANCE ACROSS PREVIOUS SESSIONS ---")
            for h in self.historical_performance[:4]:
                h_role = h.get("target_role", "")
                h_score = h.get("overall_score")
                h_date = h.get("date", "")
                parts.append(f"- Past Session ({h_date}): {h_role} -> Score: {h_score}/100")

            if self.recurring_weaknesses:
                parts.append(f"Detected Recurring Weaknesses: {', '.join(self.recurring_weaknesses)}")
            if self.recurring_strengths:
                parts.append(f"Consistent Demonstrated Strengths: {', '.join(self.recurring_strengths)}")
        else:
            parts.append("\nHistorical Performance: This is the candidate's first recorded interview session in AROVIA.")

        return "\n".join(parts)


class CoachContextBuilder:
    """Builds controlled, relevant, and privacy-isolated context for AI Coach reasoning."""

    async def build_context(
        self,
        db: AsyncSession,
        current_user: User,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        max_history_messages: int = 10,
    ) -> CoachContextPayload:
        """Gather current session, evaluation report, turns, historical performance, and conversation history."""
        # 1. Fetch Current Interview Session
        current_session_dict: Dict[str, Any] = {}
        transcript_turns: List[Dict[str, Any]] = []
        evaluation_report: Optional[Dict[str, Any]] = None

        if session_id:
            session_stmt = (
                select(InterviewSession)
                .where(
                    InterviewSession.id == session_id,
                    InterviewSession.user_id == current_user.id,
                )
                .options(selectinload(InterviewSession.turns))
            )
            session_res = await db.execute(session_stmt)
            interview_session = session_res.scalar_one_or_none()

            if interview_session:
                current_session_dict = {
                    "id": interview_session.id,
                    "target_role": interview_session.target_role,
                    "seniority_level": interview_session.seniority_level,
                    "interview_focus": interview_session.interview_focus,
                    "practice_mode": interview_session.practice_mode,
                    "status": interview_session.status,
                    "overall_score": interview_session.overall_score,
                    "dimension_scores": interview_session.dimension_scores,
                    "started_at": str(interview_session.started_at),
                    "completed_at": str(interview_session.completed_at) if interview_session.completed_at else None,
                }
                evaluation_report = interview_session.evaluation_report

                # Sort turns chronologically
                sorted_turns = sorted(interview_session.turns, key=lambda t: t.turn_index)
                for t in sorted_turns:
                    eval_d = t.evaluation_data if isinstance(t.evaluation_data, dict) else {}
                    transcript_turns.append(
                        {
                            "id": t.id,
                            "turn_index": t.turn_index,
                            "question_text": t.question_text,
                            "ideal_answer": t.ideal_answer,
                            "primary_concept": eval_d.get("primary_concept", ""),
                            "candidate_answer": t.candidate_answer,
                            "relevance_score": t.relevance_score,
                            "correctness_score": t.correctness_score,
                            "clarity_score": t.clarity_score,
                            "confidence_score": t.confidence_score,
                            "covered_concepts": eval_d.get("covered_concepts", []),
                            "missed_concepts": eval_d.get("missed_concepts", []),
                            "ideal_answer_comparison": eval_d.get("ideal_answer_comparison", ""),
                            "turn_feedback": eval_d.get("turn_feedback", ""),
                        }
                    )

        # 2. Gather Historical Performance (other completed sessions for this user)
        history_stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.user_id == current_user.id,
                InterviewSession.status == "completed",
                InterviewSession.overall_score.isnot(None),
            )
            .order_by(InterviewSession.started_at.desc())
            .limit(6)
        )
        if session_id:
            history_stmt = history_stmt.where(InterviewSession.id != session_id)

        history_res = await db.execute(history_stmt)
        past_sessions = list(history_res.scalars().all())

        historical_performance: List[Dict[str, Any]] = []
        recurring_weaknesses_map: Dict[str, int] = {}
        recurring_strengths_map: Dict[str, int] = {}

        for ps in past_sessions:
            historical_performance.append(
                {
                    "id": ps.id,
                    "target_role": ps.target_role,
                    "overall_score": ps.overall_score,
                    "date": str(ps.started_at)[:10],
                }
            )
            if ps.evaluation_report and isinstance(ps.evaluation_report, dict):
                for imp in ps.evaluation_report.get("top_improvements", []):
                    title = imp.get("title")
                    if title:
                        recurring_weaknesses_map[title] = recurring_weaknesses_map.get(title, 0) + 1
                for st in ps.evaluation_report.get("top_strengths", []):
                    title = st.get("title")
                    if title:
                        recurring_strengths_map[title] = recurring_strengths_map.get(title, 0) + 1

        recurring_weaknesses = [k for k, v in recurring_weaknesses_map.items() if v >= 2]
        recurring_strengths = [k for k, v in recurring_strengths_map.items() if v >= 2]

        # 3. Gather Recent Conversation History
        conversation_history: List[Dict[str, str]] = []
        if conversation_id:
            msg_stmt = (
                select(CoachMessage)
                .where(CoachMessage.conversation_id == conversation_id)
                .order_by(CoachMessage.created_at.desc())
                .limit(max_history_messages)
            )
            msg_res = await db.execute(msg_stmt)
            recent_messages = list(reversed(msg_res.scalars().all()))
            for m in recent_messages:
                conversation_history.append(
                    {
                        "role": "user" if m.sender == "user" else "assistant",
                        "content": m.message_text,
                    }
                )

        candidate_name = current_user.full_name or "Candidate"

        return CoachContextPayload(
            candidate_name=candidate_name,
            current_session=current_session_dict,
            transcript_turns=transcript_turns,
            evaluation_report=evaluation_report,
            historical_performance=historical_performance,
            recurring_weaknesses=recurring_weaknesses,
            recurring_strengths=recurring_strengths,
            conversation_history=conversation_history,
        )


def get_coach_context_builder() -> CoachContextBuilder:
    """Dependency provider for CoachContextBuilder."""
    return CoachContextBuilder()
