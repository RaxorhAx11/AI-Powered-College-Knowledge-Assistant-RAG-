import sys
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever

def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    """Load evaluation questions dataset."""
    if not dataset_path.exists():
        print(f"Error: Dataset not found at '{dataset_path}'")
        sys.exit(1)
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_evaluation(mode: str = "hybrid", threshold: float = 0.35, top_k_max: int = 5):
    """
    Run quantitative retrieval evaluation on benchmark question dataset.
    """
    dataset_path = Path(__file__).resolve().parent.parent / "tests" / "data" / "evaluation_questions.json"
    questions = load_dataset(dataset_path)

    embedding_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
    vector_store = VectorStoreManager(
        index_path=Config.FAISS_INDEX_PATH,
        metadata_path=Config.METADATA_PATH
    )

    if not vector_store.is_indexed():
        print("Error: Knowledge base is not indexed. Run 'python scripts/ingest.py' first.")
        sys.exit(1)

    is_hybrid = (mode.lower() == "hybrid")
    retriever = KnowledgeRetriever(
        embedding_manager=embedding_mgr,
        vector_store=vector_store,
        top_k=top_k_max,
        similarity_threshold=threshold,
        hybrid_enabled=is_hybrid
    )

    total_q = len(questions)
    answerable_q = [q for q in questions if q.get("answerable", True)]
    unanswerable_q = [q for q in questions if not q.get("answerable", True)]

    recall_at_1_count = 0
    recall_at_3_count = 0
    recall_at_5_count = 0
    mrr_sum = 0.0
    doc_accuracy_count = 0
    correct_rejections = 0
    latencies_ms = []

    for q in answerable_q:
        start_t = time.perf_counter()
        res = retriever.retrieve(q["question"], top_k=top_k_max, threshold=threshold)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies_ms.append(elapsed_ms)

        retrieved_chunks = res["chunks"]
        expected_docs = set(q.get("expected_documents", []))
        expected_pages = set(q.get("expected_pages", []))

        rank_found = 0
        doc_matched = False

        for idx, chunk in enumerate(retrieved_chunks, 1):
            chunk_doc = chunk.get("document_name", chunk.get("document", ""))
            chunk_page = chunk.get("page_number", chunk.get("page", -1))

            if chunk_doc in expected_docs:
                doc_matched = True
                if not expected_pages or chunk_page in expected_pages:
                    if rank_found == 0:
                        rank_found = idx

        if doc_matched:
            doc_accuracy_count += 1

        if rank_found > 0:
            if rank_found == 1:
                recall_at_1_count += 1
            if rank_found <= 3:
                recall_at_3_count += 1
            if rank_found <= 5:
                recall_at_5_count += 1
            mrr_sum += (1.0 / rank_found)

    # Evaluate unanswerable questions
    for q in unanswerable_q:
        start_t = time.perf_counter()
        res = retriever.retrieve(q["question"], top_k=top_k_max, threshold=threshold)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies_ms.append(elapsed_ms)

        if not res["has_sufficient_evidence"] or not res["chunks"]:
            correct_rejections += 1

    num_ans = len(answerable_q)
    num_unans = len(unanswerable_q)

    recall_1 = (recall_at_1_count / num_ans * 100.0) if num_ans else 0.0
    recall_3 = (recall_at_3_count / num_ans * 100.0) if num_ans else 0.0
    recall_5 = (recall_at_5_count / num_ans * 100.0) if num_ans else 0.0
    mrr = (mrr_sum / num_ans) if num_ans else 0.0
    doc_acc = (doc_accuracy_count / num_ans * 100.0) if num_ans else 0.0
    rejection_rate = (correct_rejections / num_unans * 100.0) if num_unans else 100.0
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    print("==================================================")
    print("RAXEL RETRIEVAL EVALUATION REPORT")
    print("==================================================")
    print(f"Mode: {mode.upper()} (Dense Weight: {Config.DENSE_WEIGHT}, Lexical Weight: {Config.LEXICAL_WEIGHT})")
    print(f"Similarity Threshold: {threshold}")
    print(f"Total Questions: {total_q}")
    print(f"Answerable Questions: {num_ans}")
    print(f"Unanswerable Questions: {num_unans}")

    print(f"\nRecall@1: {recall_1:.1f}%")
    print(f"Recall@3: {recall_3:.1f}%")
    print(f"Recall@5: {recall_5:.1f}%")

    print(f"\nMRR (Mean Reciprocal Rank): {mrr:.2f}")
    print(f"Citation Document Accuracy: {doc_acc:.1f}%")
    print(f"Unknown Rejection Rate: {rejection_rate:.1f}%")
    print(f"Average Retrieval Latency: {avg_latency:.2f} ms")
    print("==================================================")

    return {
        "mode": mode,
        "threshold": threshold,
        "recall_1": recall_1,
        "recall_3": recall_3,
        "recall_5": recall_5,
        "mrr": mrr,
        "doc_acc": doc_acc,
        "rejection_rate": rejection_rate,
        "avg_latency": avg_latency
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAXEL retrieval performance.")
    parser.add_argument("--mode", type=str, default="hybrid", choices=["dense", "hybrid"], help="Retrieval mode")
    parser.add_argument("--threshold", type=float, default=0.35, help="Similarity threshold")
    args = parser.parse_args()

    run_evaluation(mode=args.mode, threshold=args.threshold)
