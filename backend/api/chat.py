"""
RAG & Chat API Router (Phase 7.3).
Exposes grounded college RAG pipeline to both Guest Students and registered users.
Preserves existing src/rag_pipeline.py evidence gating, follow-ups, and citation formatting.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import ComponentRegistry, get_current_user_optional

router = APIRouter(prefix="/api/chat", tags=["Chat & RAG"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Student question")
    conversation_id: Optional[str] = None
    doc_type_filter: Optional[str] = None
    chat_history: Optional[List[ChatMessage]] = None
    provider: Optional[str] = Field(None, description="AI provider: gemini or ollama")
    model: Optional[str] = Field(None, description="Specific model name for provider")

class CitationItem(BaseModel):
    document_name: str
    page_number: int
    document_type: Optional[str] = "document"
    version: Optional[str] = "1.0"
    effective_date: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    has_sufficient_evidence: bool
    is_fallback: bool
    is_ambiguous: bool
    has_conflict: bool
    top_score: float
    latency_sec: float
    conversation_id: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None
    validation_info: Optional[Dict[str, Any]] = None

def sanitize_for_pydantic(data: Any) -> Any:
    """Recursively convert numpy types or non-standard objects into standard Python types."""
    if isinstance(data, dict):
        return {k: sanitize_for_pydantic(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_pydantic(i) for i in data]
    elif hasattr(data, "item"):  # numpy scalars like np.bool_, np.int64, np.float64
        return data.item()
    return data

@router.get("/providers")
def get_providers():
    """Retrieve available AI providers (Gemini & Ollama) and their models."""
    from src.config import Config
    from src.llm import get_llm_provider

    gemini_p = get_llm_provider("gemini")
    ollama_p = get_llm_provider("ollama")

    gemini_status = gemini_p.check_connection()
    ollama_status = ollama_p.check_connection()

    return {
        "default_provider": Config.LLM_PROVIDER,
        "default_gemini_model": Config.GEMINI_MODEL,
        "default_ollama_model": Config.LLM_MODEL,
        "providers": [
            {
                "id": "gemini",
                "name": "Gemini API",
                "description": "Primary Google Cloud LLM (Fast, high intelligence)",
                "models": Config.AVAILABLE_GEMINI_MODELS,
                "configured": bool(Config.GEMINI_API_KEY),
                "available": gemini_status.get("available", False),
                "status_message": gemini_status.get("message", "")
            },
            {
                "id": "ollama",
                "name": "Local Ollama",
                "description": "Local offline LLM (Privacy-focused)",
                "models": Config.AVAILABLE_OLLAMA_MODELS,
                "configured": True,
                "available": ollama_status.get("available", False),
                "status_message": ollama_status.get("message", "")
            }
        ]
    }

@router.post("", response_model=ChatResponse)
def ask_chat(payload: ChatRequest, user: dict = Depends(get_current_user_optional)):
    """
    Process question through RAXEL Grounded RAG Pipeline.
    Supports both Guest Students and Authenticated Users.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )
    
    # Convert chat_history model objects to list of dicts for RAG pipeline
    history_list = None
    if payload.chat_history:
        history_list = [
            {"role": msg.role, "content": msg.content}
            for msg in payload.chat_history
        ]

    try:
        pipeline = ComponentRegistry.get_rag_pipeline()
        
        rag_result = pipeline.answer_question(
            question=payload.message.strip(),
            chat_history=history_list,
            doc_type_filter=payload.doc_type_filter,
            provider=payload.provider,
            model=payload.model
        )
        
        sanitized = sanitize_for_pydantic(rag_result)

        return {
            "answer": str(sanitized.get("answer", "")),
            "citations": sanitized.get("citations", []),
            "has_sufficient_evidence": bool(sanitized.get("has_sufficient_evidence", False)),
            "is_fallback": bool(sanitized.get("is_fallback", False)),
            "is_ambiguous": bool(sanitized.get("is_ambiguous", False)),
            "has_conflict": bool(sanitized.get("has_conflict", False)),
            "top_score": float(sanitized.get("top_score", 0.0)),
            "latency_sec": float(sanitized.get("latency_sec", 0.0)),
            "conversation_id": payload.conversation_id,
            "debug_info": sanitized.get("debug_info"),
            "validation_info": sanitized.get("validation_info")
        }
    except Exception as e:
        import logging
        logging.exception("Error in /api/chat ask_chat endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAXEL RAG Error: {str(e)}"
        )
