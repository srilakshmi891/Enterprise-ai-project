"""
Document Embedding Service: loads embedding models lazily and generates vector representations.
Default model: all-MiniLM-L6-v2 (384 dimensions).
Model instances are cached globally to avoid reloading per request.
"""
from typing import Any, Dict, List, Optional
from app.config import settings

class EmbeddingServiceError(Exception):
    """Raised when loading model or generating embeddings fails."""
    pass


# Global module-level model cache to reuse loaded SentenceTransformer instances
_MODEL_CACHE: Dict[str, Any] = {}


def get_embedding_model(model_name: Optional[str] = None) -> Any:
    """
    Get or load the requested SentenceTransformer model from cache.
    Default model is configured via settings.EMBEDDING_MODEL_NAME.
    """
    resolved_name = model_name or settings.EMBEDDING_MODEL_NAME
    if resolved_name in _MODEL_CACHE:
        return _MODEL_CACHE[resolved_name]

    try:
        from sentence_transformers import SentenceTransformer
        # Load local or HuggingFace model (try local cache first to avoid network timeouts)
        try:
            model = SentenceTransformer(resolved_name, local_files_only=True)
        except Exception:
            model = SentenceTransformer(resolved_name)
        _MODEL_CACHE[resolved_name] = model
        return model
    except Exception as e:
        raise EmbeddingServiceError(f"Failed to load embedding model '{resolved_name}': {str(e)}")


def generate_embeddings(
    texts: List[str],
    model_name: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate embeddings for a list of string texts.
    Returns:
        List of float vectors, e.g. [[0.01, -0.05, ...], ...]
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)

    try:
        # Encode texts to numpy arrays and convert to standard Python float lists
        embeddings_ndarray = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [vector.tolist() for vector in embeddings_ndarray]
    except Exception as e:
        raise EmbeddingServiceError(f"Embedding generation failed: {str(e)}")


def get_embedding_dimension(model_name: Optional[str] = None) -> int:
    """
    Return the vector dimension size of the active embedding model.
    """
    model = get_embedding_model(model_name)
    try:
        dim = model.get_sentence_embedding_dimension()
        return int(dim)
    except Exception:
        # Fallback for all-MiniLM-L6-v2
        return 384
