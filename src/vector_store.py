import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
import numpy as np
import logging

try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages local FAISS vector index and chunk metadata persistence."""

    def __init__(self, index_path: Path, metadata_path: Path):
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.index = None
        self.metadata: List[Dict[str, Any]] = []

    def is_indexed(self) -> bool:
        """Check if vector index and metadata exist on disk."""
        return self.index_path.exists() and self.metadata_path.exists()

    def get_stats(self) -> Dict[str, Any]:
        """Return knowledge base summary statistics."""
        if not self.metadata and self.is_indexed():
            self.load()

        if not self.metadata:
            return {
                "chunk_count": 0,
                "document_count": 0,
                "page_count": 0,
                "documents": [],
                "ocr_warning_pages": 0
            }

        docs: Set[str] = set()
        doc_pages: Set[Tuple[str, int]] = set()
        ocr_pages: Set[Tuple[str, int]] = set()

        for chunk in self.metadata:
            doc_name = chunk.get("document_name", chunk.get("document", "Unknown"))
            page_num = chunk.get("page_number", chunk.get("page", 1))
            docs.add(doc_name)
            doc_pages.add((doc_name, page_num))
            if chunk.get("needs_ocr", False):
                ocr_pages.add((doc_name, page_num))

        return {
            "chunk_count": len(self.metadata),
            "document_count": len(docs),
            "page_count": len(doc_pages),
            "documents": sorted(list(docs)),
            "ocr_warning_pages": len(ocr_pages)
        }

    def get_chunk_count(self) -> int:
        """Return total number of chunks currently indexed."""
        return len(self.metadata) if self.metadata else (self.get_stats()["chunk_count"])

    def build_index(self, embeddings: np.ndarray, chunks_metadata: List[Dict[str, Any]]) -> None:
        """
        Build a fresh FAISS IndexFlatIP (Cosine similarity for L2-normalized vectors) 
        and save index + metadata to disk.
        """
        if faiss is None:
            raise ImportError("FAISS is not installed. Please run: pip install faiss-cpu")

        if len(embeddings) == 0:
            logger.warning("Empty embeddings provided. Vector store not built.")
            return

        dim = embeddings.shape[1]
        logger.info(f"Building FAISS index with dimension {dim} for {len(embeddings)} vectors...")

        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        self.index = index
        self.metadata = chunks_metadata
        self.save()
        logger.info("FAISS index built and saved successfully.")

    def save(self) -> None:
        """Save FAISS index and metadata to disk."""
        if self.index is None:
            logger.warning("No FAISS index to save.")
            return

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

        logger.info(f"Persisted FAISS index to '{self.index_path}' and metadata to '{self.metadata_path}'.")

    def load(self) -> bool:
        """Load FAISS index and metadata from disk."""
        if faiss is None:
            raise ImportError("FAISS is not installed. Please run: pip install faiss-cpu")

        if not self.is_indexed():
            self.index = None
            self.metadata = []
            logger.warning("FAISS index or metadata file not found on disk.")
            return False

        try:
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors and {len(self.metadata)} metadata records.")
            return True
        except Exception as e:
            logger.error(f"Failed to load FAISS store: {str(e)}")
            return False

    def search(self, query_embedding: np.ndarray, top_k: int = 4) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search vector index for top-k matches to query_embedding.
        
        Returns:
            List of tuples: [(chunk_metadata_dict, similarity_score), ...]
        """
        if self.index is None or not self.metadata:
            if not self.load():
                logger.error("Cannot perform search: FAISS index is not initialized or empty.")
                return []

        if query_embedding.ndim == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)

        query_embedding = query_embedding.astype(np.float32)

        k = min(top_k, self.index.ntotal)
        if k <= 0:
            return []

        scores, indices = self.index.search(query_embedding, k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if 0 <= idx < len(self.metadata):
                chunk = self.metadata[idx]
                results.append((chunk, float(score)))

        return results
