"""
Pydantic schemas for AI Project Assistant Orchestration API.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AssistantAskRequest(BaseModel):
    question: str = Field(
        ...,
        description="The question to ask the AI Project Assistant.",
        example="What does the documentation say about model evaluation?",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of relevant document context chunks or items to retrieve.",
    )
    document_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional document ID to restrict search within a specific document.",
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


class AssistantSource(BaseModel):
    type: str = Field(..., description="Type of source: 'document', 'github', 'jira', or 'general'")
    filename: Optional[str] = Field(default=None, description="Filename for document sources")
    document_id: Optional[int] = Field(default=None, description="Document ID for document sources")
    chunk_id: Optional[int] = Field(default=None, description="Chunk ID for document sources")
    repository: Optional[str] = Field(default=None, description="Repository name for GitHub sources")
    project: Optional[str] = Field(default=None, description="Project key for Jira sources")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional source metadata")


class AssistantAskResponse(BaseModel):
    question: str
    intent: str = Field(..., description="Determined intent: 'DOCUMENT', 'GITHUB', 'JIRA', or 'GENERAL_PROJECT'")
    answer: str
    sources: List[AssistantSource] = Field(default_factory=list)
    retrieved_count: int = Field(default=0)
