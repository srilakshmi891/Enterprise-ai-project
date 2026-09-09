"""
Pydantic schemas for ChromaDB vector indexing and similarity search endpoints.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentIndexResponse(BaseModel):
    document_id: int
    indexed_chunks: int
    collection: str
    status: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return (1-20)")
    document_id: Optional[int] = Field(default=None, description="Optional document ID filter")


class SearchResultItem(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    filename: str
    text: str
    distance: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
