"""
Pydantic schemas for Document Embedding endpoints.
"""
from pydantic import BaseModel, Field


class DocumentEmbeddingResponse(BaseModel):
    """Response schema for embedding operations and metadata queries."""
    document_id: int = Field(description="ID of the parent document")
    total_chunks: int = Field(description="Total number of chunks embedded")
    embedding_model: str = Field(description="Name of the embedding model used")
    embedding_dimension: int = Field(description="Dimension size of the embedding vectors")
    status: str = Field(default="embedded", description="Embedding status")

    model_config = {"from_attributes": True}
