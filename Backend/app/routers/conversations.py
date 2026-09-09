"""
Conversations Router: manages session lifecycles for multi-turn chats.
Enforces JWT authentication and user isolation.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    ConversationDetailResponse,
)
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
def create_session(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new conversation session."""
    return conversation_service.create_conversation(
        db=db, user_id=current_user.id, title=request.title
    )


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List user's conversation sessions",
)
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all conversation sessions belonging to the authenticated user."""
    items = conversation_service.list_conversations(db=db, user_id=current_user.id)
    return ConversationListResponse(total=len(items), items=items)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation session detail and history",
)
def get_session(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed session logs including past message history turns."""
    # Retrieve base session info (validates ownership inside)
    session = conversation_service.get_conversation(
        db=db, conversation_id=conversation_id, user_id=current_user.id
    )
    # Fetch all history messages for detail view (no default feed limit)
    messages = conversation_service.get_message_history(
        db=db, conversation_id=conversation_id, user_id=current_user.id, limit=1000
    )
    
    return ConversationDetailResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=messages,
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation session",
)
def delete_session(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation session and all cascade message log logs."""
    conversation_service.delete_conversation(
        db=db, conversation_id=conversation_id, user_id=current_user.id
    )
