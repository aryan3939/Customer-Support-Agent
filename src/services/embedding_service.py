"""
Embedding Service — generates vector embeddings for RAG search.

WHY THIS SERVICE EXISTS:
------------------------
For RAG (Retrieval Augmented Generation) to work, we need to convert
text into VECTORS (lists of numbers). Similar texts produce similar
vectors. This lets us find relevant KB articles by mathematical
similarity instead of brittle keyword matching.

HOW IT WORKS:
-------------
    1. Load a sentence-transformers model (all-MiniLM-L6-v2)
    2. Pass text to the model → get a 384-dimensional vector
    3. Store the vector in the database (pgvector)
    4. To search: embed the query → find closest vectors → return articles

WHY SINGLETON:
--------------
    Loading the model takes ~2-5 seconds and uses ~100MB RAM.
    We load it ONCE at startup and reuse it for all requests.

    ❌  Bad:   Every request loads the model → slow + memory explosion
    ✅  Good:  Load once at startup → fast embeddings for all requests
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Embedding Service (Singleton)
# =============================================================================

class EmbeddingService:
    """
    Manages the sentence-transformers model for generating text embeddings.
    
    Usage:
        service = EmbeddingService()
        service.load_model()                    # Call once at startup
        
        vector = service.embed_text("How do I reset my password?")
        # → [0.012, -0.045, 0.089, ..., 0.034]  (384 floats)
        
        vectors = service.embed_texts(["text1", "text2", "text3"])
        # → [[...], [...], [...]]  (3 × 384 floats)
    """
    
    def __init__(self):
        self._model: SentenceTransformer | None = None
        self._model_name: str = settings.EMBEDDING_MODEL
        self._dimension: int = 384  # all-MiniLM-L6-v2 produces 384-dim vectors
    
    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._model is not None
    
    def load_model(self) -> None:
        """
        Load the sentence-transformers model into memory.
        
        Call this ONCE at application startup (in main.py lifespan).
        Subsequent calls are no-ops if already loaded.
        """
        if self._model is not None:
            logger.info("embedding_model_already_loaded")
            return
        
        logger.info(
            "loading_embedding_model",
            model=self._model_name,
        )
        
        self._model = SentenceTransformer(self._model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        
        logger.info(
            "embedding_model_loaded",
            model=self._model_name,
            dimension=self._dimension,
        )
    
    def get_dimension(self) -> int:
        """
        Return the embedding vector dimension (384 for all-MiniLM-L6-v2).
        
        This is needed when creating the pgvector column:
            ALTER TABLE kb_embeddings ADD COLUMN embedding vector(384);
        """
        return self._dimension
    
    def embed_text(self, text: str) -> list[float]:
        """
        Convert a single text string into a vector embedding.
        
        Args:
            text: The text to embed (e.g., a search query or KB chunk)
        
        Returns:
            A list of floats (384 dimensions for all-MiniLM-L6-v2)
        
        Raises:
            RuntimeError: If the model hasn't been loaded yet
        """
        if self._model is None:
            # Lazy load if not initialized at startup
            self.load_model()
        
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Convert multiple text strings into vector embeddings (batch).
        
        Batch encoding is MUCH faster than encoding one-by-one because
        the model processes them in parallel on the GPU/CPU.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors (each is 384 floats)
        """
        if self._model is None:
            self.load_model()
        
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


# =============================================================================
# Module-level singleton instance
# =============================================================================

# This is the SINGLE instance used across the entire application.
# Import it anywhere: from src.services.embedding_service import embedding_service
embedding_service = EmbeddingService()
