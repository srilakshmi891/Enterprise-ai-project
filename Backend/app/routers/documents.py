"""
Document router: upload, list, detail, download, and delete endpoints.
All endpoints require JWT authentication and enforce document ownership.
"""
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.document import DocumentResponse, DocumentListResponse, DocumentProcessResponse
from app.schemas.document_chunk import ChunkItemResponse, DocumentChunkListResponse
from app.schemas.document_embedding import DocumentEmbeddingResponse
from app.schemas.chroma import DocumentIndexResponse
from app.services.chroma_service import chroma_service, ChromaServiceError
from app.services.document_service import (
    create_document,
    list_documents,
    get_document_by_id,
    delete_document,
    update_status,
    save_extracted_text,
    save_document_chunks,
    get_document_chunks,
    save_chunk_embeddings,
    get_document_embeddings_info,
)
from app.services.document_storage import (
    generate_stored_filename,
    save_file,
    delete_file,
    get_file_path,
)
from app.services.document_extraction import extract_text, ExtractionError
from app.services.document_chunking import chunk_text, ChunkingError
from app.services.embedding_service import (
    generate_embeddings,
    get_embedding_dimension,
    EmbeddingServiceError,
)

router = APIRouter(prefix="/documents", tags=["Documents"])

# ---------------------------------------------------------------------------
# Allowed file types: extension -> set of acceptable MIME types
# ---------------------------------------------------------------------------
ALLOWED_FILE_TYPES: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    "txt": {"text/plain"},
    "md": {"text/markdown", "text/plain", "text/x-markdown", "application/octet-stream"},
}


def _validate_file(file: UploadFile) -> tuple[str, str]:
    """
    Validate the uploaded file's extension and MIME type.

    Returns:
        (file_type, mime_type) on success.

    Raises:
        HTTPException 400 on validation failure.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    # Sanitize: take only the basename to prevent path traversal
    safe_name = os.path.basename(file.filename)
    ext = os.path.splitext(safe_name)[1].lower().lstrip(".")

    if ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Allowed types: {', '.join(ALLOWED_FILE_TYPES.keys())}",
        )

    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_FILE_TYPES[ext]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{mime}' is not valid for '.{ext}' files.",
        )

    return ext, mime


def _to_response(doc) -> DocumentResponse:
    """Map a Document ORM instance to the API response schema."""
    return DocumentResponse(
        id=doc.id,
        filename=doc.original_filename,
        file_type=doc.file_type,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        status=doc.status,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        extracted_text=doc.extracted_text,
    )


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------
@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document file (PDF, DOCX, TXT, MD).
    The file is stored on disk and metadata is saved to the database.
    """
    # 1. Validate extension + MIME
    file_type, mime_type = _validate_file(file)

    # 2. Read content with size check (stream-friendly for reasonable sizes)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    # 3. Generate safe stored filename and persist to disk
    safe_original = os.path.basename(file.filename or "upload")
    stored_filename = generate_stored_filename(safe_original)
    storage_path = save_file(stored_filename, content)

    # 4. Create database record
    try:
        doc = create_document(
            db,
            user_id=current_user.id,
            original_filename=safe_original,
            stored_filename=stored_filename,
            storage_path=storage_path,
            file_type=file_type,
            mime_type=mime_type,
            file_size=len(content),
        )
    except Exception:
        # Roll back stored file if DB insert fails
        delete_file(storage_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata.",
        )

    return _to_response(doc)


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List your documents",
)
def list_user_documents(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Results per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a paginated list of documents belonging to the authenticated user."""
    docs, total = list_documents(db, user_id=current_user.id, page=page, per_page=per_page)
    return DocumentListResponse(
        documents=[_to_response(d) for d in docs],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# GET /documents/{document_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
def get_document_detail(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return metadata for a specific document owned by the authenticated user."""
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return _to_response(doc)


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/download
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/download",
    summary="Download a document",
)
def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download the original file for a document owned by the authenticated user.
    Returns the file as an attachment with the original filename.
    """
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    file_path = get_file_path(doc.storage_path)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server.",
        )

    return FileResponse(
        path=file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
def delete_user_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a document and its stored file.
    Only the owning user can delete their document.
    """
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Delete vector embeddings from ChromaDB first
    try:
        chroma_service.delete_document_vectors(document_id=doc.id, user_id=current_user.id)
    except ChromaServiceError:
        pass

    # Remove physical file first, then DB record
    delete_file(doc.storage_path)
    delete_document(db, doc)
    return None


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/process
# ---------------------------------------------------------------------------
@router.post(
    "/{document_id}/process",
    response_model=DocumentProcessResponse,
    summary="Process document text extraction",
)
def process_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract text from the specified document owned by the authenticated user.
    """
    # 1. Enforce document ownership, return 404 for another user's document
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 2. Verify physical file exists on the server, return 404 if not
    file_path = get_file_path(doc.storage_path)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical file not found on server.",
        )

    # 3. Transition status to processing
    update_status(db, doc, "processing")

    # 4. Extract text
    try:
        text = extract_text(file_path, doc.file_type)
        save_extracted_text(db, doc, text)
    except Exception as e:
        update_status(db, doc, "failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text extraction failed: {str(e)}",
        )

    return DocumentProcessResponse(
        id=doc.id,
        status=doc.status,
        extracted_text=doc.extracted_text,
        message="Text extraction completed successfully."
    )


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/text
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/text",
    response_model=DocumentProcessResponse,
    summary="Retrieve extracted text",
)
def get_document_text(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve the extracted text for a document owned by the authenticated user.
    """
    # 1. Enforce document ownership, return 404 if not found or belongs to another user
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text extraction failed for this document.",
        )

    if doc.status != "processed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document text is not available. Status is: {doc.status}",
        )

    return DocumentProcessResponse(
        id=doc.id,
        status=doc.status,
        extracted_text=doc.extracted_text,
        message="Extracted text retrieved successfully."
    )


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/chunk
# ---------------------------------------------------------------------------
@router.post(
    "/{document_id}/chunk",
    response_model=DocumentChunkListResponse,
    summary="Create text chunks for a document",
)
def chunk_document(
    document_id: int,
    chunk_size: int = Query(default=1000, gt=0, description="Target chunk size in characters"),
    chunk_overlap: int = Query(default=200, ge=0, description="Chunk overlap in characters"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partition the extracted text of a document into ordered chunks.
    Requires JWT authentication and document ownership.
    """
    # 1. Ownership check (returns 404 for missing or another user's document)
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 2. Parameter validation
    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_overlap must be strictly less than chunk_size.",
        )

    # 3. Document status & extracted_text validation
    if doc.status != "processed" or not doc.extracted_text or not doc.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text is not available or extracted_text is empty. Process document first.",
        )

    # 4. Generate chunks using chunking service
    try:
        raw_chunks = chunk_text(doc.extracted_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except ChunkingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 5. Persist chunks in database (atomic replacement avoids duplicates)
    saved_chunks = save_document_chunks(db, doc, raw_chunks)

    # 6. Format and return response
    return DocumentChunkListResponse(
        document_id=doc.id,
        total_chunks=len(saved_chunks),
        chunks=[ChunkItemResponse.model_validate(c) for c in saved_chunks],
    )


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/chunks
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
    summary="Get document chunks",
)
def list_document_chunks(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all chunks for a document owned by the authenticated user, ordered by chunk_index.
    """
    # 1. Ownership check (returns 404 for missing or another user's document)
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 2. Fetch chunks scoped to document and user
    chunks = get_document_chunks(db, document_id=document_id, user_id=current_user.id)

    return DocumentChunkListResponse(
        document_id=doc.id,
        total_chunks=len(chunks),
        chunks=[ChunkItemResponse.model_validate(c) for c in chunks],
    )


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/embed
# ---------------------------------------------------------------------------
@router.post(
    "/{document_id}/embed",
    response_model=DocumentEmbeddingResponse,
    summary="Generate embeddings for document chunks",
)
def embed_document_chunks(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate vector embeddings for all existing chunks of a document.
    Requires JWT authentication and document ownership.
    """
    # 1. Ownership check (returns 404 for missing or another user's document)
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 2. Fetch chunks belonging to document and user
    chunks = get_document_chunks(db, document_id=document_id, user_id=current_user.id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has not been chunked yet. Create chunks first.",
        )

    # 3. Generate embeddings
    model_name = settings.EMBEDDING_MODEL_NAME
    chunk_texts = [c.text for c in chunks]

    try:
        embeddings = generate_embeddings(chunk_texts, model_name=model_name)
        dimension = get_embedding_dimension(model_name=model_name)
    except EmbeddingServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # 4. Save embeddings in DB
    try:
        save_chunk_embeddings(
            db,
            document_id=doc.id,
            user_id=current_user.id,
            embeddings=embeddings,
            model_name=model_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save embeddings to database: {str(e)}",
        )

    return DocumentEmbeddingResponse(
        document_id=doc.id,
        total_chunks=len(chunks),
        embedding_model=model_name,
        embedding_dimension=dimension,
        status="embedded",
    )


# ---------------------------------------------------------------------------
# GET /documents/{document_id}/embeddings
# ---------------------------------------------------------------------------
@router.get(
    "/{document_id}/embeddings",
    response_model=DocumentEmbeddingResponse,
    summary="Get document embeddings metadata",
)
def get_document_embeddings_metadata(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve metadata summary for embeddings of a document owned by the authenticated user.
    """
    # 1. Ownership check (returns 404 for missing or another user's document)
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 2. Query embedding info
    total_embedded, model_name = get_document_embeddings_info(db, document_id=doc.id, user_id=current_user.id)
    if total_embedded == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document embeddings have not been generated yet.",
        )

    active_model = model_name or settings.EMBEDDING_MODEL_NAME
    dimension = get_embedding_dimension(active_model)

    return DocumentEmbeddingResponse(
        document_id=doc.id,
        total_chunks=total_embedded,
        embedding_model=active_model,
        embedding_dimension=dimension,
        status="embedded",
    )


# ---------------------------------------------------------------------------
# POST /documents/{document_id}/index
# ---------------------------------------------------------------------------
@router.post(
    "/{document_id}/index",
    response_model=DocumentIndexResponse,
    summary="Index document embeddings into ChromaDB",
)
def index_document_chunks(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Index existing document chunks and their generated embeddings into ChromaDB.
    Requires JWT authentication and document ownership.
    """
    # 1. Ownership check (returns 404 for missing or another user's document)
    doc = get_document_by_id(db, document_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # 2. Fetch chunks belonging to document and user in chunk_index order
    chunks = get_document_chunks(db, document_id=document_id, user_id=current_user.id)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has not been chunked yet. Create chunks first.",
        )

    # 3. Verify all chunks have generated embeddings
    for c in chunks:
        if not c.embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document chunks missing embeddings. Generate embeddings first.",
            )

    # 4. Upsert into ChromaDB
    try:
        indexed_count = chroma_service.upsert_document_chunks(chunks, doc.original_filename)
    except ChromaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index chunks into ChromaDB: {str(e)}",
        )

    return DocumentIndexResponse(
        document_id=doc.id,
        indexed_chunks=indexed_count,
        collection=settings.CHROMA_COLLECTION_NAME,
        status="indexed",
    )
