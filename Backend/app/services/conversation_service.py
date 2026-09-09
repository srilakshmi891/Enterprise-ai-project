"""
Conversation memory service: manages creation, retrieval, deletion of conversations,
and user-isolated message history logs.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage


class ConversationService:
    def create_conversation(
        self, db: Session, user_id: int, title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation session for a user."""
        conversation = Conversation(user_id=user_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    def get_conversation(
        self, db: Session, conversation_id: int, user_id: int
    ) -> Conversation:
        """
        Retrieve a conversation session.
        Enforces user isolation: returns 404 if conversation doesn't exist or belongs to another user.
        """
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conversation or conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        return conversation

    def list_conversations(self, db: Session, user_id: int) -> List[Conversation]:
        """List all conversations for a user."""
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def delete_conversation(self, db: Session, conversation_id: int, user_id: int) -> None:
        """Delete a conversation session and all its messages via cascade."""
        conversation = self.get_conversation(db, conversation_id, user_id)
        db.delete(conversation)
        db.commit()

    def save_message(
        self, db: Session, conversation_id: int, user_id: int, role: str, content: str
    ) -> ConversationMessage:
        """Save a message turn under a user-owned conversation session."""
        # 1. Enforce conversation ownership check
        self.get_conversation(db, conversation_id, user_id)

        # 2. Add message log
        msg = ConversationMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
        )
        db.add(msg)
        
        # 3. Update conversation's updated_at timestamp
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            from datetime import datetime, timezone
            conversation.updated_at = datetime.now(timezone.utc)
            
        db.commit()
        db.refresh(msg)
        return msg

    def get_message_history(
        self, db: Session, conversation_id: int, user_id: int, limit: int = 10
    ) -> List[ConversationMessage]:
        """
        Retrieve the recent messages history log for a conversation session.
        Enforces ownership validation.
        Returns the recent `limit` messages sorted chronologically ascending.
        """
        # Validate ownership
        self.get_conversation(db, conversation_id, user_id)

        # Query messages: fetch last `limit` messages, but sorted chronologically ascending for context feed
        messages = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        # Reverse list to restore chronological order (ascending)
        messages.reverse()
        return messages


# Global singleton instance
conversation_service = ConversationService()
