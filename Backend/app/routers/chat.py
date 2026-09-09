"""
Chat Router: provides POST /assistant/chat for multi-turn conversations.
Enforces JWT authentication, user isolation, and transaction/message consistency.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.conversation_service import conversation_service
from app.services.assistant_service import assistant_service
from app.config import settings

router = APIRouter(prefix="/assistant", tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatAskResponse,
    summary="Multi-turn conversation chat with RAG and LLM context memory",
)
async def chat_assistant(
    request: ChatAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    POST /assistant/chat
    Provides stateful multi-turn grounded Q&A.
    - Resolves or creates a conversation session.
    - Saves the user's question immediately to history.
    - Compiles conversation context feed up to CHAT_HISTORY_LIMIT.
    - Queries AssistantService for grounded answer generation.
    - Saves the successful assistant response to history.
    - Keeps history logs clean and safe if LLM fails.
    """
    # 1. Resolve or create conversation session
    if request.conversation_id is None:
        # Title is deterministic: first user question (limited to 100 characters)
        title = request.question[:100]
        conversation = conversation_service.create_conversation(
            db=db, user_id=current_user.id, title=title
        )
        conv_id = conversation.id
    else:
        # get_conversation verifies existence and ownership (raises 404 if invalid)
        conversation = conversation_service.get_conversation(
            db=db, conversation_id=request.conversation_id, user_id=current_user.id
        )
        conv_id = conversation.id

    # 2. Save User Message turn immediately (persists even if generation fails later)
    conversation_service.save_message(
        db=db,
        conversation_id=conv_id,
        user_id=current_user.id,
        role="user",
        content=request.question,
    )

    # 3. Retrieve recent history for context feed (default limit = CHAT_HISTORY_LIMIT)
    history_limit = settings.CHAT_HISTORY_LIMIT
    history_messages = conversation_service.get_message_history(
        db=db,
        conversation_id=conv_id,
        user_id=current_user.id,
        limit=history_limit,
    )

    # Compile history block (excluding the current user question which was just added)
    history_blocks = []
    for msg in history_messages:
        # Do not feed the current question as "past history" turn inside history block
        if msg.role == "user" and msg.content == request.question:
            continue
        role_label = "User" if msg.role == "user" else "Assistant"
        history_blocks.append(f"{role_label}: {msg.content}")
        
    history_context = "\n".join(history_blocks) if history_blocks else None

    # 4. Generate answer via AssistantService
    try:
        assistant_resp = await assistant_service.process_question(
            db=db,
            user_id=current_user.id,
            question=request.question,
            top_k=5,
            history=history_context,
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions from lower service layers safely
        raise he
    except Exception as e:
        # Keep stack traces hidden, raise clean 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failure: {str(e)}",
        )

    # 5. Save successful Assistant response turn to history
    conversation_service.save_message(
        db=db,
        conversation_id=conv_id,
        user_id=current_user.id,
        role="assistant",
        content=assistant_resp.answer,
    )

    return ChatAskResponse(
        conversation_id=conv_id,
        question=request.question,
        intent=assistant_resp.intent,
        answer=assistant_resp.answer,
        sources=assistant_resp.sources,
        retrieved_count=assistant_resp.retrieved_count,
    )
