"""
Document service: database operations for the Document model.
All ownership checks are enforced here so routes stay thin.
"""
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


def create_document(
    db: Session,
    *,
    user_id: int,
    original_filename: str,
    stored_filename: str,
    storage_path: str,
    file_type: str,
    mime_type: str,
    file_size: int,
) -> Document:
    """Insert a new document record and return it."""
    doc = Document(
        user_id=user_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=storage_path,
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(
    db: Session,
    user_id: int,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Document], int]:
    """
    Return a page of documents belonging to the given user plus the total count.
    """
    query = db.query(Document).filter(Document.user_id == user_id)
    total = query.count()
    docs = (
        query
        .order_by(Document.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return docs, total


def get_document_by_id(db: Session, document_id: int, user_id: int) -> Document | None:
    """
    Fetch a single document by ID, scoped to the given user.
    Returns None if not found OR if it belongs to another user (information hiding).
    """
    return (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )


def delete_document(db: Session, document: Document) -> None:
    """Delete a document record from the database."""
    db.delete(document)
    db.commit()

# ---------------------------------------------------------------------------
# Additional helpers for text extraction processing
# ---------------------------------------------------------------------------

def update_status(db: Session, document: Document, new_status: str) -> Document:
    """Set a new processing status and persist the change."""
    document.status = new_status
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

def save_extracted_text(db: Session, document: Document, text: str) -> Document:
    """Store extracted text and mark the document as processed."""
    document.extracted_text = text
    document.status = "processed"
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

# ---------------------------------------------------------------------------
# Additional helpers for document text chunking
# ---------------------------------------------------------------------------

def save_document_chunks(
    db: Session,
    document: Document,
    chunks_data: list[dict],
) -> list[DocumentChunk]:
    """
    Save generated text chunks for a document.
    Atomic replacement: Deletes any existing chunks for this document to prevent duplicate entries.
    """
    # 1. Remove any existing chunks for this document
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)

    # 2. Bulk insert new chunks
    chunk_objects = [
        DocumentChunk(
            document_id=document.id,
            user_id=document.user_id,
            chunk_index=c_data["chunk_index"],
            text=c_data["text"],
            start_char=c_data.get("start_char"),
            end_char=c_data.get("end_char"),
        )
        for c_data in chunks_data
    ]
    db.add_all(chunk_objects)
    db.commit()

    # Query back created chunks in deterministic index order
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )


def get_document_chunks(
    db: Session,
    document_id: int,
    user_id: int,
) -> list[DocumentChunk]:
    """
    Retrieve all chunks for a document scoped to the specific user.
    Returns empty list if document has no chunks or does not belong to user.
    """
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id, DocumentChunk.user_id == user_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

# ---------------------------------------------------------------------------
# Additional helpers for document chunk embeddings
# ---------------------------------------------------------------------------

def save_chunk_embeddings(
    db: Session,
    document_id: int,
    user_id: int,
    embeddings: list[list[float]],
    model_name: str,
) -> list[DocumentChunk]:
    """
    Update DocumentChunk records with generated embedding vectors and model metadata.
    Idempotent: Updates existing chunk rows in index order without creating duplicates.
    """
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id, DocumentChunk.user_id == user_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    if len(chunks) != len(embeddings):
        raise ValueError(f"Mismatch between number of chunks ({len(chunks)}) and generated embeddings ({len(embeddings)})")

    for chunk, emb in zip(chunks, embeddings):
        chunk.embedding = emb
        chunk.embedding_model = model_name

    db.commit()
    return chunks


def get_document_embeddings_info(
    db: Session,
    document_id: int,
    user_id: int,
) -> tuple[int, str | None]:
    """
    Retrieve embedding summary (count of embedded chunks, model_name used)
    scoped strictly to document_id and user_id.
    """
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.user_id == user_id,
            DocumentChunk.embedding.isnot(None),
        )
        .all()
    )

    total_embedded = len(chunks)
    model_name = chunks[0].embedding_model if total_embedded > 0 else None
    return total_embedded, model_name
