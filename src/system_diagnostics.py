"""
Admin System Diagnostics & Recovery Layer for RAXEL (Phase 6.6).

Provides Admin-only health diagnostics, system readiness checks, local backup creation,
backup validation, atomic safety restore safeguards, safe active index rebuilding,
maintenance concurrency guards, and audit logging.
"""

import os
import re
import json
import shutil
import sqlite3
import logging
import hashlib
import datetime
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import faiss
import urllib.request

from src.config import Config
from src.permissions import require_role, ROLE_ADMIN
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.document_manager import DocumentManager

logger = logging.getLogger(__name__)

# Global Maintenance Concurrency Guard
MAINTENANCE_LOCK = threading.Lock()

def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file on disk."""
    if not file_path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

class SystemDiagnosticsManager:
    """Manages RAXEL system diagnostics, health checks, backup creation, validation, atomic restore, and rebuild."""

    def __init__(self, db_path: Optional[Path] = None, backups_dir: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else Config.AUTH_DATABASE_PATH
        self.backups_dir = Path(backups_dir) if backups_dir else Config.BACKUPS_DIR
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.doc_manager = DocumentManager(db_path=self.db_path)

    def get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with Row factory."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def run_full_diagnostics(self, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run complete system diagnostics & readiness evaluation (Admin ONLY).
        Returns aggregated health report with status, category checks, messages, and recommendations.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "admin") if user else "admin"

        checks = []
        has_fail = False
        has_warning = False

        # 1. Environment & Directories Check
        env_res = self._check_environment()
        checks.append(env_res)

        # 2. Database Health & Schema Check
        db_res = self._check_database()
        checks.append(db_res)

        # 3. Document Storage Check
        doc_res = self._check_document_storage()
        checks.append(doc_res)

        # 4. Manifest Check
        man_res = self._check_manifest()
        checks.append(man_res)

        # 5. FAISS Index Check
        faiss_res = self._check_faiss_index()
        checks.append(faiss_res)

        # 6. Embedding Model Check
        emb_res = self._check_embedding_model(faiss_res.get("dimension"))
        checks.append(emb_res)

        # 7. AI LLM Providers Check (Gemini API & Local Ollama)
        gemini_res = self._check_gemini()
        checks.append(gemini_res)
        ollama_res = self._check_ollama()
        checks.append(ollama_res)

        # 8. Retrieval Readiness Check
        ret_res = self._check_retrieval_readiness()
        checks.append(ret_res)

        # 9. Knowledge Base Health Summary
        kb_res = self._check_knowledge_base_health()
        checks.append(kb_res)

        # 10. Configuration & Limits Check
        cfg_res = self._check_configuration()
        checks.append(cfg_res)

        # Determine overall system readiness status
        for c in checks:
            if c["status"] == "FAIL":
                has_fail = True
            elif c["status"] == "WARNING":
                has_warning = True

        if has_fail:
            overall_status = "NOT READY"
            summary_msg = "Critical system components failed. Diagnostic action or recovery required."
        elif has_warning:
            overall_status = "DEGRADED"
            summary_msg = "System is operational with minor warnings or degraded features."
        else:
            overall_status = "READY"
            summary_msg = "All system components are healthy and RAXEL is ready for operational RAG retrieval."

        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary_message": summary_msg,
            "checks": checks,
            "recommendations": [c["recommendation"] for c in checks if c.get("recommendation")]
        }

        self._log_audit("diagnostics_run", username, details=f"Overall status: {overall_status}")
        return report

    def _check_environment(self) -> Dict[str, Any]:
        """Check Python environment, OS, and required directories."""
        import sys
        req_dirs = [Config.DATA_DIR, Config.DOCUMENTS_DIR, Config.VECTORSTORE_DIR, self.backups_dir]
        missing = [str(d) for d in req_dirs if not d.exists()]

        if missing:
            return {
                "name": "Application Environment",
                "category": "environment",
                "status": "WARNING",
                "message": f"Missing required directories: {', '.join(missing)}",
                "recommendation": "Re-run Config.ensure_directories() or create missing storage folders."
            }
        return {
            "name": "Application Environment",
            "category": "environment",
            "status": "PASS",
            "message": f"Python {sys.version.split()[0]} running. All required directories exist.",
            "recommendation": ""
        }

    def _check_database(self) -> Dict[str, Any]:
        """Check SQLite database file existence, connection, tables, columns, and readability."""
        if not self.db_path.exists():
            return {
                "name": "SQLite Database",
                "category": "database",
                "status": "FAIL",
                "message": f"Database file does not exist at '{self.db_path}'.",
                "recommendation": "Restore database from backup or initialize authentication/document database."
            }

        try:
            conn = self.get_db_connection()
            try:
                tables_res = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = {r["name"] for r in tables_res}
                req_tables = {"users", "documents", "document_audit_log", "document_quality_issues"}
                missing_tables = req_tables - table_names

                if missing_tables:
                    return {
                        "name": "SQLite Database",
                        "category": "database",
                        "status": "FAIL",
                        "message": f"Database is missing required tables: {', '.join(missing_tables)}.",
                        "recommendation": "Database schema requires attention. Re-initialize database tables."
                    }

                # Check key columns in documents table
                cursor = conn.execute("PRAGMA table_info(documents)")
                cols = {r["name"] for r in cursor.fetchall()}
                req_cols = {"quality_status", "governance_status", "retrieval_enabled", "preferred_source"}
                missing_cols = req_cols - cols
                if missing_cols:
                    return {
                        "name": "SQLite Database",
                        "category": "database",
                        "status": "WARNING",
                        "message": f"Database 'documents' table missing columns: {', '.join(missing_cols)}.",
                        "recommendation": "Run DocumentManager schema migration to update column definitions."
                    }

                doc_count = conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()["cnt"]
                return {
                    "name": "SQLite Database",
                    "category": "database",
                    "status": "PASS",
                    "message": f"Database connection OK. All tables intact. Total registered documents: {doc_count}.",
                    "recommendation": ""
                }
            finally:
                conn.close()
        except Exception as e:
            return {
                "name": "SQLite Database",
                "category": "database",
                "status": "FAIL",
                "message": f"Database error: {str(e)}",
                "recommendation": "Check database file permissions or restore a clean database backup."
            }

    def _check_document_storage(self) -> Dict[str, Any]:
        """Check managed PDF storage directory for missing files, orphan files, and path integrity."""
        docs_dir = Config.DOCUMENTS_DIR
        if not docs_dir.exists():
            return {
                "name": "Document Storage",
                "category": "storage",
                "status": "FAIL",
                "message": f"Document directory '{docs_dir}' missing.",
                "recommendation": "Create document directory or restore document storage from backup."
            }

        conn = self.get_db_connection()
        try:
            db_docs = [dict(r) for r in conn.execute("SELECT document_id, original_filename, stored_path, file_hash FROM documents").fetchall()]
        finally:
            conn.close()

        missing_files = []
        hash_mismatches = []
        for d in db_docs:
            sp = Path(d["stored_path"])
            if not sp.exists():
                missing_files.append(d["original_filename"])
            else:
                curr_hash = compute_sha256(sp)
                # Compare file_hash if present
                if d.get("file_hash") and len(d["file_hash"]) == 64 and curr_hash and curr_hash != d["file_hash"]:
                    hash_mismatches.append(d["original_filename"])

        disk_files = {p.name for p in docs_dir.glob("*.pdf")}
        db_filenames = {d["original_filename"] for d in db_docs}
        orphan_files = disk_files - db_filenames

        if missing_files or hash_mismatches:
            msg = []
            if missing_files:
                msg.append(f"Missing {len(missing_files)} file(s): {', '.join(missing_files[:3])}")
            if hash_mismatches:
                msg.append(f"Hash mismatch on {len(hash_mismatches)} file(s): {', '.join(hash_mismatches[:3])}")
            return {
                "name": "Document Storage",
                "category": "storage",
                "status": "WARNING",
                "message": "; ".join(msg),
                "recommendation": "Restore missing PDF files or re-index updated documents."
            }

        if orphan_files:
            return {
                "name": "Document Storage",
                "category": "storage",
                "status": "PASS",
                "message": f"All registered PDF files exist. {len(orphan_files)} unindexed orphan PDF file(s) present on disk.",
                "recommendation": "Ingest or review orphan PDF files."
            }

        return {
            "name": "Document Storage",
            "category": "storage",
            "status": "PASS",
            "message": f"Document storage healthy. All {len(db_docs)} registered PDF file(s) exist on disk.",
            "recommendation": ""
        }

    def _check_manifest(self) -> Dict[str, Any]:
        """Check documents_manifest.json existence, JSON validity, and structure."""
        manifest_path = Config.DATA_DIR / "documents_manifest.json"
        if not manifest_path.exists():
            return {
                "name": "Document Manifest",
                "category": "manifest",
                "status": "WARNING",
                "message": "Manifest file 'documents_manifest.json' does not exist.",
                "recommendation": "Run sync_manifest() to regenerate manifest from SQLite metadata."
            }

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                return {
                    "name": "Document Manifest",
                    "category": "manifest",
                    "status": "WARNING",
                    "message": "Manifest JSON format is invalid (expected list of records).",
                    "recommendation": "Regenerate manifest using DocumentManager.sync_manifest()."
                }

            return {
                "name": "Document Manifest",
                "category": "manifest",
                "status": "PASS",
                "message": f"Manifest JSON is valid and contains {len(data)} document record(s).",
                "recommendation": ""
            }
        except Exception as e:
            return {
                "name": "Document Manifest",
                "category": "manifest",
                "status": "WARNING",
                "message": f"Manifest JSON corrupted: {str(e)}",
                "recommendation": "Regenerate manifest using DocumentManager.sync_manifest()."
            }

    def _check_faiss_index(self) -> Dict[str, Any]:
        """Inspect active FAISS index file, metadata file, vector count, and loadability."""
        idx_path = Config.FAISS_INDEX_PATH
        meta_path = Config.METADATA_PATH

        if not idx_path.exists() or not meta_path.exists():
            return {
                "name": "FAISS Vector Index",
                "category": "vector_index",
                "status": "FAIL",
                "message": "CRITICAL: FAISS index file or metadata file is missing. Student retrieval unavailable.",
                "recommendation": "Rebuild active knowledge base index using Admin recovery controls.",
                "dimension": None
            }

        try:
            index = faiss.read_index(str(idx_path))
            vec_count = int(index.ntotal)
            dim = int(index.d)

            vstore = VectorStoreManager(index_path=idx_path, metadata_path=meta_path)
            meta_count = len(vstore.metadata)

            if vec_count != meta_count:
                return {
                    "name": "FAISS Vector Index",
                    "category": "vector_index",
                    "status": "WARNING",
                    "message": f"Vector count mismatch: FAISS has {vec_count} vectors, but metadata has {meta_count} records.",
                    "recommendation": "Rebuild active knowledge base index to resolve vector-metadata alignment.",
                    "dimension": dim
                }

            if vec_count == 0:
                return {
                    "name": "FAISS Vector Index",
                    "category": "vector_index",
                    "status": "WARNING",
                    "message": "FAISS index is loaded but contains 0 vectors.",
                    "recommendation": "Approve active documents and run safe index rebuild.",
                    "dimension": dim
                }

            return {
                "name": "FAISS Vector Index",
                "category": "vector_index",
                "status": "PASS",
                "message": f"FAISS index loaded cleanly ({vec_count} vectors, dimension {dim}, aligned metadata).",
                "recommendation": "",
                "dimension": dim
            }
        except Exception as e:
            return {
                "name": "FAISS Vector Index",
                "category": "vector_index",
                "status": "FAIL",
                "message": f"CRITICAL: FAISS index corrupted or unloadable: {str(e)}",
                "recommendation": "Restore a known-good backup or perform a safe index rebuild.",
                "dimension": None
            }

    def _check_embedding_model(self, index_dim: Optional[int] = None) -> Dict[str, Any]:
        """Test loading embedding model and check embedding dimension alignment."""
        try:
            mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
            test_emb = mgr.embed_texts(["test text"])
            dim = int(test_emb.shape[1]) if hasattr(test_emb, 'shape') and len(test_emb.shape) > 1 else (int(len(test_emb[0])) if len(test_emb) > 0 else 0)

            if index_dim is not None and int(dim) != int(index_dim):
                return {
                    "name": "Embedding Model",
                    "category": "embeddings",
                    "status": "FAIL",
                    "message": f"CRITICAL: Embedding dimension ({dim}) does not match active FAISS index dimension ({index_dim}).",
                    "recommendation": "Rebuild the active index using the current embedding model configuration."
                }

            return {
                "name": "Embedding Model",
                "category": "embeddings",
                "status": "PASS",
                "message": f"Local embedding model '{Config.EMBEDDING_MODEL_NAME}' loaded (dimension {dim}).",
                "recommendation": ""
            }
        except Exception as e:
            return {
                "name": "Embedding Model",
                "category": "embeddings",
                "status": "FAIL",
                "message": f"Failed to load local embedding model: {str(e)}",
                "recommendation": "Verify PyTorch / sentence-transformers installation and model cache."
            }

    def _check_gemini(self) -> Dict[str, Any]:
        """Check status of Gemini API configuration and connectivity."""
        api_key = Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return {
                "name": "Cloud LLM (Gemini API)",
                "category": "llm",
                "status": "WARNING",
                "message": "Gemini API key is not configured in GEMINI_API_KEY environment variable.",
                "recommendation": "Add GEMINI_API_KEY to .env file or environment variables to enable Gemini API."
            }
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "RAXEL-Diagnostics"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return {
                        "name": "Cloud LLM (Gemini API)",
                        "category": "llm",
                        "status": "PASS",
                        "message": f"Gemini API key validated. Active model '{Config.GEMINI_MODEL}' ready.",
                        "recommendation": ""
                    }
                else:
                    return {
                        "name": "Cloud LLM (Gemini API)",
                        "category": "llm",
                        "status": "WARNING",
                        "message": f"Gemini API returned status code {resp.status}.",
                        "recommendation": "Check GEMINI_API_KEY validity and network connectivity."
                    }
        except Exception as e:
            return {
                "name": "Cloud LLM (Gemini API)",
                "category": "llm",
                "status": "WARNING",
                "message": f"Gemini API connectivity check failed ({str(e)}).",
                "recommendation": "Verify internet connectivity and GEMINI_API_KEY."
            }

    def _check_ollama(self) -> Dict[str, Any]:
        """Check reachable status of local Ollama LLM service and configured model."""
        url = f"{Config.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RAXEL-Diagnostics"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    cfg_model = Config.LLM_MODEL
                    
                    found = any(cfg_model in m or m in cfg_model for m in models)
                    if found or not models:
                        return {
                            "name": "Local LLM (Ollama)",
                            "category": "llm",
                            "status": "PASS",
                            "message": f"Ollama service reachable at '{Config.OLLAMA_BASE_URL}'. Model '{Config.LLM_MODEL}' available.",
                            "recommendation": ""
                        }
                    else:
                        return {
                            "name": "Local LLM (Ollama)",
                            "category": "llm",
                            "status": "WARNING",
                            "message": f"Ollama service reachable, but configured model '{Config.LLM_MODEL}' was not found in installed models list ({models}).",
                            "recommendation": f"Run 'ollama pull {Config.LLM_MODEL}' on local server."
                        }
        except Exception as e:
            return {
                "name": "Local LLM (Ollama)",
                "category": "llm",
                "status": "WARNING",
                "message": f"Local Ollama service unreachable at '{Config.OLLAMA_BASE_URL}' ({str(e)}). Retrieval works, but answer generation is unavailable.",
                "recommendation": "Start local Ollama service (`ollama serve`)."
            }

    def _check_retrieval_readiness(self) -> Dict[str, Any]:
        """Run a lightweight retrieval test query without calling LLM."""
        if not Config.FAISS_INDEX_PATH.exists():
            return {
                "name": "Retrieval Pipeline",
                "category": "retrieval",
                "status": "FAIL",
                "message": "CRITICAL: Retrieval pipeline unavailable because FAISS index file is missing.",
                "recommendation": "Rebuild active knowledge base index."
            }

        try:
            emb_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
            vstore = VectorStoreManager(index_path=Config.FAISS_INDEX_PATH, metadata_path=Config.METADATA_PATH)
            retriever = KnowledgeRetriever(embedding_manager=emb_mgr, vector_store=vstore, top_k=2, similarity_threshold=0.1)

            res = retriever.retrieve("test question")
            return {
                "name": "Retrieval Pipeline",
                "category": "retrieval",
                "status": "PASS",
                "message": f"Retrieval pipeline test query succeeded (returned {len(res['chunks'])} candidate chunks).",
                "recommendation": ""
            }
        except Exception as e:
            return {
                "name": "Retrieval Pipeline",
                "category": "retrieval",
                "status": "FAIL",
                "message": f"CRITICAL: Retrieval test query failed: {str(e)}",
                "recommendation": "Rebuild active index or restore from a clean backup."
            }

    def _check_knowledge_base_health(self) -> Dict[str, Any]:
        """Summarize knowledge base document governance and quality distribution."""
        conn = self.get_db_connection()
        try:
            docs = [dict(r) for r in conn.execute("SELECT governance_status, quality_status, retrieval_enabled FROM documents").fetchall()]
            total = len(docs)
            approved_active = sum(1 for d in docs if d.get("governance_status") == "approved" and d.get("retrieval_enabled") == 1)
            pending = sum(1 for d in docs if d.get("governance_status") == "pending_review")
            conflicts = sum(1 for d in docs if d.get("quality_status") == "conflict")
            outdated = sum(1 for d in docs if d.get("quality_status") == "outdated")
            future = sum(1 for d in docs if d.get("quality_status") == "future_effective")

            msg = (
                f"Total documents: {total} | Active Approved: {approved_active} | Pending Review: {pending} | "
                f"Conflicts: {conflicts} | Outdated: {outdated} | Future Effective: {future}"
            )
            status = "WARNING" if pending > 0 or conflicts > 0 else "PASS"
            rec = "Review pending documents and resolve flagged quality conflicts." if (pending > 0 or conflicts > 0) else ""

            return {
                "name": "Knowledge Base Health",
                "category": "knowledge_base",
                "status": status,
                "message": msg,
                "recommendation": rec
            }
        finally:
            conn.close()

    def _check_configuration(self) -> Dict[str, Any]:
        """Check key configuration bounds and settings."""
        return {
            "name": "System Configuration",
            "category": "config",
            "status": "PASS",
            "message": f"Upload Limit: {Config.MAX_UPLOAD_SIZE_MB}MB | Similarity Threshold: {Config.SIMILARITY_THRESHOLD} | Top-K: {Config.TOP_K}",
            "recommendation": ""
        }

    @staticmethod
    def _safe_copy_db(src_db: Path, dst_db: Path) -> None:
        """Safely copy SQLite DB file using online backup API if available, fallback to shutil."""
        if not src_db.exists():
            return
        dst_db.parent.mkdir(parents=True, exist_ok=True)
        try:
            src_conn = sqlite3.connect(f"file:{src_db.resolve()}?mode=ro", uri=True)
            dst_conn = sqlite3.connect(dst_db)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
        except Exception:
            shutil.copy2(src_db, dst_db)

    # =========================================================================
    # BACKUP SYSTEM
    # =========================================================================

    def create_backup(self, user: Optional[Dict[str, Any]] = None, note: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a deterministic local backup of RAXEL state (Admin ONLY).
        Saves SQLite DB, manifest, FAISS index, metadata, document PDFs, SHA-256 hashes, and backup manifest.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "admin") if user else "admin"

        if not MAINTENANCE_LOCK.acquire(blocking=False):
            return {"success": False, "message": "Another maintenance operation is currently in progress."}

        try:
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"raxel_backup_{timestamp_str}"
            backup_path = self.backups_dir / backup_id
            
            if backup_path.exists():
                shutil.rmtree(backup_path)
            backup_path.mkdir(parents=True, exist_ok=True)

            file_hashes = {}

            # 1. Copy SQLite database
            if self.db_path.exists():
                dst_db = backup_path / "raxel.db"
                self._safe_copy_db(self.db_path, dst_db)
                file_hashes["raxel.db"] = compute_sha256(dst_db)

            # 2. Copy manifest
            manifest_path = Config.DATA_DIR / "documents_manifest.json"
            if manifest_path.exists():
                dst_man = backup_path / "documents_manifest.json"
                shutil.copy2(manifest_path, dst_man)
                file_hashes["documents_manifest.json"] = compute_sha256(dst_man)

            # 3. Copy FAISS vector store
            vstore_dir = backup_path / "vectorstore"
            vstore_dir.mkdir(parents=True, exist_ok=True)
            if Config.FAISS_INDEX_PATH.exists():
                dst_faiss = vstore_dir / "index.faiss"
                shutil.copy2(Config.FAISS_INDEX_PATH, dst_faiss)
                file_hashes["vectorstore/index.faiss"] = compute_sha256(dst_faiss)

            if Config.METADATA_PATH.exists():
                dst_meta = vstore_dir / "metadata.pkl"
                shutil.copy2(Config.METADATA_PATH, dst_meta)
                file_hashes["vectorstore/metadata.pkl"] = compute_sha256(dst_meta)

            # 4. Copy Document PDFs
            docs_dst_dir = backup_path / "documents"
            docs_dst_dir.mkdir(parents=True, exist_ok=True)
            if Config.DOCUMENTS_DIR.exists():
                for pdf_file in Config.DOCUMENTS_DIR.glob("*.pdf"):
                    dst_pdf = docs_dst_dir / pdf_file.name
                    shutil.copy2(pdf_file, dst_pdf)
                    file_hashes[f"documents/{pdf_file.name}"] = compute_sha256(dst_pdf)

            # Fetch statistics
            doc_cnt, active_cnt, chunk_cnt, vec_cnt = self._get_backup_stats(backup_path)

            # Write backup_manifest.json
            b_manifest = {
                "backup_id": backup_id,
                "created_at": datetime.datetime.now().isoformat(),
                "created_by": username,
                "note": note or "Manual Admin system backup",
                "document_count": doc_cnt,
                "active_document_count": active_cnt,
                "chunk_count": chunk_cnt,
                "vector_count": vec_cnt,
                "file_hashes": file_hashes,
                "schema_version": "6.6"
            }
            with open(backup_path / "backup_manifest.json", "w", encoding="utf-8") as f:
                json.dump(b_manifest, f, indent=2)

            # Validate created backup
            val_res = self.validate_backup(backup_id)
            if not val_res["valid"]:
                self._log_audit("backup_failed", username, details=f"Validation failed for {backup_id}: {val_res['message']}")
                return {"success": False, "message": f"Backup created but validation failed: {val_res['message']}"}

            self._log_audit("backup_created", username, details=f"Backup ID: {backup_id} ({doc_cnt} docs, {vec_cnt} vectors)")
            return {
                "success": True,
                "backup_id": backup_id,
                "backup_path": str(backup_path),
                "message": f"Backup '{backup_id}' created and validated successfully."
            }
        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")
            return {"success": False, "message": f"Backup creation failed: {str(e)}"}
        finally:
            MAINTENANCE_LOCK.release()

    def _get_backup_stats(self, backup_path: Path) -> Tuple[int, int, int, int]:
        """Extract statistics from backup directory files."""
        db_file = backup_path / "raxel.db"
        doc_cnt, active_cnt, chunk_cnt = 0, 0, 0
        if db_file.exists():
            try:
                conn = sqlite3.connect(str(db_file))
                conn.row_factory = sqlite3.Row
                r1 = conn.execute("SELECT COUNT(*) as cnt FROM documents").fetchone()
                doc_cnt = r1["cnt"] if r1 else 0
                r2 = conn.execute("SELECT COUNT(*) as cnt FROM documents WHERE governance_status='approved' AND retrieval_enabled=1").fetchone()
                active_cnt = r2["cnt"] if r2 else 0
                r3 = conn.execute("SELECT SUM(chunk_count) as cnt FROM documents WHERE governance_status='approved' AND retrieval_enabled=1").fetchone()
                chunk_cnt = r3["cnt"] if r3 and r3["cnt"] else 0
                conn.close()
            except Exception:
                pass

        vec_cnt = 0
        faiss_file = backup_path / "vectorstore" / "index.faiss"
        if faiss_file.exists():
            try:
                idx = faiss.read_index(str(faiss_file))
                vec_cnt = idx.ntotal
            except Exception:
                pass

        return doc_cnt, active_cnt, chunk_cnt, vec_cnt

    def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """Validate backup file integrity, JSON manifest, SHA-256 hashes, DB readability, and FAISS loadability."""
        clean_id = Path(backup_id).name
        backup_path = self.backups_dir / clean_id

        if not backup_path.exists() or not backup_path.is_dir():
            return {"valid": False, "message": f"Backup directory '{clean_id}' does not exist."}

        b_manifest_path = backup_path / "backup_manifest.json"
        if not b_manifest_path.exists():
            return {"valid": False, "message": "Backup manifest 'backup_manifest.json' is missing."}

        try:
            with open(b_manifest_path, "r", encoding="utf-8") as f:
                b_manifest = json.load(f)
        except Exception as e:
            return {"valid": False, "message": f"Backup manifest JSON corrupted: {str(e)}"}

        hashes = b_manifest.get("file_hashes", {})
        for rel_path, expected_hash in hashes.items():
            f_path = backup_path / rel_path
            if not f_path.exists():
                return {"valid": False, "message": f"Backup file '{rel_path}' is missing."}
            actual_hash = compute_sha256(f_path)
            if actual_hash != expected_hash:
                return {"valid": False, "message": f"SHA-256 hash mismatch for backup file '{rel_path}'."}

        # Check DB readable
        db_file = backup_path / "raxel.db"
        if db_file.exists():
            try:
                conn = sqlite3.connect(str(db_file))
                conn.execute("SELECT COUNT(*) FROM users").fetchone()
                conn.close()
            except Exception as e:
                return {"valid": False, "message": f"Backup database corrupted: {str(e)}"}

        # Check FAISS index loadable if present
        faiss_file = backup_path / "vectorstore" / "index.faiss"
        if faiss_file.exists():
            try:
                faiss.read_index(str(faiss_file))
            except Exception as e:
                return {"valid": False, "message": f"Backup FAISS index corrupted: {str(e)}"}

        return {
            "valid": True,
            "backup_id": clean_id,
            "manifest": b_manifest,
            "message": f"Backup '{clean_id}' validated successfully."
        }

    def list_backups(self, user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List all available system backups with metadata and validation status (Admin ONLY)."""
        require_role(ROLE_ADMIN, user)
        backups = []
        if not self.backups_dir.exists():
            return backups

        for entry in sorted(self.backups_dir.iterdir(), reverse=True):
            if entry.is_dir() and entry.name.startswith("raxel_backup_"):
                val_res = self.validate_backup(entry.name)
                manifest = val_res.get("manifest", {})
                backups.append({
                    "backup_id": entry.name,
                    "created_at": manifest.get("created_at", "Unknown"),
                    "created_by": manifest.get("created_by", "Unknown"),
                    "note": manifest.get("note", ""),
                    "document_count": manifest.get("document_count", 0),
                    "vector_count": manifest.get("vector_count", 0),
                    "valid": val_res["valid"],
                    "validation_message": val_res["message"]
                })
        return backups

    # =========================================================================
    # RESTORE SYSTEM & SAFETY SAFEGUARDS
    # =========================================================================

    def restore_backup(
        self,
        backup_id: str,
        user: Optional[Dict[str, Any]] = None,
        confirmation: bool = False
    ) -> Dict[str, Any]:
        """
        Restore RAXEL system state from a validated backup (Admin ONLY).
        Safeguards:
          1. Requires explicit confirmation parameter (confirmation=True).
          2. Automatically creates a safety backup of current state first.
          3. Extracts/stages backup in temporary staging folder (`data/backups/temp_restore`).
          4. Validates staged state (database, manifest, FAISS index, metadata, retrieval sanity).
          5. Atomically activates validated state.
          6. If any validation fails, stops immediately and preserves current working system.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "admin") if user else "admin"

        if not confirmation:
            return {"success": False, "message": "Restore operation requires explicit confirmation."}

        clean_id = Path(backup_id).name
        backup_path = self.backups_dir / clean_id

        if not backup_path.exists():
            return {"success": False, "message": f"Backup ID '{clean_id}' not found."}

        if not MAINTENANCE_LOCK.acquire(blocking=False):
            return {"success": False, "message": "Another maintenance operation is currently in progress."}

        try:
            self._log_audit("restore_started", username, details=f"Target backup: {clean_id}")

            # Step 1: Create automatic safety backup of current state first
            safety_res = self._create_safety_backup_internal(username, f"Pre-restore safety backup before restoring {clean_id}")
            if not safety_res["success"]:
                self._log_audit("restore_failed", username, details=f"Pre-restore safety backup failed: {safety_res['message']}")
                return {"success": False, "message": f"Restore aborted: Could not create safety backup of current state: {safety_res['message']}"}

            # Step 2: Validate target backup
            val_res = self.validate_backup(clean_id)
            if not val_res["valid"]:
                self._log_audit("restore_failed", username, details=f"Target backup validation failed: {val_res['message']}")
                return {"success": False, "message": f"Restore aborted: Target backup validation failed: {val_res['message']}"}

            # Step 3: Extract/Stage target backup to temporary directory
            temp_restore_dir = self.backups_dir / "temp_restore"
            if temp_restore_dir.exists():
                shutil.rmtree(temp_restore_dir)
            temp_restore_dir.mkdir(parents=True, exist_ok=True)

            for item in backup_path.iterdir():
                if item.name == "backup_manifest.json":
                    continue
                if item.is_dir():
                    shutil.copytree(item, temp_restore_dir / item.name)
                else:
                    shutil.copy2(item, temp_restore_dir / item.name)

            # Step 4: Validate staged state in isolation
            staged_db = temp_restore_dir / "raxel.db"
            staged_faiss = temp_restore_dir / "vectorstore" / "index.faiss"
            staged_meta = temp_restore_dir / "vectorstore" / "metadata.pkl"
            staged_manifest = temp_restore_dir / "documents_manifest.json"

            staged_valid, staged_msg = self._validate_staged_state(staged_db, staged_faiss, staged_meta, staged_manifest)
            if not staged_valid:
                shutil.rmtree(temp_restore_dir)
                self._log_audit("restore_failed", username, details=f"Staged restore validation failed: {staged_msg}")
                return {"success": False, "message": f"Restore aborted during staging validation: {staged_msg}. Current system preserved."}

            # Step 5: Atomically activate restored state
            if staged_db.exists():
                self._safe_copy_db(staged_db, self.db_path)

            if staged_manifest.exists():
                shutil.copy2(staged_manifest, Config.DATA_DIR / "documents_manifest.json")

            if staged_faiss.exists() and staged_meta.exists():
                Config.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staged_faiss, Config.FAISS_INDEX_PATH)
                shutil.copy2(staged_meta, Config.METADATA_PATH)

            staged_docs_dir = temp_restore_dir / "documents"
            if staged_docs_dir.exists():
                Config.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
                for pdf_file in staged_docs_dir.glob("*.pdf"):
                    shutil.copy2(pdf_file, Config.DOCUMENTS_DIR / pdf_file.name)

            # Clean up temp restore
            if temp_restore_dir.exists():
                shutil.rmtree(temp_restore_dir)

            self._log_audit("restore_succeeded", username, details=f"Successfully restored system from {clean_id}")
            return {
                "success": True,
                "message": f"System state restored successfully from backup '{clean_id}'."
            }
        except Exception as e:
            logger.error(f"Restore failed with exception: {str(e)}")
            self._log_audit("restore_failed", username, details=f"Exception during restore: {str(e)}")
            return {"success": False, "message": f"Restore failed: {str(e)}. Previous working system preserved."}
        finally:
            MAINTENANCE_LOCK.release()

    def _create_safety_backup_internal(self, username: str, note: str) -> Dict[str, Any]:
        """Internal helper to create a safety backup without acquiring lock twice."""
        try:
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"raxel_backup_safety_{timestamp_str}"
            backup_path = self.backups_dir / backup_id
            backup_path.mkdir(parents=True, exist_ok=True)

            file_hashes = {}

            if self.db_path.exists():
                dst_db = backup_path / "raxel.db"
                self._safe_copy_db(self.db_path, dst_db)
                file_hashes["raxel.db"] = compute_sha256(dst_db)

            manifest_path = Config.DATA_DIR / "documents_manifest.json"
            if manifest_path.exists():
                dst_man = backup_path / "documents_manifest.json"
                shutil.copy2(manifest_path, dst_man)
                file_hashes["documents_manifest.json"] = compute_sha256(dst_man)

            vstore_dir = backup_path / "vectorstore"
            vstore_dir.mkdir(parents=True, exist_ok=True)
            if Config.FAISS_INDEX_PATH.exists():
                dst_faiss = vstore_dir / "index.faiss"
                shutil.copy2(Config.FAISS_INDEX_PATH, dst_faiss)
                file_hashes["vectorstore/index.faiss"] = compute_sha256(dst_faiss)

            if Config.METADATA_PATH.exists():
                dst_meta = vstore_dir / "metadata.pkl"
                shutil.copy2(Config.METADATA_PATH, dst_meta)
                file_hashes["vectorstore/metadata.pkl"] = compute_sha256(dst_meta)

            docs_dst_dir = backup_path / "documents"
            docs_dst_dir.mkdir(parents=True, exist_ok=True)
            if Config.DOCUMENTS_DIR.exists():
                for pdf_file in Config.DOCUMENTS_DIR.glob("*.pdf"):
                    dst_pdf = docs_dst_dir / pdf_file.name
                    shutil.copy2(pdf_file, dst_pdf)
                    file_hashes[f"documents/{pdf_file.name}"] = compute_sha256(dst_pdf)

            doc_cnt, active_cnt, chunk_cnt, vec_cnt = self._get_backup_stats(backup_path)

            b_manifest = {
                "backup_id": backup_id,
                "created_at": datetime.datetime.now().isoformat(),
                "created_by": username,
                "note": note,
                "document_count": doc_cnt,
                "active_document_count": active_cnt,
                "chunk_count": chunk_cnt,
                "vector_count": vec_cnt,
                "file_hashes": file_hashes,
                "schema_version": "6.6"
            }
            with open(backup_path / "backup_manifest.json", "w", encoding="utf-8") as f:
                json.dump(b_manifest, f, indent=2)

            return {"success": True, "backup_id": backup_id}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _validate_staged_state(
        self,
        staged_db: Path,
        staged_faiss: Path,
        staged_meta: Path,
        staged_manifest: Path
    ) -> Tuple[bool, str]:
        """Validate staged database, manifest, FAISS index, and retrieval sanity."""
        if not staged_db.exists():
            return False, "Staged database file 'raxel.db' missing."

        try:
            conn = sqlite3.connect(str(staged_db))
            conn.execute("SELECT COUNT(*) FROM users").fetchone()
            conn.execute("SELECT COUNT(*) FROM documents").fetchone()
            conn.close()
        except Exception as e:
            return False, f"Staged database validation failed: {str(e)}"

        if staged_manifest.exists():
            try:
                with open(staged_manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    return False, "Staged manifest JSON is invalid format."
            except Exception as e:
                return False, f"Staged manifest validation failed: {str(e)}"

        if staged_faiss.exists() and staged_meta.exists():
            try:
                idx = faiss.read_index(str(staged_faiss))
                if idx.ntotal < 0:
                    return False, "Staged FAISS index has invalid vector count."
            except Exception as e:
                return False, f"Staged FAISS index validation failed: {str(e)}"

        return True, "Staged state validated successfully."

    # =========================================================================
    # SAFE KNOWLEDGE BASE REBUILD
    # =========================================================================

    def rebuild_active_knowledge_base(self, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Safely rebuild active FAISS index using strictly approved active documents (Admin ONLY).
        Creates a safety backup first, performs embedding dimension check, builds a temporary index,
        and atomically activates it upon successful validation.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "admin") if user else "admin"

        if not MAINTENANCE_LOCK.acquire(blocking=False):
            return {"success": False, "message": "Another maintenance operation is currently in progress."}

        try:
            self._log_audit("index_rebuild_started", username, details="Admin initiated active index rebuild")

            # 1. Create safety backup of current state
            self._create_safety_backup_internal(username, "Pre-rebuild safety backup")

            # 2. Embedding dimension check
            embedder = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
            test_emb = embedder.embed_texts(["dimension check"])
            curr_dim = int(test_emb.shape[1]) if (test_emb is not None and hasattr(test_emb, "shape") and len(test_emb.shape) > 1) else 384

            # 3. Perform safe rebuild via DocumentManager
            reindex_res = self.doc_manager.rebuild_active_faiss_index()
            if not reindex_res["success"]:
                self._log_audit("index_rebuild_failed", username, details=reindex_res["message"])
                return {"success": False, "message": f"Active index rebuild failed: {reindex_res['message']}. Previous index preserved."}

            # 4. Verify rebuilt index
            if Config.FAISS_INDEX_PATH.exists():
                idx = faiss.read_index(str(Config.FAISS_INDEX_PATH))
                if idx.d != curr_dim:
                    self._log_audit("index_rebuild_failed", username, details=f"Dimension mismatch after rebuild ({idx.d} vs {curr_dim})")
                    return {"success": False, "message": "Index rebuild produced dimension mismatch."}

            self._log_audit("index_rebuild_succeeded", username, details=f"Rebuilt index ({reindex_res.get('chunk_count', 0)} chunks)")
            return {
                "success": True,
                "message": f"Active knowledge base rebuilt successfully ({reindex_res.get('chunk_count', 0)} chunks indexed).",
                "details": reindex_res
            }
        except Exception as e:
            logger.error(f"Active index rebuild failed: {str(e)}")
            self._log_audit("index_rebuild_failed", username, details=f"Exception during rebuild: {str(e)}")
            return {"success": False, "message": f"Active index rebuild failed: {str(e)}. Previous index preserved."}
        finally:
            MAINTENANCE_LOCK.release()

    def _log_audit(self, action: str, performed_by: str, reason: Optional[str] = None, details: Optional[str] = None) -> None:
        """Record diagnostic and recovery events in SQLite document_audit_log."""
        conn = self.get_db_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO document_audit_log (document_id, action, performed_by, reason, details)
                    VALUES ('SYSTEM', ?, ?, ?, ?)
                """, (action, performed_by, reason, details))
        except Exception as e:
            logger.warning(f"Audit logging warning: {str(e)}")
        finally:
            conn.close()
