"""
Pydantic schemas for document upload endpoints.
Sensitive fields (storage_path, stored_filename) are excluded from responses.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response for a single document — returned after upload and for detail views."""
    id: int
    filename: str = Field(description="Original filename as uploaded by the user")
    file_type: str = Field(description="File extension without dot (pdf, docx, txt, md)")
    mime_type: str
    file_size: int = Field(description="File size in bytes")
    status: str = Field(description="Processing status: uploaded, processing, processed, failed")
    created_at: datetime
    updated_at: datetime
    extracted_text: Optional[str] = None  # only when status == "processed"

    model_config = {"from_attributes": True}

class DocumentProcessResponse(BaseModel):
    """Response for processing a document"""
    id: int
    status: str = Field(description="Processing status after request")
    extracted_text: Optional[str] = None
    message: Optional[str] = None
    
    model_config = {"from_attributes": True}

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: List[DocumentResponse]
    total: int
    page: int
    per_page: int
