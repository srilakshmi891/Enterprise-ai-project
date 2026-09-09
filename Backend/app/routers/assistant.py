"""
AI Project Assistant Router: provides POST /assistant/ask for unified Q&A.
Enforces JWT authentication and user isolation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.assistant import AssistantAskRequest, AssistantAskResponse
from app.services.assistant_service import assistant_service

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post(
    "/ask",
    response_model=AssistantAskResponse,
    summary="Ask a question to the AI Project Assistant (routes to Documents, GitHub, Jira, or General)",
)
async def ask_assistant(
    request: AssistantAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified AI Project Assistant endpoint.
    1. Authenticates user and enforces user isolation.
    2. Classifies intent (DOCUMENT, GITHUB, JIRA, GENERAL_PROJECT).
    3. Retrieves context from target service.
    4. Generates grounded answer via Gemini LLM.
    5. Returns answer with source attribution.
    """
    return await assistant_service.process_question(
        db=db,
        user_id=current_user.id,
        question=request.question,
        top_k=request.top_k,
        document_id=request.document_id,
    )
