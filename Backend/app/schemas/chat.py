"""
Pydantic schemas for Multi-Turn Chat.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.assistant import AssistantSource


class ChatAskRequest(BaseModel):
    question: str = Field(
        ...,
        description="The user's chat question.",
        example="Which document discusses model evaluation?",
    )
    conversation_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="ID of an existing conversation. If null, a new conversation is created.",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace only.")
        v_clean = v.strip()
        if len(v_clean) > 2000:
            raise ValueError("Question exceeds maximum length of 2000 characters.")
        return v_clean


class ChatAskResponse(BaseModel):
    conversation_id: int
    question: str
    intent: str
    answer: str
    sources: List[AssistantSource] = Field(default_factory=list)
    retrieved_count: int = Field(default=0)
