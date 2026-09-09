"""
Pydantic schemas for RAG Grounded Answer Generation (/rag/ask).
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RAGAskRequest(BaseModel):
    question: str = Field(..., description="User question string")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top chunks to retrieve (1-20)")
    document_id: Optional[int] = Field(default=None, gt=0, description="Optional document ID filter")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question must not be empty or whitespace only.")
        stripped = v.strip()
        if len(stripped) > 2000:
            raise ValueError("Question exceeds maximum length of 2000 characters.")
        return stripped


class RAGSourceMetadata(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    filename: str
    distance: float


class RAGAskResponse(BaseModel):
    question: str
    answer: str
    sources: List[RAGSourceMetadata]
    retrieved_count: Optional[int] = None
