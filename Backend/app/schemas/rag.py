"""
Pydantic schemas for RAG Retrieval & Context Assembly endpoint (/rag/retrieve).
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RAGRetrieveRequest(BaseModel):
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


class RAGChunkResult(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    filename: str
    text: str
    distance: float


class RAGRetrieveResponse(BaseModel):
    question: str
    retrieved_count: int
    results: List[RAGChunkResult]
    context: str
