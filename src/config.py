import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Base Project Directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Central configuration class for College Knowledge Assistant (RAXEL)."""
    
    BASE_DIR: Path = BASE_DIR
    # Storage Paths
    DATA_DIR: Path = BASE_DIR / "data"
    DOCUMENTS_DIR: Path = BASE_DIR / os.getenv("DOCUMENTS_DIR", "data/documents")
    VECTORSTORE_DIR: Path = BASE_DIR / os.getenv("VECTORSTORE_DIR", "data/vectorstore")
    BACKUPS_DIR: Path = BASE_DIR / os.getenv("BACKUPS_DIR", "data/backups")

    # Auth Database
    AUTH_DATABASE_PATH: Path = BASE_DIR / os.getenv("AUTH_DATABASE_PATH", "data/raxel.db")
    
    # Vector Index & Metadata Files
    FAISS_INDEX_PATH: Path = VECTORSTORE_DIR / "index.faiss"
    METADATA_PATH: Path = VECTORSTORE_DIR / "metadata.pkl"

    # Local Embedding Model
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    
    # AI / LLM Providers (Gemini API & Local Ollama)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    
    # Gemini API Settings (Primary/Default)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    AVAILABLE_GEMINI_MODELS: list = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"]
    
    # Local LLM (Ollama Settings)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3:latest")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    AVAILABLE_OLLAMA_MODELS: list = ["llama3:latest", "llama3", "mistral", "phi3"]
    
    # Text Chunking Settings
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    MIN_CHUNK_SIZE: int = int(os.getenv("MIN_CHUNK_SIZE", "80"))
    
    # Retrieval & Evidence Gating Settings
    RETRIEVAL_MODE: str = os.getenv("RETRIEVAL_MODE", "hybrid")
    HYBRID_ENABLED: bool = os.getenv("HYBRID_ENABLED", "true").lower() in ("true", "1", "yes")
    DENSE_WEIGHT: float = float(os.getenv("DENSE_WEIGHT", "0.7"))
    LEXICAL_WEIGHT: float = float(os.getenv("LEXICAL_WEIGHT", "0.3"))
    TOP_K: int = int(os.getenv("TOP_K", "4"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
    EVIDENCE_MIN_SCORE: float = float(os.getenv("EVIDENCE_MIN_SCORE", "0.35"))
    MIN_RELEVANT_CHUNKS: int = int(os.getenv("MIN_RELEVANT_CHUNKS", "1"))
    EVIDENCE_KEYWORD_MATCH: bool = os.getenv("EVIDENCE_KEYWORD_MATCH", "true").lower() in ("true", "1", "yes")

    # OCR Settings
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() in ("true", "1", "yes")
    OCR_MIN_TEXT_LENGTH: int = int(os.getenv("OCR_MIN_TEXT_LENGTH", "50"))

    # Document Upload Settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS: set = {".pdf"}

    # Developer Debug Settings
    RAG_DEBUG: bool = os.getenv("RAG_DEBUG", "false").lower() in ("true", "1", "yes")

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        cls.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        cls.AUTH_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Instantiate and ensure directories on load
Config.ensure_directories()
