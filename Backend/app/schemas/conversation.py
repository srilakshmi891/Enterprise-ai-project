"""
Pydantic schemas for Conversation Memory.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional title for the conversation.")


class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    total: int
    items: List[ConversationResponse]


class ConversationMessageResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    messages: List[ConversationMessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
