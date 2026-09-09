"""
RAG Router: provides POST /rag/retrieve for context assembly and retrieval.
Enforces JWT authentication and user isolation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.rag import RAGChunkResult, RAGRetrieveRequest, RAGRetrieveResponse
from app.schemas.ask import RAGAskRequest, RAGAskResponse, RAGSourceMetadata
from app.services.document_service import get_document_by_id
from app.services.rag_service import rag_service, RAGServiceError
from app.services.gemini_service import gemini_service, GeminiServiceError

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/retrieve",
    response_model=RAGRetrieveResponse,
    summary="Retrieve document chunks and assemble context for RAG",
)
def retrieve_rag_context(
    request: RAGRetrieveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve top relevant document chunks for a question and assemble formatted context.
    Enforces user isolation via JWT token.
    Optionally filters by document_id if provided (verifying user ownership).
    """
    # 1. Document ownership verification if document_id filter is passed
    if request.document_id is not None:
        doc = get_document_by_id(db, document_id=request.document_id, user_id=current_user.id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

    # 2. Perform retrieval and context assembly via RAGService
    try:
        data = rag_service.retrieve_and_assemble_context(
            question=request.question,
            user_id=current_user.id,
            top_k=request.top_k,
            document_id=request.document_id,
        )
    except RAGServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG retrieval error: {str(e)}",
        )

    results = [
        RAGChunkResult(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            chunk_index=r["chunk_index"],
            filename=r["filename"],
            text=r["text"],
            distance=r["distance"],
        )
        for r in data["results"]
    ]

    return RAGRetrieveResponse(
        question=data["question"],
        retrieved_count=data["retrieved_count"],
        results=results,
        context=data["context"],
    )


@router.post(
    "/ask",
    response_model=RAGAskResponse,
    summary="Ask a question and generate a grounded answer using RAG + Gemini LLM",
)
def ask_rag_question(
    request: RAGAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    RAG Grounded Q&A endpoint.
    1. Authenticate user and enforce user isolation.
    2. Verify document ownership if document_id is specified.
    3. Retrieve top relevant chunks and context via RAGService.
    4. If no context found, return immediate 'not found' response without calling Gemini.
    5. Generate grounded answer via Gemini LLM using retrieved context.
    """
    # 1. Ownership check if document_id filter is passed
    if request.document_id is not None:
        doc = get_document_by_id(db, document_id=request.document_id, user_id=current_user.id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

    # 2. Retrieve RAG context using existing RAGService
    try:
        retrieval_data = rag_service.retrieve_and_assemble_context(
            question=request.question,
            user_id=current_user.id,
            top_k=request.top_k,
            document_id=request.document_id,
        )
    except RAGServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG retrieval failure: {str(e)}",
        )

    sources = [
        RAGSourceMetadata(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            chunk_index=r["chunk_index"],
            filename=r["filename"],
            distance=r["distance"],
        )
        for r in retrieval_data["results"]
    ]

    # 3. No context case: do NOT call Gemini LLM
    if retrieval_data["retrieved_count"] == 0 or not retrieval_data["context"].strip():
        return RAGAskResponse(
            question=request.question,
            answer="I couldn't find this information in the provided documents.",
            sources=[],
            retrieved_count=0,
        )

    # 4. Context exists: generate grounded answer using Gemini LLM
    try:
        answer = gemini_service.generate_answer(
            question=request.question,
            context=retrieval_data["context"],
        )
    except GeminiServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failure: {str(e)}",
        )

    return RAGAskResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        retrieved_count=len(sources),
    )
