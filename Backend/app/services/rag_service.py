"""
RAG Service: handles RAG retrieval and context assembly.
Reuses existing EmbeddingService and ChromaService without calling any LLMs.
"""
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.chroma_service import chroma_service, ChromaServiceError
from app.services.embedding_service import generate_embeddings, EmbeddingServiceError


class RAGServiceError(Exception):
    """Base exception for RAG service errors."""
    pass


class RAGService:
    def retrieve_and_assemble_context(
        self,
        question: str,
        user_id: int,
        top_k: int = 5,
        document_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        1. Generate query vector using existing EmbeddingService.
        2. Query ChromaDB with user_id isolation (and optional document_id filter).
        3. Format source chunks and assemble context block.
        """
        # 1. Generate query embedding
        model_name = settings.EMBEDDING_MODEL_NAME
        try:
            embeddings = generate_embeddings([question], model_name=model_name)
            if not embeddings or len(embeddings) == 0:
                raise RAGServiceError("Failed to generate embedding for query.")
            query_vector = embeddings[0]
        except EmbeddingServiceError as e:
            raise RAGServiceError(f"Embedding generation failed: {str(e)}")

        # 2. Retrieve chunks from ChromaDB
        try:
            raw_results = chroma_service.query_similar_chunks(
                query_embedding=query_vector,
                user_id=user_id,
                top_k=top_k,
                document_id=document_id,
            )
        except ChromaServiceError as e:
            raise RAGServiceError(f"ChromaDB retrieval failed: {str(e)}")

        if not raw_results:
            return {
                "question": question,
                "retrieved_count": 0,
                "results": [],
                "context": "",
            }

        # 3. Format results and assemble context
        results: List[Dict[str, Any]] = []
        context_blocks: List[str] = []

        for idx, res in enumerate(raw_results, start=1):
            results.append({
                "chunk_id": res["chunk_id"],
                "document_id": res["document_id"],
                "chunk_index": res["chunk_index"],
                "filename": res["filename"],
                "text": res["text"],
                "distance": res["distance"],
            })

            block = (
                f"[Source {idx}]\n"
                f"File: {res['filename']}\n"
                f"Document ID: {res['document_id']}\n"
                f"Chunk: {res['chunk_index']}\n\n"
                f"{res['text']}"
            )
            context_blocks.append(block)

        assembled_context = "\n\n".join(context_blocks)

        return {
            "question": question,
            "retrieved_count": len(results),
            "results": results,
            "context": assembled_context,
        }


# Global singleton instance
rag_service = RAGService()
