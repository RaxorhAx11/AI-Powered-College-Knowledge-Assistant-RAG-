"""
FastAPI Dependencies and Component Singletons for RAXEL.
"""

import secrets
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends, Header, Cookie

from src.config import Config
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline
from src.document_manager import DocumentManager
from src.quality_control import QualityControlManager
from src.system_diagnostics import SystemDiagnosticsManager
from src.permissions import has_role, ROLE_STUDENT

import json
from pathlib import Path

# Active Session Storage (Token -> User Dict)
SESSIONS_FILE = Path("data/sessions.json")
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

def _load_sessions():
    global ACTIVE_SESSIONS
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                ACTIVE_SESSIONS = json.load(f)
    except Exception as e:
        ACTIVE_SESSIONS = {}

def _save_sessions():
    try:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(ACTIVE_SESSIONS, f, indent=2)
    except Exception as e:
        pass

_load_sessions()

def create_session(user_dict: Dict[str, Any]) -> str:
    """Create a new session token for authenticated user."""
    token = secrets.token_hex(32)
    ACTIVE_SESSIONS[token] = {
        "id": user_dict["id"],
        "username": user_dict["username"],
        "role": user_dict["role"],
        "authenticated": True
    }
    _save_sessions()
    return token

def revoke_session(token: Optional[str]) -> bool:
    """Revoke an active session token."""
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
        _save_sessions()
        return True
    return False

# Singletons Container
class ComponentRegistry:
    _embedding_manager: Optional[EmbeddingManager] = None
    _vector_store: Optional[VectorStoreManager] = None
    _llm: Optional[OllamaLLM] = None
    _retriever: Optional[KnowledgeRetriever] = None
    _rag_pipeline: Optional[RAGPipeline] = None
    _doc_manager: Optional[DocumentManager] = None
    _qc_manager: Optional[QualityControlManager] = None
    _diag_manager: Optional[SystemDiagnosticsManager] = None

    @classmethod
    def initialize(cls):
        Config.ensure_directories()
        if cls._embedding_manager is None:
            cls._embedding_manager = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
        if cls._vector_store is None:
            cls._vector_store = VectorStoreManager(
                index_path=Config.FAISS_INDEX_PATH,
                metadata_path=Config.METADATA_PATH
            )
        if cls._llm is None:
            cls._llm = OllamaLLM(model_name=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)
        if cls._retriever is None:
            cls._retriever = KnowledgeRetriever(
                vector_store=cls._vector_store,
                embedding_manager=cls._embedding_manager
            )
        if cls._rag_pipeline is None:
            cls._rag_pipeline = RAGPipeline(retriever=cls._retriever, llm=cls._llm)
        if cls._doc_manager is None:
            cls._doc_manager = DocumentManager()
        if cls._qc_manager is None:
            cls._qc_manager = QualityControlManager()
        if cls._diag_manager is None:
            cls._diag_manager = SystemDiagnosticsManager()

    @classmethod
    def get_rag_pipeline(cls) -> RAGPipeline:
        if cls._rag_pipeline is None:
            cls.initialize()
        return cls._rag_pipeline

    @classmethod
    def get_doc_manager(cls) -> DocumentManager:
        if cls._doc_manager is None:
            cls.initialize()
        return cls._doc_manager

    @classmethod
    def get_qc_manager(cls) -> QualityControlManager:
        if cls._qc_manager is None:
            cls.initialize()
        return cls._qc_manager

    @classmethod
    def get_diag_manager(cls) -> SystemDiagnosticsManager:
        if cls._diag_manager is None:
            cls.initialize()
        return cls._diag_manager

    @classmethod
    def reload_vector_store(cls):
        """Reload vector store index & metadata from disk and re-init BM25 in retriever."""
        if cls._vector_store is None:
            cls.initialize()
        else:
            cls._vector_store.load()
        if cls._retriever and hasattr(cls._retriever, 'hybrid_retriever'):
            cls._retriever.hybrid_retriever.vector_store = cls._vector_store
            cls._retriever.hybrid_retriever._init_bm25()

def get_session_token_from_request(request: Request, authorization: Optional[str] = Header(None), raxel_session: Optional[str] = Cookie(None)) -> Optional[str]:
    """Extract session token from Cookie, Query param, or Authorization header."""
    if raxel_session:
        return raxel_session
    token_param = request.query_params.get("token")
    if token_param:
        return token_param
    if authorization:
        parts = authorization.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return authorization
    return None

def get_current_user_optional(token: Optional[str] = Depends(get_session_token_from_request)) -> Dict[str, Any]:
    """
    Retrieve current user context. Returns Guest Student context if token missing/invalid.
    """
    if token and token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[token]
    
    return {
        "authenticated": False,
        "id": None,
        "username": "Guest Student",
        "role": ROLE_STUDENT
    }

def get_current_user(user: Dict[str, Any] = Depends(get_current_user_optional)) -> Dict[str, Any]:
    """
    Require authenticated user.
    """
    if not user.get("authenticated", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in as a registered user."
        )
    return user

def require_role(required_role: str):
    """
    FastAPI dependency factory enforcing server-side RBAC role permissions.
    """
    def dependency(user: Dict[str, Any] = Depends(get_current_user_optional)):
        user_role = user.get("role", ROLE_STUDENT)
        is_auth = user.get("authenticated", False)

        if required_role == ROLE_STUDENT:
            return user
        
        if not is_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication required to access {required_role} resources."
            )
        
        if not has_role(user_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You do not have permissions for {required_role} access."
            )
        return user
    return dependency
