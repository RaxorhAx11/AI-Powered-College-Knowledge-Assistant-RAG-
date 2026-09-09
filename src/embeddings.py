from typing import List
import numpy as np
import logging

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Generates local vector embeddings using SentenceTransformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None

    def _load_model(self):
        """Lazy load model on first call."""
        if self.model is None:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Please run: pip install sentence-transformers"
                )
            logger.info(f"Loading embedding model: '{self.model_name}'...")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully.")

    def embed_texts(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        Generate vector embeddings for a list of texts.
        
        Returns:
            np.ndarray of shape (len(texts), embedding_dim) and dtype float32.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        self._load_model()
        embeddings = self.model.encode(
            texts, 
            show_progress_bar=False, 
            convert_to_numpy=True, 
            normalize_embeddings=normalize
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Generate a vector embedding for a single user query string.
        
        Returns:
            np.ndarray of shape (1, embedding_dim) and dtype float32.
        """
        embeddings = self.embed_texts([query], normalize=normalize)
        return embeddings
