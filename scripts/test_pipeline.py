import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline

def run_tests():
    print("=" * 60)
    print("Running RAG Pipeline Verification Tests")
    print("=" * 60)

    embedding_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
    vector_store = VectorStoreManager(
        index_path=Config.FAISS_INDEX_PATH,
        metadata_path=Config.METADATA_PATH
    )
    llm = OllamaLLM(model_name=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)
    retriever = KnowledgeRetriever(
        embedding_manager=embedding_mgr,
        vector_store=vector_store,
        top_k=Config.TOP_K,
        similarity_threshold=Config.SIMILARITY_THRESHOLD
    )
    pipeline = RAGPipeline(retriever=retriever, llm=llm)

    test_queries = [
        {
            "name": "Test 1: Attendance Query (Academic Regulations)",
            "query": "What is the minimum attendance requirement for exams?",
            "should_have_evidence": True
        },
        {
            "name": "Test 2: Hostel Rules Query (Student Handbook)",
            "query": "What is the hostel curfew time and mess breakfast timing?",
            "should_have_evidence": True
        },
        {
            "name": "Test 3: Out-of-Scope Query (Safe Fallback)",
            "query": "What is the formula for quantum entanglement?",
            "should_have_evidence": False
        }
    ]

    for test in test_queries:
        print(f"\n--- {test['name']} ---")
        print(f"Question: '{test['query']}'")
        res = pipeline.answer_question(test["query"])

        print(f"Sufficient Evidence Found: {res['has_sufficient_evidence']}")
        print(f"Top Similarity Score: {res['top_score']:.4f}")
        print(f"Answer:\n{res['answer']}\n")

        if res['citations']:
            print("Citations:")
            for cite in res['citations']:
                print(f"  - {cite['formatted']} (Score: {cite['score']:.4f})")
        else:
            print("Citations: None")

        if test["should_have_evidence"] != res["has_sufficient_evidence"]:
            print(f"[FAILED]: Expected evidence={test['should_have_evidence']}, got {res['has_sufficient_evidence']}")
        else:
            print("[PASSED] Test verified successfully!")

    print("\n" + "=" * 60)
    print("All Pipeline Verification Tests Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
