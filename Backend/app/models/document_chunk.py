"""
DocumentChunk model: stores individual text chunks generated from documents.
Used by downstream Vector DB / Embedding / RAG pipelines.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import backref, relationship

from app.database.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)

    # Embedding fields for downstream Vector DB / RAG pipelines
    embedding = Column(JSON, nullable=True)
    embedding_model = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    document = relationship(
        "Document",
        backref=backref("chunks", cascade="all, delete-orphan", passive_deletes=True),
        lazy="select",
    )
    owner = relationship("User", lazy="select")

    __table_args__ = (
        Index("idx_document_chunks_doc_chunk", "document_id", "chunk_index"),
        Index("idx_document_chunks_user_doc", "user_id", "document_id"),
    )
