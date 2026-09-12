from typing import Dict, Any, List, Optional
import logging
import time

from src.retriever import KnowledgeRetriever
from src.llm import BaseLLMProvider, OllamaLLM, get_llm_provider
from src.prompt_builder import get_system_prompt, build_user_prompt
from src.citation_validator import validate_and_sanitize_answer_citations
from src.answer_validator import (
    validate_rag_response, 
    is_ambiguous_query, 
    evaluate_pre_llm_evidence_sufficiency,
    format_partial_answer_notice,
    SAFE_FALLBACK_TEXT, 
    AMBIGUOUS_CLARIFICATION_TEXT
)
from src.query_resolver import resolve_followup_query

logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    Phase 5 RAXEL Grounded RAG Pipeline.
    Orchestrates evidence retrieval, injection-resistant context assembly,
    grounding-first generation, programmatic citation validation, safe fallback,
    and ambiguous query clarification prompts.
    """

    def __init__(self, retriever: KnowledgeRetriever, llm: BaseLLMProvider):
        self.retriever = retriever
        self.llm = llm

    def answer_question(
        self, 
        question: str, 
        chat_history: Optional[List[Dict[str, str]]] = None,
        doc_type_filter: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute Phase 5 grounded RAG workflow for a student question.
        """
        start_time = time.time()
        effective_llm = get_llm_provider(provider_name=provider, model_name=model) if (provider or model) else self.llm
        logger.info(f"Processing student question: '{question}' using provider '{getattr(effective_llm, 'provider_id', 'llm')}' and model '{getattr(effective_llm, 'model_name', '')}'")

        # 0. Query Context Resolution for follow-up questions (using USER history ONLY)
        search_query = question
        was_resolved = False
        if chat_history:
            search_query, was_resolved = resolve_followup_query(question, chat_history, llm=effective_llm)
            if was_resolved:
                logger.info(f"Resolved follow-up query: '{question}' -> '{search_query}'")

        # 0b. Check for overly ambiguous queries
        if is_ambiguous_query(search_query):
            elapsed = time.time() - start_time
            return {
                "answer": AMBIGUOUS_CLARIFICATION_TEXT,
                "citations": [],
                "retrieved_chunks": [],
                "has_sufficient_evidence": False,
                "is_fallback": False,
                "is_ambiguous": True,
                "has_conflict": False,
                "top_score": 0.0,
                "latency_sec": round(elapsed, 3),
                "debug_info": {"query_status": "ambiguous_query", "resolved_query": search_query},
                "validation_info": {"notes": ["Ambiguous query detected; returned clarification prompt."]}
            }

        # 1. Retrieve evidence chunks with resolved search_query
        retrieval_res = self.retriever.retrieve(search_query, doc_type_filter=doc_type_filter)
        chunks = retrieval_res.get("chunks", [])
        top_score = retrieval_res.get("top_score", 0.0)
        debug_info = retrieval_res.get("debug_info", {})
        debug_info["resolved_query"] = search_query
        debug_info["was_resolved"] = was_resolved

        # 2. Pre-LLM Evidence Gate (score + term coverage evaluation)
        gate_res = evaluate_pre_llm_evidence_sufficiency(
            search_query, 
            chunks, 
            top_score, 
            min_score_threshold=self.retriever.similarity_threshold
        )
        has_evidence = gate_res["has_sufficient_evidence"]

        if not has_evidence or not chunks:
            logger.info(f"Pre-LLM Evidence Gate failed ({gate_res['reason']}). Triggering safe fallback.")
            elapsed = time.time() - start_time
            return {
                "answer": SAFE_FALLBACK_TEXT,
                "citations": [],
                "retrieved_chunks": [],
                "has_sufficient_evidence": False,
                "is_fallback": True,
                "is_ambiguous": False,
                "has_conflict": False,
                "top_score": top_score,
                "latency_sec": round(elapsed, 3),
                "debug_info": debug_info,
                "validation_info": {"notes": [f"Pre-LLM Evidence Gate failed: {gate_res['reason']}"]}
            }

        # 3. Build grounding-first prompt & system prompt
        system_prompt = get_system_prompt()
        user_prompt = build_user_prompt(search_query, chunks, chat_history=chat_history)

        # 4. Invoke LLM for grounded answer generation
        raw_answer = effective_llm.generate(user_prompt, system_prompt=system_prompt)

        # 5. Citation validation: programmatically derive and sanitize citations
        citation_res = validate_and_sanitize_answer_citations(raw_answer, chunks)
        sanitized_answer = citation_res["sanitized_answer"]
        programmatic_citations = citation_res["validated_citations"]

        # 6. Answer grounding & evidence sufficiency validation
        validation_res = validate_rag_response(
            question=search_query,
            raw_answer=sanitized_answer,
            retrieved_chunks=chunks,
            retrieval_has_evidence=has_evidence,
            top_score=top_score,
            min_score_threshold=self.retriever.similarity_threshold
        )

        final_answer = validation_res["final_answer"]
        if gate_res.get("is_partial_evidence") and gate_res.get("missing_keywords") and not validation_res["is_fallback"]:
            missing_terms = gate_res["missing_keywords"]
            if not any(term in final_answer.lower() for term in missing_terms):
                final_answer = format_partial_answer_notice(final_answer, missing_terms)
        is_fallback = validation_res["is_fallback"]
        is_ambiguous = validation_res.get("is_ambiguous", False)
        has_conflict = validation_res["has_conflict"]
        sufficient_evidence = validation_res["has_sufficient_evidence"]

        final_citations = programmatic_citations if (sufficient_evidence and not is_fallback and not is_ambiguous) else []

        elapsed = time.time() - start_time
        logger.info(f"Answer generated in {elapsed:.2f}s | Sufficient: {sufficient_evidence} | Citations: {len(final_citations)}")

        return {
            "answer": final_answer,
            "citations": final_citations,
            "retrieved_chunks": chunks,
            "has_sufficient_evidence": sufficient_evidence,
            "is_fallback": is_fallback,
            "is_ambiguous": is_ambiguous,
            "has_conflict": has_conflict,
            "top_score": top_score,
            "latency_sec": round(elapsed, 3),
            "debug_info": debug_info,
            "validation_info": {
                "hallucinations_detected": citation_res["hallucinations_detected"],
                "notes": validation_res["validation_notes"],
                "conflict_message": validation_res.get("conflict_message", "")
            }
        }
