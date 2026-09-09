from typing import Dict, Any, Optional
import logging

from src.config import Config
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.hybrid_retriever import HybridRetriever
from src.query_preprocessor import QueryPreprocessor

logger = logging.getLogger(__name__)

class KnowledgeRetriever:
    """Production retriever supporting dense vector search, hybrid BM25+FAISS, and debug metadata."""

    def __init__(
        self, 
        embedding_manager: EmbeddingManager, 
        vector_store: VectorStoreManager,
        top_k: int = Config.TOP_K,
        similarity_threshold: float = Config.SIMILARITY_THRESHOLD,
        hybrid_enabled: bool = Config.HYBRID_ENABLED
    ):
        self.embedding_manager = embedding_manager
        self.vector_store = vector_store
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.hybrid_enabled = hybrid_enabled

        self.hybrid_retriever = HybridRetriever(
            vector_store=self.vector_store,
            embedding_manager=self.embedding_manager,
            dense_weight=Config.DENSE_WEIGHT,
            lexical_weight=Config.LEXICAL_WEIGHT,
            similarity_threshold=self.similarity_threshold
        )

    def retrieve(
        self, 
        query: str, 
        top_k: Optional[int] = None, 
        threshold: Optional[float] = None,
        doc_type_filter: Optional[str] = None,
        document_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve context relevant to the user query.
        
        Returns:
            {
                "chunks": [ ... ],
                "has_sufficient_evidence": True/False,
                "top_score": float,
                "debug_info": Dict (if RAG_DEBUG=True)
            }
        """
        k = top_k if top_k is not None else self.top_k
        thresh = threshold if threshold is not None else self.similarity_threshold

        clean_query = QueryPreprocessor.preprocess(query)
        if not clean_query:
            return {
                "chunks": [],
                "has_sufficient_evidence": False,
                "top_score": 0.0,
                "debug_info": {}
            }

        # 1. Detect query intent (Current vs Historical)
        intent_info = QueryPreprocessor.detect_query_intent(query)
        is_historical = intent_info.get("is_historical", False)
        target_year = intent_info.get("target_year")

        # 2. Retrieve candidates
        if self.hybrid_enabled:
            candidates = self.hybrid_retriever.retrieve_hybrid(
                query=clean_query,
                top_k=k * 3,  # candidate pool before thresholding
                doc_type_filter=doc_type_filter,
                document_filter=document_filter
            )
        else:
            query_vector = self.embedding_manager.embed_query(clean_query)
            total_chunks = len(self.vector_store.metadata) if self.vector_store.metadata else k * 5
            raw = self.vector_store.search(query_vector, top_k=max(k * 3, total_chunks))
            candidates = []
            for c, score in raw:
                if doc_type_filter and c.get("document_type") != doc_type_filter:
                    continue
                if document_filter and c.get("document_name") != document_filter:
                    continue
                candidates.append((c, score, score, 0.0))

        if not candidates:
            return {
                "chunks": [],
                "has_sufficient_evidence": False,
                "top_score": 0.0,
                "debug_info": {
                    "original_query": query,
                    "clean_query": clean_query,
                    "retrieval_mode": "hybrid" if self.hybrid_enabled else "dense",
                    "candidates_examined": 0
                }
            }

        # For current queries, re-rank candidates to prefer documents with latest effective dates & version numbers
        if not is_historical:
            def version_rank(item):
                c_meta, score, d_score, l_score = item
                eff_date = str(c_meta.get("effective_date") or "")
                ver = str(c_meta.get("version") or "")
                year = str(c_meta.get("academic_year") or "")
                return (eff_date, ver, year, score)
            
            candidates = sorted(candidates, key=version_rank, reverse=True)

        # For historical queries with a target year, prefer candidates matching target_year
        elif is_historical and target_year:
            def historical_rank(item):
                c_meta, score, d_score, l_score = item
                year_str = str(c_meta.get("academic_year") or c_meta.get("version") or "")
                matches_target = 1 if target_year in year_str else 0
                return (matches_target, score)

            candidates = sorted(candidates, key=historical_rank, reverse=True)

        top_score = candidates[0][1]

        # 3. Threshold Filtering
        filtered_chunks = []
        debug_candidates = []

        for chunk_meta, score, d_score, l_score in candidates:
            passed = score >= thresh
            chunk_copy = dict(chunk_meta)
            chunk_copy["score"] = round(score, 4)
            chunk_copy["dense_score"] = round(d_score, 4)
            chunk_copy["lexical_score"] = round(l_score, 4)

            debug_candidates.append({
                "chunk_id": chunk_meta.get("chunk_id"),
                "document": chunk_meta.get("document_name"),
                "page": chunk_meta.get("page_number"),
                "score": round(score, 4),
                "dense_score": round(d_score, 4),
                "lexical_score": round(l_score, 4),
                "passed_threshold": passed
            })

            if passed and len(filtered_chunks) < k:
                filtered_chunks.append(chunk_copy)

        has_evidence = len(filtered_chunks) > 0

        debug_info = {
            "original_query": query,
            "clean_query": clean_query,
            "retrieval_mode": "hybrid" if self.hybrid_enabled else "dense",
            "threshold_applied": thresh,
            "top_score": round(top_score, 4),
            "candidates_examined": len(candidates),
            "intent_info": intent_info,
            "candidates": debug_candidates
        }

        return {
            "chunks": filtered_chunks,
            "has_sufficient_evidence": has_evidence,
            "top_score": round(top_score, 4),
            "debug_info": debug_info
        }
