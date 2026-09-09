"""
AI Project Assistant Service.
Orchestrates intent classification, context retrieval from RAG/GitHub/Jira,
and grounded answer generation via GeminiService.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.schemas.assistant import AssistantAskRequest, AssistantAskResponse, AssistantSource
from app.services.assistant_router import classify_intent, IntentType
from app.services.document_service import get_document_by_id
from app.services.rag_service import rag_service, RAGServiceError
from app.services.gemini_service import gemini_service, GeminiServiceError
from app import services as services_pkg


class AssistantServiceError(Exception):
    """Base exception for Assistant service errors."""
    pass


class AssistantService:
    async def process_question(
        self,
        db: Session,
        user_id: int,
        question: str,
        top_k: int = 5,
        document_id: Optional[int] = None,
        history: Optional[str] = None,
    ) -> AssistantAskResponse:
        """
        Orchestrate Q&A processing based on deterministic intent classification.
        Enforces strict user isolation and credential protection.
        """
        # 1. Ownership check if document_id filter is passed
        if document_id is not None:
            doc = get_document_by_id(db, document_id=document_id, user_id=user_id)
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found.",
                )

        # 2. Classify intent deterministically
        intent = classify_intent(question, document_id=document_id)

        # 3. Handle intent routing
        if intent == IntentType.DOCUMENT:
            return await self._handle_document_intent(
                question=question, user_id=user_id, top_k=top_k, document_id=document_id, history=history
            )

        elif intent == IntentType.GITHUB:
            return await self._handle_github_intent(question=question, history=history)

        elif intent == IntentType.JIRA:
            return await self._handle_jira_intent(question=question, history=history)

        else:
            return await self._handle_general_intent(
                question=question, user_id=user_id, top_k=top_k, history=history
            )

    async def _handle_document_intent(
        self,
        question: str,
        user_id: int,
        top_k: int,
        document_id: Optional[int],
        history: Optional[str] = None,
    ) -> AssistantAskResponse:
        """Handle document-based RAG questions."""
        try:
            retrieval_data = rag_service.retrieve_and_assemble_context(
                question=question,
                user_id=user_id,
                top_k=top_k,
                document_id=document_id,
            )
        except RAGServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Assistant retrieval failure: {str(e)}",
            )

        sources = [
            AssistantSource(
                type="document",
                filename=r["filename"],
                document_id=r["document_id"],
                chunk_id=r["chunk_id"],
            )
            for r in retrieval_data["results"]
        ]

        if retrieval_data["retrieved_count"] == 0 or not retrieval_data["context"].strip():
            return AssistantAskResponse(
                question=question,
                intent=IntentType.DOCUMENT,
                answer="I couldn't find this information in the available project data.",
                sources=[],
                retrieved_count=0,
            )

        try:
            answer = gemini_service.generate_answer(
                question=question,
                context=retrieval_data["context"],
                history=history,
            )
        except GeminiServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Assistant LLM generation failure: {str(e)}",
            )

        return AssistantAskResponse(
            question=question,
            intent=IntentType.DOCUMENT,
            answer=answer,
            sources=sources,
            retrieved_count=len(sources),
        )

    async def _handle_github_intent(self, question: str, history: Optional[str] = None) -> AssistantAskResponse:
        """Handle GitHub repository questions."""
        from app.services.github_service import list_user_repositories
        try:
            repos = await list_user_repositories()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"GitHub integration error: {str(e)}",
            )

        if not repos:
            return AssistantAskResponse(
                question=question,
                intent=IntentType.GITHUB,
                answer="I couldn't find this information in the available project data.",
                sources=[],
                retrieved_count=0,
            )

        context_blocks = []
        sources = []
        for repo in repos:
            full_name = getattr(repo, "full_name", None) or getattr(repo, "name", "unknown")
            is_private = getattr(repo, "private", False)
            lang = getattr(repo, "language", "N/A")
            desc = getattr(repo, "description", "") or ""
            
            context_blocks.append(
                f"[GitHub Repository: {full_name}]\n"
                f"Visibility: {'Private' if is_private else 'Public'}\n"
                f"Language: {lang}\n"
                f"Description: {desc}"
            )
            sources.append(AssistantSource(type="github", repository=full_name))

        assembled_context = "\n\n".join(context_blocks)

        try:
            answer = gemini_service.generate_answer(
                question=question,
                context=assembled_context,
                history=history,
            )
        except GeminiServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Assistant LLM generation failure: {str(e)}",
            )

        return AssistantAskResponse(
            question=question,
            intent=IntentType.GITHUB,
            answer=answer,
            sources=sources,
            retrieved_count=len(sources),
        )

    async def _handle_jira_intent(self, question: str, history: Optional[str] = None) -> AssistantAskResponse:
        """Handle Jira project and issue questions."""
        from app.services.jira_service import list_projects
        try:
            projects = await list_projects()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Jira integration error: {str(e)}",
            )

        if not projects:
            return AssistantAskResponse(
                question=question,
                intent=IntentType.JIRA,
                answer="I couldn't find this information in the available project data.",
                sources=[],
                retrieved_count=0,
            )

        context_blocks = []
        sources = []
        for proj in projects:
            key = getattr(proj, "key", "UNKNOWN")
            name = getattr(proj, "name", "")
            p_type = getattr(proj, "projectTypeKey", "software")

            context_blocks.append(
                f"[Jira Project: {key}]\n"
                f"Name: {name}\n"
                f"Type: {p_type}"
            )
            sources.append(AssistantSource(type="jira", project=key))

        assembled_context = "\n\n".join(context_blocks)

        try:
            answer = gemini_service.generate_answer(
                question=question,
                context=assembled_context,
                history=history,
            )
        except GeminiServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Assistant LLM generation failure: {str(e)}",
            )

        return AssistantAskResponse(
            question=question,
            intent=IntentType.JIRA,
            answer=answer,
            sources=sources,
            retrieved_count=len(sources),
        )

    async def _handle_general_intent(
        self, question: str, user_id: int, top_k: int, history: Optional[str] = None
    ) -> AssistantAskResponse:
        """Handle general project questions by combining user document context."""
        retrieval_data = rag_service.retrieve_and_assemble_context(
            question=question,
            user_id=user_id,
            top_k=top_k,
        )

        sources = [
            AssistantSource(
                type="document",
                filename=r["filename"],
                document_id=r["document_id"],
                chunk_id=r["chunk_id"],
            )
            for r in retrieval_data["results"]
        ]

        if retrieval_data["retrieved_count"] == 0 or not retrieval_data["context"].strip():
            return AssistantAskResponse(
                question=question,
                intent=IntentType.GENERAL_PROJECT,
                answer="I couldn't find this information in the available project data.",
                sources=[],
                retrieved_count=0,
            )

        try:
            answer = gemini_service.generate_answer(
                question=question,
                context=retrieval_data["context"],
                history=history,
            )
        except GeminiServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Assistant LLM generation failure: {str(e)}",
            )

        return AssistantAskResponse(
            question=question,
            intent=IntentType.GENERAL_PROJECT,
            answer=answer,
            sources=sources,
            retrieved_count=len(sources),
        )


# Global singleton instance
assistant_service = AssistantService()
