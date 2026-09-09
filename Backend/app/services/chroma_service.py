"""
ChromaDB Vector Database Service.
Handles persistent vector storage, collection management, chunk upserting,
metadata filtering for multi-tenant isolation, and vector similarity search.
"""
import os
from typing import Any, Dict, List, Optional

import chromadb
from app.config import settings


class ChromaServiceError(Exception):
    """Base exception class for ChromaDB service operations."""
    pass


class ChromaService:
    def __init__(self, persist_directory: Optional[str] = None, collection_name: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

        # Ensure storage directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    @property
    def client(self) -> chromadb.PersistentClient:
        """Lazy initialization of the persistent ChromaDB client."""
        if self._client is None:
            try:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
            except Exception as e:
                raise ChromaServiceError(f"Failed to initialize ChromaDB persistent client: {str(e)}")
        return self._client

    def get_collection(self):
        """Retrieve or create the document chunks collection."""
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                raise ChromaServiceError(f"Failed to get or create collection '{self.collection_name}': {str(e)}")
        return self._collection

    def upsert_document_chunks(self, chunks: list, filename: str) -> int:
        """
        Upsert document chunks and their embeddings into ChromaDB.
        
        Deterministic ID format: document_{document_id}_chunk_{chunk_index}
        This ensures idempotency and avoids duplicate vector entries.
        """
        if not chunks:
            return 0

        collection = self.get_collection()

        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for c in chunks:
            if not c.embedding or not isinstance(c.embedding, list):
                raise ChromaServiceError(
                    f"Chunk ID {c.id} (index {c.chunk_index}) is missing a valid embedding vector."
                )

            chunk_id_str = f"document_{c.document_id}_chunk_{c.chunk_index}"

            ids.append(chunk_id_str)
            embeddings.append(c.embedding)
            documents.append(c.text or "")
            metadatas.append({
                "user_id": int(c.user_id),
                "document_id": int(c.document_id),
                "chunk_id": int(c.id),
                "chunk_index": int(c.chunk_index),
                "filename": str(filename),
                "embedding_model": str(c.embedding_model or settings.EMBEDDING_MODEL_NAME),
            })

        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
        except Exception as e:
            raise ChromaServiceError(f"Failed to upsert chunks into ChromaDB: {str(e)}")

        return len(ids)

    def delete_document_vectors(self, document_id: int, user_id: int) -> None:
        """
        Delete all vector records associated with a document_id belonging to user_id.
        """
        collection = self.get_collection()

        try:
            # Metadata filter enforcing user isolation and target document_id
            where_filter = {
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"user_id": {"$eq": user_id}}
                ]
            }
            collection.delete(where=where_filter)
        except Exception as e:
            raise ChromaServiceError(f"Failed to delete vectors for document_id {document_id}: {str(e)}")

    def query_similar_chunks(
        self,
        query_embedding: List[float],
        user_id: int,
        top_k: int = 5,
        document_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query ChromaDB for vector similarity search.
        Enforces strict user isolation via metadata filter (user_id).
        Optionally filters by document_id if provided.
        """
        collection = self.get_collection()

        if document_id is not None:
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"document_id": {"$eq": document_id}}
                ]
            }
        else:
            where_filter = {"user_id": {"$eq": user_id}}

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            raise ChromaServiceError(f"ChromaDB similarity query failed: {str(e)}")

        formatted_results: List[Dict[str, Any]] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            dists = results["distances"][0] if results.get("distances") else []

            for i in range(len(ids)):
                meta = metas[i] if i < len(metas) else {}
                formatted_results.append({
                    "chunk_id": meta.get("chunk_id", 0),
                    "document_id": meta.get("document_id", 0),
                    "chunk_index": meta.get("chunk_index", 0),
                    "filename": meta.get("filename", ""),
                    "text": docs[i] if i < len(docs) else "",
                    "distance": float(dists[i]) if i < len(dists) else 0.0,
                })

        return formatted_results

    def count_vectors(self) -> int:
        """Return the total number of vectors in the collection."""
        return self.get_collection().count()


# Instantiate global singleton service instance
chroma_service = ChromaService()
