"""Coach conversation and message Pydantic v2 DTO schemas."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CoachConversationCreate(BaseModel):
    """Payload to get or initialize a coach conversation."""

    session_id: Optional[str] = Field(
        None,
        description="Optional interview session ID to ground the coach conversation.",
    )
    auto_debrief: bool = Field(
        default=True,
        description="Whether to automatically generate an initial coach debrief if conversation is new.",
    )


class CoachMessageBase(BaseModel):
    """Base schema for a coach message."""

    sender: Literal["user", "coach"] = Field(
        ..., description="Message sender role: 'user' or 'coach'."
    )
    message_text: str = Field(
        ..., min_length=1, max_length=10000, description="The message content."
    )
    context_turn_index: Optional[int] = Field(
        None,
        description="Optional turn index (0-based) this message specifically refers to.",
    )


class CoachMessageCreate(BaseModel):
    """Payload to append a message to an existing conversation."""

    conversation_id: str = Field(
        ..., description="The target coach conversation ID."
    )
    sender: Literal["user", "coach"] = Field(
        default="user", description="Message sender role: 'user' or 'coach'."
    )
    message_text: str = Field(
        ..., min_length=1, max_length=10000, description="Message text."
    )
    context_turn_index: Optional[int] = Field(
        None, description="Optional turn index being discussed."
    )


class CoachMessageResponse(BaseModel):
    """Public representation of an individual coach message."""

    id: str
    conversation_id: str
    sender: str
    message_text: str
    context_turn_index: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CoachConversationResponse(BaseModel):
    """Public representation of a coach conversation session."""

    id: str
    user_id: str
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[CoachMessageResponse] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CoachHistoryResponse(BaseModel):
    """Response DTO for session coach history retrieval."""

    conversation_id: Optional[str] = None
    session_id: str
    messages: List[CoachMessageResponse] = Field(default_factory=list)
    total_messages: int = 0
    suggested_followups: List[str] = Field(default_factory=list)


class CoachChatRequest(BaseModel):
    """Payload for candidate interactive inquiry to the AI Coach."""

    conversation_id: str = Field(
        ..., description="Target coach conversation session ID."
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Candidate's question or feedback request.",
    )
    context_turn_index: Optional[int] = Field(
        None,
        description="Optional turn index (0-based) the question specifically refers to.",
    )


class CoachChatResponse(BaseModel):
    """Response from interactive AI Coach conversation turn."""

    user_message: CoachMessageResponse
    coach_message: CoachMessageResponse
    suggested_followups: List[str] = Field(default_factory=list)
