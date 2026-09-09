import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline

def run_rag_evaluation(sample_size: int = 50, output_path: str = "evaluation_results.json", dataset_file: str = "tests/data/gls_evaluation_questions.json"):
    """
    Execute Phase 5 synthetic-document RAG pipeline evaluation and output detailed summary report & JSON logs.
    """
    dataset_path = Path(__file__).resolve().parent.parent / dataset_file
    if not dataset_path.exists():
        dataset_path = Path(__file__).resolve().parent.parent / "tests" / "data" / "evaluation_questions.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    eval_sample = questions[:sample_size]

    embedding_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
    vector_store = VectorStoreManager(index_path=Config.FAISS_INDEX_PATH, metadata_path=Config.METADATA_PATH)
    llm = OllamaLLM(model_name=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)
    retriever = KnowledgeRetriever(
        embedding_manager=embedding_mgr, 
        vector_store=vector_store, 
        top_k=Config.TOP_K,
        similarity_threshold=Config.SIMILARITY_THRESHOLD
    )
    pipeline = RAGPipeline(retriever=retriever, llm=llm)

    total_questions = len(eval_sample)
    answerable_count = sum(1 for q in eval_sample if q.get("answerable", True))
    unsupported_count = total_questions - answerable_count

    correct_answers = 0
    correct_citations = 0
    complete_citations = 0
    correct_unsupported_rejections = 0
    multipart_success = 0
    multipart_total = 0
    conflict_success = 0
    conflict_total = 0
    followup_success = 0
    followup_total = 0
    injection_success = 0
    injection_total = 0

    total_latency = 0.0
    retrieval_latencies = []
    
    evaluation_records = []

    print("==================================================")
    print("RAXEL PHASE 5 SYNTHETIC-DOCUMENT EVALUATION")
    print("==================================================")

    for idx, q in enumerate(eval_sample, 1):
        q_id = q.get("id", f"Q{idx:03d}")
        category = q.get("category", "general")
        question_text = q["question"]
        answerable = q.get("answerable", True)
        expected_docs = set(q.get("expected_documents", []))
        expected_keywords = q.get("expected_keywords", [])

        print(f"\n[{idx}/{total_questions}] [{category.upper()}] ({q_id}): '{question_text}'", flush=True)
        
        t0 = time.time()
        res = pipeline.answer_question(question_text)
        total_lat = time.time() - t0
        total_latency += total_lat

        answer = res["answer"]
        citations = res["citations"]
        retrieved_chunks = res["retrieved_chunks"]
        has_evidence = res["has_sufficient_evidence"]
        is_fallback = res.get("is_fallback", False)
        has_conflict = res.get("has_conflict", False)

        retrieved_docs = set(c.get("document_name", c.get("document", "")) for c in retrieved_chunks)
        cited_docs = set(c.get("document", "") for c in citations)

        # Track category stats
        if category == "multi_part" or category == "multi_chunk":
            multipart_total += 1
        elif category == "conflicting_evidence":
            conflict_total += 1
        elif category == "follow_up":
            followup_total += 1
        elif category == "prompt_injection":
            injection_total += 1

        is_correct_answer = False
        is_correct_citation = False
        is_correct_unsupported = False

        if answerable:
            # Answer is correct if grounded evidence was used and key content matches expected keywords
            has_keywords = any(kw.lower() in answer.lower() for kw in expected_keywords) if expected_keywords else True
            if has_evidence and not is_fallback and has_keywords:
                is_correct_answer = True
                correct_answers += 1

            # Citation correctness: cited docs must be subset of actual retrieved docs and match expected docs
            if citations and cited_docs.issubset(retrieved_docs) and (not expected_docs or cited_docs.intersection(expected_docs)):
                is_correct_citation = True
                correct_citations += 1
                complete_citations += 1

            if (category == "multi_part" or category == "multi_chunk") and is_correct_answer:
                multipart_success += 1
            if category == "conflicting_evidence" and (has_conflict or is_correct_answer):
                conflict_success += 1
            if category == "follow_up" and is_correct_answer:
                followup_success += 1
            if category == "prompt_injection" and is_correct_answer:
                # Injection resisted if system answered question without revealing system prompt / secrets
                if "secret" not in answer.lower() and "system prompt" not in answer.lower():
                    injection_success += 1

            print(f"  Result: Grounded Answer | Correct: {is_correct_answer} | Citations: {list(cited_docs)}", flush=True)

        else:
            # Unsupported question: must trigger safe fallback and output 0 citations
            if (not has_evidence or is_fallback) and len(citations) == 0:
                is_correct_unsupported = True
                correct_unsupported_rejections += 1
                correct_answers += 1
                print("  Result: Safe Fallback Triggered Correctly (No fake citation)", flush=True)
            else:
                print("  Result: [FAIL] Hallucination warning on unsupported query!", flush=True)

            if category == "prompt_injection":
                if "secret" not in answer.lower() and "system prompt" not in answer.lower():
                    injection_success += 1

        record = {
            "id": q_id,
            "category": category,
            "question": question_text,
            "expected_documents": list(expected_docs),
            "retrieved_documents": list(retrieved_docs),
            "generated_answer": answer,
            "generated_citations": [c.get("formatted") for c in citations],
            "has_sufficient_evidence": has_evidence,
            "is_fallback": is_fallback,
            "has_conflict": has_conflict,
            "is_correct_answer": is_correct_answer if answerable else is_correct_unsupported,
            "is_valid_citation": is_correct_citation if answerable else True,
            "latency_sec": round(total_lat, 2)
        }
        evaluation_records.append(record)

    # Calculate overall metrics
    ans_correctness_pct = (correct_answers / total_questions) * 100.0 if total_questions else 0.0
    cite_correctness_pct = (correct_citations / answerable_count) * 100.0 if answerable_count else 0.0
    cite_completeness_pct = (complete_citations / answerable_count) * 100.0 if answerable_count else 0.0
    unsupported_rejection_pct = (correct_unsupported_rejections / unsupported_count) * 100.0 if unsupported_count else 0.0
    multipart_pct = (multipart_success / multipart_total) * 100.0 if multipart_total else 100.0
    conflict_pct = (conflict_success / conflict_total) * 100.0 if conflict_total else 100.0
    followup_pct = (followup_success / followup_total) * 100.0 if followup_total else 100.0
    avg_latency = total_latency / total_questions if total_questions else 0.0

    print("\n==================================================")
    print("RAXEL PHASE 5 SYNTHETIC-DOCUMENT EVALUATION SUMMARY")
    print("==================================================")
    print(f"Total questions: {total_questions}")
    print(f"Answer correctness: {ans_correctness_pct:.1f}%")
    print(f"Citation correctness: {cite_correctness_pct:.1f}%")
    print(f"Citation completeness: {cite_completeness_pct:.1f}%")
    print(f"Unsupported rejection: {unsupported_rejection_pct:.1f}%")
    print(f"Multi-part success: {multipart_pct:.1f}%")
    print(f"Conflict handling: {conflict_pct:.1f}%")
    print(f"Follow-up success: {followup_pct:.1f}%")
    print(f"Average total response latency: {avg_latency:.2f} sec")
    print("==================================================")

    # Save detailed evaluation records for manual evaluation support
    out_file = Path(output_path)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "total_questions": total_questions,
                "answer_correctness_pct": ans_correctness_pct,
                "citation_correctness_pct": cite_correctness_pct,
                "citation_completeness_pct": cite_completeness_pct,
                "unsupported_rejection_pct": unsupported_rejection_pct,
                "multipart_success_pct": multipart_pct,
                "conflict_handling_pct": conflict_pct,
                "followup_success_pct": followup_pct,
                "avg_total_latency_sec": round(avg_latency, 2)
            },
            "records": evaluation_records
        }, f, indent=2)

    print(f"\n[+] Detailed evaluation log saved to `{output_path}`.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=50, help="Number of questions to evaluate (default 50)")
    parser.add_argument("--dataset", type=str, default="tests/data/gls_evaluation_questions.json", help="Path to evaluation questions JSON")
    parser.add_argument("--output", type=str, default="evaluation_results.json", help="Path to output JSON")
    args = parser.parse_args()

    run_rag_evaluation(sample_size=args.sample, output_path=args.output, dataset_file=args.dataset)
