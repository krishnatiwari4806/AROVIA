"""Personal AI Coach conversation, debrief, and chat REST API Endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.coach import (
    CoachChatRequest,
    CoachChatResponse,
    CoachConversationCreate,
    CoachConversationResponse,
    CoachHistoryResponse,
    CoachMessageCreate,
    CoachMessageResponse,
)
from app.services.coach_service import CoachService, get_coach_service

router = APIRouter()


@router.post(
    "/conversation",
    response_model=CoachConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get or initialize a coach conversation with initial debrief",
)
@limiter.limit("15/minute")
async def get_or_create_coach_conversation(
    request: Request,
    response: Response,
    body: CoachConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    coach_service: Annotated[CoachService, Depends(get_coach_service)],
) -> CoachConversationResponse:
    """Retrieve or initialize an active coach conversation session.

    If session_id is provided, grounds the conversation in that specific interview session.
    Automatically generates an initial mentor debrief if this is a newly opened conversation.
    Strictly verifies user ownership of the interview session.
    """
    conversation, followups = await coach_service.get_or_create_conversation(
        db=db,
        current_user=current_user,
        session_id=body.session_id,
        auto_debrief=body.auto_debrief,
    )
    resp = CoachConversationResponse.model_validate(conversation)
    resp.suggested_followups = followups
    return resp


@router.get(
    "/history/{session_id}",
    response_model=CoachHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get stored coach conversation history for an interview session",
)
async def get_coach_history(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    coach_service: Annotated[CoachService, Depends(get_coach_service)],
) -> CoachHistoryResponse:
    """Retrieve chronological coach conversation history for a specific interview session.

    Enforces strict user ownership: candidates can only retrieve history for their own sessions.
    Returns an empty history payload if no coach conversation has been started yet.
    """
    return await coach_service.get_conversation_history(
        db=db,
        current_user=current_user,
        session_id=session_id,
    )


@router.post(
    "/chat",
    response_model=CoachChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the AI Coach a follow-up question or request feedback",
)
@limiter.limit("30/minute")
async def chat_with_coach(
    request: Request,
    response: Response,
    body: CoachChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    coach_service: Annotated[CoachService, Depends(get_coach_service)],
) -> CoachChatResponse:
    """Interactive AI Coach inquiry.

    Grounded in current interview session, transcript turns, historical performance,
    and recent dialogue memory. Persists both candidate inquiry and AI Coach response.
    """
    return await coach_service.process_chat(
        db=db,
        current_user=current_user,
        conversation_id=body.conversation_id,
        message_text=body.message,
        context_turn_index=body.context_turn_index,
    )


@router.post(
    "/messages",
    response_model=CoachMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append a raw message to a coach conversation",
)
async def add_coach_message(
    body: CoachMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    coach_service: Annotated[CoachService, Depends(get_coach_service)],
) -> CoachMessageResponse:
    """Persist a message (from candidate or coach) into the conversation history.

    Verifies that the conversation belongs to the authenticated user before adding.
    """
    message = await coach_service.add_message(
        db=db,
        current_user=current_user,
        conversation_id=body.conversation_id,
        sender=body.sender,
        message_text=body.message_text,
        context_turn_index=body.context_turn_index,
    )
    return CoachMessageResponse.model_validate(message)
