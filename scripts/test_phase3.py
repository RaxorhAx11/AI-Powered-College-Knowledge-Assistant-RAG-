import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.hybrid_retriever import HybridRetriever
from src.query_preprocessor import QueryPreprocessor
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline

def test_phase3_suite():
    print("=" * 60)
    print("RUNNING PHASE 3 COMPREHENSIVE TEST SUITE (PROJECT RAXEL)")
    print("=" * 60)

    embedding_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
    vector_store = VectorStoreManager(index_path=Config.FAISS_INDEX_PATH, metadata_path=Config.METADATA_PATH)
    
    if not vector_store.is_indexed():
        print("Indexing documents for Phase 3 test suite...")
        processor = PDFProcessor()
        chunker = TextChunker()
        pages = processor.process_directory(Config.DOCUMENTS_DIR)
        chunks = chunker.chunk_documents(pages)
        texts = [c["text"] for c in chunks]
        embs = embedding_mgr.embed_texts(texts, normalize=True)
        vector_store.build_index(embs, chunks)

    llm = OllamaLLM(model_name=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)

    # 1. Query Preprocessor Test
    print("\n--- TEST 1: Query Preprocessing ---")
    raw_q = "  how much att req for exam???  "
    clean_q = QueryPreprocessor.preprocess(raw_q)
    assert "attendance" in clean_q, f"Failed to expand abbreviation in query: {clean_q}"
    print(f"[PASSED] Query preprocessing normalized: '{raw_q.strip()}' -> '{clean_q}'")

    # 2. Dense Retrieval Test
    print("\n--- TEST 2: Dense Retrieval ---")
    dense_retriever = KnowledgeRetriever(embedding_manager=embedding_mgr, vector_store=vector_store, hybrid_enabled=False)
    res_dense = dense_retriever.retrieve("What is the minimum attendance requirement?")
    assert res_dense["has_sufficient_evidence"] is True, "Dense retrieval failed"
    print("[PASSED] Dense retrieval returned candidate chunks.")

    # 3. Top-K Ordering Test
    print("\n--- TEST 3: Top-K Ordering ---")
    res_k = dense_retriever.retrieve("attendance requirement", top_k=3)
    scores = [c["score"] for c in res_k["chunks"]]
    assert scores == sorted(scores, reverse=True), f"Top-K chunks not ordered by score: {scores}"
    print(f"[PASSED] Top-K chunks strictly sorted by similarity score: {scores}")

    # 4. Threshold Rejection Test
    print("\n--- TEST 4: Threshold Rejection ---")
    res_thresh = dense_retriever.retrieve("quantum entanglement physics equation", threshold=0.35)
    assert res_thresh["has_sufficient_evidence"] is False, "Threshold failed to reject irrelevant query"
    print("[PASSED] Similarity threshold correctly rejected irrelevant query.")

    # 5. Paraphrased Question Test
    print("\n--- TEST 5: Paraphrased Query Retrieval ---")
    res_para = dense_retriever.retrieve("How many classes do I need to attend to write finals?")
    assert res_para["has_sufficient_evidence"] is True, "Paraphrased query failed to retrieve context"
    print("[PASSED] Paraphrased query successfully retrieved attendance evidence.")

    # 6. Exact Keyword Query Test
    print("\n--- TEST 6: Exact Keyword Query ---")
    res_key = dense_retriever.retrieve("75% attendance End-Semester Examinations")
    assert res_key["has_sufficient_evidence"] is True, "Exact keyword query failed"
    print("[PASSED] Exact keyword query retrieved matching chunks.")

    # 7. Metadata Preservation Test
    print("\n--- TEST 7: Chunk Metadata Preservation ---")
    chunk_sample = vector_store.metadata[0]
    required_keys = ["document_name", "page_number", "source_path", "document_type", "chunk_id"]
    for k in required_keys:
        assert k in chunk_sample, f"Missing required metadata key: {k}"
    print(f"[PASSED] All rich metadata keys preserved in stored vector chunks.")

    # 8. Document Filtering Test
    print("\n--- TEST 8: Document Metadata Filtering ---")
    res_filtered = dense_retriever.retrieve("hostel curfew", document_filter="Student_Handbook.pdf")
    docs_retrieved = set(c["document_name"] for c in res_filtered["chunks"])
    assert docs_retrieved == {"Student_Handbook.pdf"}, f"Document filter failed: {docs_retrieved}"
    print(f"[PASSED] Document metadata filter restricted search to: {docs_retrieved}")

    # 9. Version Metadata Test
    print("\n--- TEST 9: Version Metadata Preservation ---")
    has_ver_field = any("version_str" in c for c in vector_store.metadata)
    assert has_ver_field is True, "Version metadata field missing from vector store"
    print("[PASSED] Version string metadata field intact.")

    # 10. Duplicate Context Reduction Test
    print("\n--- TEST 10: Duplicate Context Control ---",)
    hybrid_retriever = HybridRetriever(vector_store=vector_store, embedding_manager=embedding_mgr)
    raw_hybrid = hybrid_retriever.retrieve_hybrid("attendance requirement", top_k=10)
    seen_snips = set(c[0]["text"][:100] for c in raw_hybrid)
    assert len(seen_snips) == len(raw_hybrid), "Duplicate chunk text present in hybrid retrieval results"
    print(f"[PASSED] Deduplication control verified on {len(raw_hybrid)} candidate chunks.")

    # 11. Citation Metadata Verification
    print("\n--- TEST 11: Citation Metadata Integrity ---")
    pipeline = RAGPipeline(retriever=dense_retriever, llm=llm)
    rag_res = pipeline.answer_question("What is the hostel curfew time?")
    assert len(rag_res["citations"]) > 0, "Citations empty for valid question"
    assert "Student_Handbook" in rag_res["citations"][0]["document"], "Citation document mismatch"
    print(f"[PASSED] Citation metadata verified: {rag_res['citations'][0]['formatted']}")

    # 12. Unknown Question Safe Fallback Test
    print("\n--- TEST 12: Unknown Question Safe Fallback ---")
    fallback_res = pipeline.answer_question("Who won the 2024 ICC World Cup?")
    assert fallback_res["has_sufficient_evidence"] is False, "Unknown query failed to trigger fallback"
    assert len(fallback_res["citations"]) == 0, "Unknown query generated illegal citations"
    print("[PASSED] Unknown query correctly triggered safe fallback without hallucination.")

    # 13. Hybrid Retrieval Test
    print("\n--- TEST 13: Hybrid Retrieval Execution ---")
    hybrid_ret = KnowledgeRetriever(embedding_manager=embedding_mgr, vector_store=vector_store, hybrid_enabled=True)
    res_hyb = hybrid_ret.retrieve("hostel curfew 9:30 PM")
    assert res_hyb["has_sufficient_evidence"] is True, "Hybrid retrieval failed"
    print(f"[PASSED] Hybrid retrieval executed successfully (Top Score: {res_hyb['top_score']:.4f}).")

    # 14. Phase 1 Regression Suite Verification
    print("\n--- TEST 14: Phase 1 Regression Suite Check ---")
    root_dir = Path(__file__).resolve().parent.parent
    p1_code = subprocess.run([sys.executable, "scripts/test_pipeline.py"], cwd=root_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert p1_code.returncode == 0, f"Phase 1 regression tests failed: {p1_code.stderr}"
    print("[PASSED] Phase 1 regression test suite passed cleanly.")

    # 15. Phase 2 Regression Suite Verification
    print("\n--- TEST 15: Phase 2 Regression Suite Check ---")
    p2_code = subprocess.run([sys.executable, "scripts/test_phase2.py"], cwd=root_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert p2_code.returncode == 0, f"Phase 2 regression tests failed: {p2_code.stderr}"
    print("[PASSED] Phase 2 regression test suite passed cleanly.")

    print("\n" + "=" * 60)
    print("ALL 15 PHASE 3 COMPREHENSIVE TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_phase3_suite()
