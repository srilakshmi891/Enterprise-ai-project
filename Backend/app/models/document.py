"""
Document model: stores metadata for uploaded files.
Physical files live on disk; this table tracks ownership, location, and processing status.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False, unique=True)
    storage_path = Column(String, nullable=False)

    file_type = Column(String, nullable=False)       # e.g. "pdf", "docx", "txt", "md"
    mime_type = Column(String, nullable=False)        # e.g. "application/pdf"
    file_size = Column(Integer, nullable=False)       # bytes

    # Processing status for future RAG pipeline
    status = Column(String, nullable=False, default="uploaded")
    extracted_text = Column(Text, nullable=True)  # extracted content

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship back to User (read-only convenience; does NOT modify User model)
    owner = relationship("User", backref="documents", lazy="select")
