"""
Pydantic schemas for Document Chunk endpoints.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkItemResponse(BaseModel):
    """Schema representing an individual document chunk."""
    id: int
    chunk_index: int = Field(description="Zero-based sequential index of the chunk")
    text: str = Field(description="Text contents of the chunk")
    start_char: Optional[int] = Field(default=None, description="Starting character offset in source text")
    end_char: Optional[int] = Field(default=None, description="Ending character offset in source text")

    model_config = {"from_attributes": True}


class DocumentChunkListResponse(BaseModel):
    """Schema for chunk listing / chunking operation output."""
    document_id: int = Field(description="ID of the parent document")
    total_chunks: int = Field(description="Total number of generated chunks")
    chunks: List[ChunkItemResponse] = Field(description="List of document chunks ordered by chunk_index")
