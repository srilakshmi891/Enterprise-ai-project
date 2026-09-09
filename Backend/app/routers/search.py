"""
Search router: authenticated vector similarity search endpoint.
Converts query string to embedding using the embedding service and performs
metadata-filtered vector search in ChromaDB.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.chroma import SearchRequest, SearchResponse, SearchResultItem
from app.services.chroma_service import chroma_service, ChromaServiceError
from app.services.document_service import get_document_by_id
from app.services.embedding_service import generate_embeddings, EmbeddingServiceError

router = APIRouter(tags=["Search"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search document vectors",
)
def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform semantic vector search across document chunks.
    Enforces user isolation so users can only search their own documents.
    Optional document_id filter restricts search to a specific document owned by the user.
    """
    # 1. If document_id is provided, verify ownership
    if request.document_id is not None:
        doc = get_document_by_id(db, document_id=request.document_id, user_id=current_user.id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

    # 2. Generate embedding for query using current embedding model
    model_name = settings.EMBEDDING_MODEL_NAME
    try:
        query_embeddings = generate_embeddings([request.query], model_name=model_name)
        if not query_embeddings or len(query_embeddings) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate query embedding.",
            )
        query_vector = query_embeddings[0]
    except EmbeddingServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding service error: {str(e)}",
        )

    # 3. Perform ChromaDB similarity search
    try:
        raw_results = chroma_service.query_similar_chunks(
            query_embedding=query_vector,
            user_id=current_user.id,
            top_k=request.top_k,
            document_id=request.document_id,
        )
    except ChromaServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}",
        )

    items = [
        SearchResultItem(
            chunk_id=res["chunk_id"],
            document_id=res["document_id"],
            chunk_index=res["chunk_index"],
            filename=res["filename"],
            text=res["text"],
            distance=res["distance"],
        )
        for res in raw_results
    ]

    return SearchResponse(
        query=request.query,
        results=items,
    )
