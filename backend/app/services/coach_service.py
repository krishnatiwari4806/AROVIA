"""Personal AI Coach persistent conversation service."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.models.coach import CoachConversation, CoachMessage
from app.models.interview import InterviewSession
from app.models.user import User
from app.schemas.coach import (
    CoachChatResponse,
    CoachConversationResponse,
    CoachHistoryResponse,
    CoachMessageResponse,
)
from app.services.coach_ai_service import CoachAIService, get_coach_ai_service
from app.services.coach_context_builder import (
    CoachContextBuilder,
    get_coach_context_builder,
)

logger = logging.getLogger(__name__)

DEFAULT_INITIAL_FOLLOWUPS = [
    "Why was my answer in Turn 1 scored lower?",
    "Give me an ideal senior-level answer for Turn 2.",
    "What are the top 3 concepts I should practice?",
]


class CoachService:
    """Service orchestrating coach conversations, message persistence, and session grounding."""

    def __init__(
        self,
        ai_service: Optional[CoachAIService] = None,
        context_builder: Optional[CoachContextBuilder] = None,
    ):
        self.ai_service = ai_service or get_coach_ai_service()
        self.context_builder = context_builder or get_coach_context_builder()

    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        current_user: User,
        session_id: Optional[str] = None,
        auto_debrief: bool = True,
    ) -> Tuple[CoachConversation, List[str]]:
        """Fetch an existing coach conversation for user + session, or create one idempotently.

        If a new conversation is initialized and auto_debrief is True, generates an opening debrief.
        """
        # 1. If session_id is provided, verify session exists and belongs to current user
        if session_id:
            session_stmt = select(InterviewSession).where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == current_user.id,
            )
            session_res = await db.execute(session_stmt)
            interview_session = session_res.scalar_one_or_none()
            if not interview_session:
                raise NotFoundError(
                    detail="Interview session not found or does not belong to you.",
                    error_code="SESSION_NOT_FOUND",
                )

        # 2. Check for existing conversation
        stmt = (
            select(CoachConversation)
            .where(
                CoachConversation.user_id == current_user.id,
                CoachConversation.session_id == session_id,
            )
            .order_by(CoachConversation.created_at.desc())
            .options(selectinload(CoachConversation.messages))
        )
        res = await db.execute(stmt)
        conversation = res.scalars().first()

        suggested_followups = DEFAULT_INITIAL_FOLLOWUPS

        if conversation:
            # If conversation already exists and has messages, return it directly
            if conversation.messages:
                return conversation, suggested_followups

        # 3. Create new conversation if not existing
        if not conversation:
            conversation = CoachConversation(
                user_id=current_user.id,
                session_id=session_id,
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

        # 4. Generate initial debrief if requested
        if auto_debrief:
            try:
                context = await self.context_builder.build_context(
                    db=db,
                    current_user=current_user,
                    session_id=session_id,
                    conversation_id=conversation.id,
                )
                debrief_text = await self.ai_service.generate_initial_debrief(
                    context
                )

                initial_msg = CoachMessage(
                    conversation_id=conversation.id,
                    sender="coach",
                    message_text=debrief_text,
                    context_turn_index=None,
                )
                db.add(initial_msg)
                await db.commit()
            except Exception as exc:
                logger.warning(
                    f"Auto-debrief generation failed, proceeding with empty conversation: {exc}"
                )

        # Re-fetch with eager loaded messages
        stmt = (
            select(CoachConversation)
            .where(CoachConversation.id == conversation.id)
            .options(selectinload(CoachConversation.messages))
        )
        res = await db.execute(stmt)
        return res.scalar_one(), suggested_followups

    async def get_conversation_for_user(
        self,
        db: AsyncSession,
        current_user: User,
        conversation_id: str,
    ) -> CoachConversation:
        """Fetch a specific coach conversation, strictly verifying user ownership."""
        stmt = (
            select(CoachConversation)
            .where(
                CoachConversation.id == conversation_id,
                CoachConversation.user_id == current_user.id,
            )
            .options(selectinload(CoachConversation.messages))
        )
        res = await db.execute(stmt)
        conversation = res.scalar_one_or_none()

        if not conversation:
            raise NotFoundError(
                detail="Coach conversation not found or access denied.",
                error_code="CONVERSATION_NOT_FOUND",
            )
        return conversation

    async def get_conversation_history(
        self,
        db: AsyncSession,
        current_user: User,
        session_id: str,
    ) -> CoachHistoryResponse:
        """Retrieve stored coach messages chronologically for a session."""
        # Verify session exists and belongs to current user
        session_stmt = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
        session_res = await db.execute(session_stmt)
        interview_session = session_res.scalar_one_or_none()
        if not interview_session:
            raise NotFoundError(
                detail="Interview session not found or does not belong to you.",
                error_code="SESSION_NOT_FOUND",
            )

        # Fetch conversation with messages
        stmt = (
            select(CoachConversation)
            .where(
                CoachConversation.user_id == current_user.id,
                CoachConversation.session_id == session_id,
            )
            .order_by(CoachConversation.created_at.desc())
            .options(selectinload(CoachConversation.messages))
        )
        res = await db.execute(stmt)
        conversation = res.scalars().first()

        if not conversation:
            return CoachHistoryResponse(
                conversation_id=None,
                session_id=session_id,
                messages=[],
                total_messages=0,
                suggested_followups=DEFAULT_INITIAL_FOLLOWUPS,
            )

        messages_resp = [
            CoachMessageResponse.model_validate(msg)
            for msg in conversation.messages
        ]

        return CoachHistoryResponse(
            conversation_id=conversation.id,
            session_id=session_id,
            messages=messages_resp,
            total_messages=len(messages_resp),
            suggested_followups=DEFAULT_INITIAL_FOLLOWUPS,
        )

    async def add_message(
        self,
        db: AsyncSession,
        current_user: User,
        conversation_id: str,
        sender: str,
        message_text: str,
        context_turn_index: Optional[int] = None,
    ) -> CoachMessage:
        """Persist a message (user or coach) to a conversation with user authorization."""
        if sender not in ("user", "coach"):
            raise ValidationError(
                detail="Sender must be 'user' or 'coach'.",
                error_code="INVALID_SENDER",
            )

        # Fetch conversation and verify ownership
        conversation = await self.get_conversation_for_user(
            db=db,
            current_user=current_user,
            conversation_id=conversation_id,
        )

        message = CoachMessage(
            conversation_id=conversation.id,
            sender=sender,
            message_text=message_text.strip(),
            context_turn_index=context_turn_index,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def process_chat(
        self,
        db: AsyncSession,
        current_user: User,
        conversation_id: str,
        message_text: str,
        context_turn_index: Optional[int] = None,
    ) -> CoachChatResponse:
        """Process candidate inquiry with Gemini, ground in session context, and persist both turns."""
        clean_text = message_text.strip()
        if not clean_text:
            raise ValidationError(
                detail="Message text cannot be empty.",
                error_code="EMPTY_MESSAGE",
            )

        # 1. Verify ownership
        conversation = await self.get_conversation_for_user(
            db=db,
            current_user=current_user,
            conversation_id=conversation_id,
        )

        # 2. Persist candidate user message
        user_msg = CoachMessage(
            conversation_id=conversation.id,
            sender="user",
            message_text=clean_text,
            context_turn_index=context_turn_index,
        )
        db.add(user_msg)
        await db.commit()
        await db.refresh(user_msg)

        # 3. Assemble enriched context
        context = await self.context_builder.build_context(
            db=db,
            current_user=current_user,
            session_id=conversation.session_id,
            conversation_id=conversation.id,
        )

        # 4. Generate AI Coach Response
        ai_reply = await self.ai_service.generate_chat_reply(
            context=context,
            user_message=clean_text,
            context_turn_index=context_turn_index,
        )

        coach_text = ai_reply.get("coach_response", "")
        followups = ai_reply.get("suggested_followups", [])

        # 5. Persist coach message
        coach_msg = CoachMessage(
            conversation_id=conversation.id,
            sender="coach",
            message_text=coach_text,
            context_turn_index=context_turn_index,
        )
        db.add(coach_msg)
        await db.commit()
        await db.refresh(coach_msg)

        return CoachChatResponse(
            user_message=CoachMessageResponse.model_validate(user_msg),
            coach_message=CoachMessageResponse.model_validate(coach_msg),
            suggested_followups=followups,
        )


def get_coach_service() -> CoachService:
    """Dependency provider for CoachService."""
    return CoachService()
