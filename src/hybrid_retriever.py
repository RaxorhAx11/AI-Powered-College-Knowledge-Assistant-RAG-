import re
from typing import List, Dict, Any, Tuple, Optional
import logging

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

from src.vector_store import VectorStoreManager
from src.embeddings import EmbeddingManager
from src.query_preprocessor import QueryPreprocessor

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Combines Dense Vector Search (FAISS) and Lexical Search (Rank-BM25) with context deduplication."""

    def __init__(
        self,
        vector_store: VectorStoreManager,
        embedding_manager: EmbeddingManager,
        dense_weight: float = 0.7,
        lexical_weight: float = 0.3,
        similarity_threshold: float = 0.35
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.dense_weight = dense_weight
        self.lexical_weight = lexical_weight
        self.similarity_threshold = similarity_threshold
        
        self.bm25 = None
        self.bm25_corpus_indices = []

    def _init_bm25(self):
        """Initialize BM25 index over vector store metadata chunks."""
        if not HAS_BM25 or not self.vector_store.metadata:
            return

        tokenized_corpus = []
        for chunk in self.vector_store.metadata:
            text = chunk.get("text", "").lower()
            tokens = re.findall(r'\w+', text)
            tokenized_corpus.append(tokens)

        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"Initialized BM25 index over {len(tokenized_corpus)} chunks.")

    @staticmethod
    def _normalize_scores(scores: List[float]) -> List[float]:
        """Min-max normalize a list of scores to range [0.0, 1.0]."""
        if not scores:
            return []
        min_s = min(scores)
        max_s = max(scores)
        if max_s - min_s < 1e-6:
            return [1.0 if max_s > 0 else 0.0 for _ in scores]
        return [(s - min_s) / (max_s - min_s) for s in scores]

    def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 4,
        doc_type_filter: Optional[str] = None,
        document_filter: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float, float, float]]:
        """
        Retrieve chunks using hybrid dense + lexical retrieval with metadata filtering.
        
        Returns list of tuples:
        [(chunk_metadata, hybrid_score, dense_score, lexical_score), ...]
        """
        clean_query = QueryPreprocessor.preprocess(query)
        if not clean_query:
            return []

        # 1. Dense retrieval (search all candidate vectors)
        all_metadata = self.vector_store.metadata
        if not all_metadata:
            if not self.vector_store.load():
                return []
            all_metadata = self.vector_store.metadata

        total_chunks = len(all_metadata)
        if total_chunks == 0:
            return []

        # Candidate pool size bounded for scaling (defaults to max(top_k * 10, 100) or total_chunks)
        candidate_pool_size = min(total_chunks, max(top_k * 10, 100))

        query_vector = self.embedding_manager.embed_query(clean_query)
        dense_results = self.vector_store.search(query_vector, top_k=candidate_pool_size)
        
        dense_score_map = {}
        candidate_chunk_ids = set()
        for chunk, score in dense_results:
            chunk_id = chunk.get("chunk_id")
            dense_score_map[chunk_id] = score
            candidate_chunk_ids.add(chunk_id)

        # 2. Lexical BM25 retrieval
        if HAS_BM25:
            if self.bm25 is None or getattr(self.bm25, 'corpus_size', len(all_metadata)) != total_chunks:
                self._init_bm25()

        lexical_score_map = {}
        if self.bm25 is not None:
            query_tokens = re.findall(r'\w+', clean_query.lower())
            bm25_scores = self.bm25.get_scores(query_tokens)
            norm_lexical = self._normalize_scores(list(bm25_scores))
            limit = min(len(norm_lexical), len(all_metadata))
            for idx in range(limit):
                chunk_id = all_metadata[idx].get("chunk_id")
                score = norm_lexical[idx]
                lexical_score_map[chunk_id] = score
                if score > 0.05:
                    candidate_chunk_ids.add(chunk_id)
        else:
            for chunk in all_metadata:
                lexical_score_map[chunk.get("chunk_id")] = 0.0

        candidate_chunks = [c for c in all_metadata if c.get("chunk_id") in candidate_chunk_ids] if candidate_chunk_ids else all_metadata

        # 3. Combine scores & apply metadata filtering
        candidates = []
        for chunk in candidate_chunks:
            # Metadata filtering if specified
            if doc_type_filter and chunk.get("document_type") != doc_type_filter:
                continue
            if document_filter and chunk.get("document_name") != document_filter:
                continue

            chunk_id = chunk.get("chunk_id")
            d_score = dense_score_map.get(chunk_id, 0.0)
            l_score = lexical_score_map.get(chunk_id, 0.0)

            h_score = (self.dense_weight * d_score) + (self.lexical_weight * l_score)
            candidates.append((chunk, h_score, d_score, l_score))

        # 4. Sort candidates by hybrid_score descending
        candidates.sort(key=lambda x: x[1], reverse=True)

        # 5. Deduplicate nearly identical text chunks
        seen_texts = set()
        deduped = []
        for chunk, h_s, d_s, l_s in candidates:
            text_snippet = chunk.get("text", "").strip()[:100]
            if text_snippet not in seen_texts:
                seen_texts.add(text_snippet)
                deduped.append((chunk, h_s, d_s, l_s))

        return deduped[:top_k]
