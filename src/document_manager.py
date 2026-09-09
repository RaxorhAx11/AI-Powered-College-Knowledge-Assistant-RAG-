"""
Document Management & Safe Re-Indexing Layer for RAXEL (Phase 6.2).

Manages document metadata in SQLite, file validation, safe storage, duplicate detection,
document lifecycle transitions (uploaded -> processing -> indexed / failed / archived),
and safe FAISS index rebuilding to prevent corrupting active RAG search data.
"""

import os
import re
import json
import shutil
import sqlite3
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from src.config import Config
from src.permissions import require_role, ROLE_FACULTY, ROLE_ADMIN, ROLE_STUDENT
from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

SUGGESTED_DOC_TYPES = [
    "academic_regulations",
    "student_handbook",
    "syllabus",
    "notice",
    "circular",
    "timetable",
    "placement",
    "examination",
    "other"
]

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and unsafe characters.
    Strips directory separators, null bytes, and path traversal tokens.
    """
    if not filename:
        return "unnamed_document.pdf"
    
    # Strip paths
    name = Path(filename).name
    
    # Remove path traversal tokens and dangerous characters
    name = re.sub(r'[\x00-\x1f\x7f\\/:\*\?"<>\|]', '_', name)
    name = re.sub(r'\.\.+', '.', name)
    name = name.strip(' .')
    
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
        
    return name if name else "document.pdf"

def validate_pdf_bytes(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validate uploaded PDF file bytes against safety criteria:
    1. Presence / non-empty
    2. Extension is .pdf
    3. File size within safe limit (Config.MAX_UPLOAD_SIZE_BYTES)
    4. PDF magic bytes header check (%PDF-)
    """
    if not file_bytes:
        return False, "Uploaded file is empty."
    
    size_bytes = len(file_bytes)
    if size_bytes > Config.MAX_UPLOAD_SIZE_BYTES:
        return False, f"The uploaded file exceeds the maximum allowed size of {Config.MAX_UPLOAD_SIZE_MB} MB."
    
    ext = Path(filename).suffix.lower()
    if ext != ".pdf":
        return False, "Only PDF documents are supported."
        
    clean_name = sanitize_filename(filename)
    
    # PDF Magic Bytes check: first 1024 bytes should contain %PDF-
    header = file_bytes[:1024]
    if b"%PDF-" not in header:
        return False, "This file does not appear to be a valid PDF."
    
    return True, "Valid PDF"

class DocumentManager:
    """Manages RAXEL college knowledge documents, SQLite metadata, and safe FAISS re-indexing."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else Config.AUTH_DATABASE_PATH
        self.init_db()
        self.seed_from_manifest_if_empty()

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a SQLite connection with Row factory."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize the `documents` and `document_audit_log` tables if they do not already exist."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        original_filename TEXT NOT NULL,
                        stored_path TEXT NOT NULL,
                        document_type TEXT NOT NULL,
                        academic_year TEXT,
                        version TEXT,
                        effective_date TEXT,
                        description TEXT,
                        file_hash TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        page_count INTEGER DEFAULT 0,
                        chunk_count INTEGER DEFAULT 0,
                        ocr_page_count INTEGER DEFAULT 0,
                        uploaded_by TEXT NOT NULL,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT NOT NULL DEFAULT 'uploaded',
                        governance_status TEXT NOT NULL DEFAULT 'pending_review',
                        approved_by TEXT,
                        approved_at TIMESTAMP,
                        rejected_by TEXT,
                        rejected_at TIMESTAMP,
                        rejection_reason TEXT,
                        retrieval_enabled INTEGER NOT NULL DEFAULT 0,
                        authority TEXT DEFAULT 'faculty_uploaded',
                        error_message TEXT,
                        quality_status TEXT NOT NULL DEFAULT 'clean',
                        supersedes_document_id TEXT,
                        superseded_by TEXT,
                        quality_reviewed INTEGER DEFAULT 0,
                        quality_reviewed_by TEXT,
                        quality_reviewed_at TIMESTAMP,
                        quality_notes TEXT,
                        preferred_source INTEGER DEFAULT 0,
                        preferred_reason TEXT
                    );
                """)

                # Automatic schema migration for existing SQLite databases missing new governance/quality columns
                cursor = conn.execute("PRAGMA table_info(documents)")
                existing_cols = {row["name"] for row in cursor.fetchall()}

                new_cols = [
                    ("governance_status", "TEXT NOT NULL DEFAULT 'pending_review'"),
                    ("approved_by", "TEXT"),
                    ("approved_at", "TIMESTAMP"),
                    ("rejected_by", "TEXT"),
                    ("rejected_at", "TIMESTAMP"),
                    ("rejection_reason", "TEXT"),
                    ("quality_status", "TEXT NOT NULL DEFAULT 'clean'"),
                    ("supersedes_document_id", "TEXT"),
                    ("superseded_by", "TEXT"),
                    ("quality_reviewed", "INTEGER DEFAULT 0"),
                    ("quality_reviewed_by", "TEXT"),
                    ("quality_reviewed_at", "TIMESTAMP"),
                    ("quality_notes", "TEXT"),
                    ("preferred_source", "INTEGER DEFAULT 0"),
                    ("preferred_reason", "TEXT")
                ]
                for col_name, col_def in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_def}")

                # Create document_audit_log table for lightweight governance audit trails
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        performed_by TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reason TEXT,
                        details TEXT
                    );
                """)

                # Create document_quality_issues table for Phase 6.4 Knowledge Base Quality Control
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_quality_issues (
                        issue_id TEXT PRIMARY KEY,
                        document_a_id TEXT NOT NULL,
                        document_b_id TEXT NOT NULL,
                        issue_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'open',
                        resolved_by TEXT,
                        resolved_at TIMESTAMP,
                        resolution TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
        finally:
            conn.close()

    def seed_from_manifest_if_empty(self) -> None:
        """Seed `documents` table from existing `data/documents_manifest.json` if empty."""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) as count FROM documents")
            row = cursor.fetchone()
            if row and row["count"] > 0:
                return
            
            manifest_path = Config.DATA_DIR / "documents_manifest.json"
            if not manifest_path.exists():
                return
            
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                
            docs_dir = Config.DOCUMENTS_DIR
            with conn:
                for item in manifest:
                    fname = item.get("file_name", "doc.pdf")
                    file_path = docs_dir / fname
                    fsize = file_path.stat().st_size if file_path.exists() else 0
                    is_active = (item.get("status") == "active")
                    
                    conn.execute("""
                        INSERT OR IGNORE INTO documents (
                            document_id, title, original_filename, stored_path,
                            document_type, academic_year, version, effective_date,
                            description, file_hash, file_size, page_count, chunk_count,
                            ocr_page_count, uploaded_by, status, governance_status,
                            approved_by, approved_at, retrieval_enabled, authority
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                    """, (
                        item.get("document_id", f"doc_{item.get('file_hash', '')[:10]}"),
                        fname.replace(".pdf", "").replace("_", " "),
                        fname,
                        str(file_path),
                        item.get("document_type", "general"),
                        item.get("academic_year"),
                        item.get("version"),
                        item.get("effective_date"),
                        "Seeded synthetic document fixture",
                        item.get("file_hash", ""),
                        fsize,
                        item.get("page_count", 0),
                        0,
                        0,
                        "system",
                        "indexed",
                        "approved" if is_active else "pending_review",
                        "system" if is_active else None,
                        1 if is_active else 0,
                        item.get("authority", "synthetic_fixture")
                    ))
        except Exception as e:
            logger.warning(f"Manifest seeding warning: {str(e)}")
        finally:
            conn.close()

    def log_audit_event(
        self,
        doc_id: str,
        action: str,
        performed_by: str,
        reason: Optional[str] = None,
        details: Optional[str] = None
    ) -> None:
        """Record a governance audit trail entry in SQLite."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO document_audit_log (document_id, action, performed_by, reason, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (doc_id, action, performed_by, reason, details))
        except Exception as e:
            logger.warning(f"Failed to log audit event ({action}) for doc {doc_id}: {str(e)}")
        finally:
            conn.close()

    def get_audit_logs(self, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve audit trail records, optionally filtered by document_id."""
        conn = self.get_connection()
        try:
            if doc_id:
                cursor = conn.execute(
                    "SELECT * FROM document_audit_log WHERE document_id = ? ORDER BY timestamp DESC", (doc_id,)
                )
            else:
                cursor = conn.execute("SELECT * FROM document_audit_log ORDER BY timestamp DESC")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve existing document record by cryptographic hash."""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document record by document_id."""
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM documents WHERE document_id = ?", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_documents(
        self,
        status: Optional[str] = None,
        governance_status: Optional[str] = None,
        doc_type: Optional[str] = None,
        academic_year: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List documents from SQLite with optional filtering and search."""
        conn = self.get_connection()
        try:
            query = "SELECT * FROM documents WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            if governance_status:
                query += " AND governance_status = ?"
                params.append(governance_status)
            if doc_type:
                query += " AND document_type = ?"
                params.append(doc_type)
            if academic_year:
                query += " AND academic_year = ?"
                params.append(academic_year)
            if search_query:
                query += " AND (LOWER(title) LIKE ? OR LOWER(original_filename) LIKE ?)"
                q = f"%{search_query.lower()}%"
                params.extend([q, q])
                
            query += " ORDER BY uploaded_at DESC"
            cursor = conn.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def upload_document(
        self,
        file_bytes: bytes,
        filename: str,
        title: str,
        document_type: str,
        academic_year: Optional[str] = None,
        version: Optional[str] = None,
        effective_date: Optional[str] = None,
        description: Optional[str] = None,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload and register a new document for Faculty or Admin.
        Validates file, checks for duplicates, safely saves PDF to data/documents/,
        and creates record with status='uploaded', governance_status='pending_review', and retrieval_enabled=0.
        """
        # Server-side RBAC check
        require_role(ROLE_FACULTY, user)
        username = user.get("username", "unknown") if user else "unknown"
        user_role = user.get("role", ROLE_FACULTY) if user else ROLE_FACULTY
        
        # 1. Validate PDF file
        is_valid, err_msg = validate_pdf_bytes(file_bytes, filename)
        if not is_valid:
            return {"success": False, "message": err_msg}
        
        # 2. Sanitize filename & determine target storage path
        safe_name = sanitize_filename(filename)
        dest_dir = Config.DOCUMENTS_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        target_path = dest_dir / safe_name
        
        # Write to temporary file first before atomic replace
        temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf", dir=str(dest_dir))
        try:
            with os.fdopen(temp_fd, "wb") as f:
                f.write(file_bytes)
                
            # Calculate file hash
            processor = PDFProcessor()
            file_hash = processor.calculate_file_hash(Path(temp_path))
            
            # 3. Check for duplicates
            existing = self.get_document_by_hash(file_hash)
            if existing and existing.get("status") != "failed":
                os.remove(temp_path)
                return {
                    "success": False,
                    "duplicate": True,
                    "message": "This document already exists in the knowledge base.",
                    "existing_document": existing
                }
            
            # Atomic move to final safe path
            if target_path.exists() and target_path != Path(temp_path):
                # If name collision with different hash, create unique filename
                safe_name = f"{Path(safe_name).stem}_{file_hash[:8]}.pdf"
                target_path = dest_dir / safe_name
                
            shutil.move(temp_path, target_path)
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"Failed to write uploaded document safely: {str(e)}")
            return {"success": False, "message": f"Failed to save document file safely: {str(e)}"}
        
        # 4. Create Database Record
        doc_id = f"doc_{file_hash[:10]}"
        clean_title = title.strip() if title and title.strip() else Path(safe_name).stem.replace("_", " ")
        clean_doc_type = document_type.strip() if document_type else "general"
        authority_label = "admin_uploaded" if user_role == ROLE_ADMIN else "faculty_uploaded"
        
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO documents (
                        document_id, title, original_filename, stored_path,
                        document_type, academic_year, version, effective_date,
                        description, file_hash, file_size, uploaded_by, status,
                        governance_status, retrieval_enabled, authority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(document_id) DO UPDATE SET
                        title=excluded.title,
                        stored_path=excluded.stored_path,
                        document_type=excluded.document_type,
                        academic_year=excluded.academic_year,
                        version=excluded.version,
                        effective_date=excluded.effective_date,
                        description=excluded.description,
                        uploaded_by=excluded.uploaded_by,
                        status='uploaded',
                        governance_status='pending_review',
                        retrieval_enabled=0,
                        updated_at=CURRENT_TIMESTAMP,
                        error_message=NULL
                """, (
                    doc_id,
                    clean_title,
                    filename,
                    str(target_path),
                    clean_doc_type,
                    academic_year,
                    version,
                    effective_date,
                    description,
                    file_hash,
                    len(file_bytes),
                    username,
                    "uploaded",
                    "pending_review",
                    0,
                    authority_label
                ))
            
            # Log audit event
            self.log_audit_event(doc_id, "uploaded", username, details=f"Uploaded '{filename}' ({clean_doc_type})")

            doc_record = self.get_document_by_id(doc_id)
            return {
                "success": True,
                "message": "Document uploaded successfully and submitted for admin review.",
                "document": doc_record
            }
        except Exception as e:
            logger.error(f"Failed to record uploaded document metadata: {str(e)}")
            return {"success": False, "message": f"Database error: {str(e)}"}
        finally:
            conn.close()

    def process_and_index_document(
        self,
        doc_id: str,
        user: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Process PDF and update counts.
        UNAPPROVED DOCUMENTS REMAIN INACTIVE (retrieval_enabled=0).
        Rebuilds active FAISS index safely using ONLY approved documents.
        """
        require_role(ROLE_FACULTY, user)
        username = user.get("username", "unknown") if user else "unknown"
        
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return {"success": False, "message": f"Document ID '{doc_id}' not found."}
        
        file_path = Path(doc["stored_path"])
        if not file_path.exists():
            self._update_status(doc_id, "failed", 0, "Document PDF file not found on disk.")
            return {"success": False, "message": "Document PDF file not found on disk."}

        # Update status to processing
        self._update_status(doc_id, "processing", 0)

        def report(stage_msg: str):
            if progress_callback:
                progress_callback(stage_msg)
            logger.info(f"[{doc_id}] {stage_msg}")

        try:
            report("1. Validating PDF & target path...")
            report("2. Extracting text & structure from PDF...")
            processor = PDFProcessor(
                ocr_enabled=Config.OCR_ENABLED,
                ocr_min_text_length=Config.OCR_MIN_TEXT_LENGTH
            )
            pages = processor.process_pdf(file_path)
            if not pages:
                raise ValueError("Could not extract any readable content from PDF.")

            report("3. Checking for scanned pages & running OCR...")
            ocr_count = sum(1 for p in pages if p.get("needs_ocr", False))

            report("4. Creating text chunks with metadata...")
            chunker = TextChunker(
                chunk_size=Config.CHUNK_SIZE,
                chunk_overlap=Config.CHUNK_OVERLAP,
                min_chunk_size=Config.MIN_CHUNK_SIZE
            )
            
            # Enrich page metadata with document record details
            for p in pages:
                p["document_type"] = doc.get("document_type", p.get("document_type", "general"))
                p["academic_year"] = doc.get("academic_year") or p.get("version_str")
                p["version"] = doc.get("version") or p.get("version_str")
                p["effective_date"] = doc.get("effective_date") or p.get("notice_date")
                p["authority"] = doc.get("authority", "faculty_uploaded")

            chunks = chunker.chunk_documents(pages)
            if not chunks:
                raise ValueError("PDF extraction succeeded, but 0 valid chunks were generated.")

            report("5. Staging safe re-index for all active approved documents...")
            gov_state = doc.get("governance_status", "pending_review")
            retrieval_flag = 1 if (gov_state == "approved") else 0

            # Update status to indexed in DB
            self._update_doc_counts_and_status(
                doc_id=doc_id,
                status="indexed",
                retrieval_enabled=retrieval_flag,
                page_count=len(pages),
                chunk_count=len(chunks),
                ocr_count=ocr_count
            )

            # Log audit event
            self.log_audit_event(
                doc_id, "processed", username,
                details=f"Extracted {len(pages)} pages, {len(chunks)} chunks. Governance status: {gov_state}"
            )

            # Rebuild index safely from ALL currently approved + active documents
            reindex_res = self.rebuild_active_faiss_index(report=report)
            if not reindex_res["success"]:
                raise RuntimeError(reindex_res["message"])

            # Sync documents_manifest.json
            self.sync_manifest()

            updated_doc = self.get_document_by_id(doc_id)
            if gov_state == "approved":
                msg = "Document processed and indexed successfully."
            else:
                msg = "Document processed successfully and is waiting for admin approval."

            report(f"6. {msg}")
            return {
                "success": True,
                "message": msg,
                "document": updated_doc
            }

        except Exception as e:
            err_text = str(e)
            logger.error(f"Processing failed for document {doc_id}: {err_text}")
            # Mark document as failed, disable retrieval
            self._update_status(doc_id, "failed", 0, error_message=err_text)
            
            # Rebuild index from remaining active docs to ensure index consistency
            try:
                self.rebuild_active_faiss_index()
                self.sync_manifest()
            except Exception:
                pass
                
            return {
                "success": False,
                "message": f"Processing failed: {err_text}. The existing active knowledge base remains safe.",
                "error": err_text
            }

    def approve_document(self, doc_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Approve a document (Admin ONLY).
        Enforces self-approval check (faculty/uploader cannot approve own document).
        Validates processing completed successfully, chunks exist, and metadata is valid.
        Sets governance_status='approved', retrieval_enabled=1, rebuilds FAISS index, and logs audit.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "unknown") if user else "unknown"

        doc = self.get_document_by_id(doc_id)
        if not doc:
            return {"success": False, "message": f"Document ID '{doc_id}' not found."}

        # 1. Prevent Self-Approval (for non-admin users)
        user_role = user.get("role", "") if user else ""
        if doc.get("uploaded_by", "").lower() == username.lower() and user_role != ROLE_ADMIN:
            return {
                "success": False,
                "message": "Self-approval is not allowed. A user cannot approve their own uploaded document."
            }

        # 2. Validation & Automatic processing if status is 'uploaded' or chunk_count <= 0
        if doc["status"] != "indexed" or doc.get("chunk_count", 0) <= 0:
            proc_res = self.process_and_index_document(doc_id=doc_id, user=user)
            if not proc_res.get("success"):
                return {
                    "success": False,
                    "message": f"Document processing failed: {proc_res.get('message', 'Unknown error')}"
                }
            doc = self.get_document_by_id(doc_id)
            
        if not Path(doc["stored_path"]).exists():
            return {"success": False, "message": "Cannot approve document: physical PDF file not found on disk."}

        # 3. Update DB state
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    UPDATE documents
                    SET governance_status = 'approved',
                        retrieval_enabled = 1,
                        approved_by = ?,
                        approved_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (username, doc_id))
        finally:
            conn.close()

        # 4. Log Audit Event
        self.log_audit_event(doc_id, "approved", username, details=f"Approved by Admin '{username}'")

        # 5. Rebuild FAISS index safely & sync manifest
        reindex_res = self.rebuild_active_faiss_index()
        self.sync_manifest()

        if not reindex_res["success"]:
            return {
                "success": False,
                "message": f"Document approved in database, but FAISS re-indexing failed: {reindex_res['message']}"
            }

        return {
            "success": True,
            "message": "Document approved and added to the active knowledge base.",
            "document": self.get_document_by_id(doc_id)
        }

    def reject_document(self, doc_id: str, rejection_reason: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Reject a document (Admin ONLY).
        Requires explicit non-empty rejection reason.
        Sets governance_status='rejected', retrieval_enabled=0, rebuilds FAISS index, and logs audit.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "unknown") if user else "unknown"

        if not rejection_reason or not rejection_reason.strip():
            return {"success": False, "message": "Rejection reason cannot be empty."}

        clean_reason = rejection_reason.strip()
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return {"success": False, "message": f"Document ID '{doc_id}' not found."}

        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    UPDATE documents
                    SET governance_status = 'rejected',
                        retrieval_enabled = 0,
                        rejected_by = ?,
                        rejected_at = CURRENT_TIMESTAMP,
                        rejection_reason = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (username, clean_reason, doc_id))
        finally:
            conn.close()

        self.log_audit_event(doc_id, "rejected", username, reason=clean_reason)
        self.rebuild_active_faiss_index()
        self.sync_manifest()

        return {
            "success": True,
            "message": f"Document '{doc['title']}' rejected.",
            "document": self.get_document_by_id(doc_id)
        }

    def rebuild_active_faiss_index(self, report: Optional[Any] = None) -> Dict[str, Any]:
        """
        Rebuild FAISS index from scratch using all active documents.
        MUST SATISFY ALL THREE CONDITIONS:
          status == 'indexed'
          AND governance_status == 'approved'
          AND retrieval_enabled == 1
        This guarantees index consistency and prevents orphaned vectors or unapproved evidence leaks.
        """
        if report:
            report("Generating embeddings & updating FAISS index...")

        active_docs = self.list_documents(status="indexed", governance_status="approved")
        active_docs = [d for d in active_docs if d.get("retrieval_enabled", 0) == 1]

        all_active_pages = []
        processor = PDFProcessor(ocr_enabled=Config.OCR_ENABLED, ocr_min_text_length=Config.OCR_MIN_TEXT_LENGTH)

        for d in active_docs:
            fpath = Path(d["stored_path"])
            if fpath.exists():
                pages = processor.process_pdf(fpath)
                for p in pages:
                    p["document_type"] = d.get("document_type", p.get("document_type", "general"))
                    p["academic_year"] = d.get("academic_year") or p.get("version_str")
                    p["version"] = d.get("version") or p.get("version_str")
                    p["effective_date"] = d.get("effective_date") or p.get("notice_date")
                    p["authority"] = d.get("authority", "faculty_uploaded")
                    p["document_id"] = d.get("document_id")
                    p["document_title"] = d.get("title")
                all_active_pages.extend(pages)

        vector_store = VectorStoreManager(
            index_path=Config.FAISS_INDEX_PATH,
            metadata_path=Config.METADATA_PATH
        )

        if not all_active_pages:
            # If no active documents, clear vector index safely
            vector_store.metadata = []
            vector_store.index = None
            if Config.FAISS_INDEX_PATH.exists():
                os.remove(Config.FAISS_INDEX_PATH)
            if Config.METADATA_PATH.exists():
                os.remove(Config.METADATA_PATH)
            self._notify_cache_reload()
            return {"success": True, "message": "Knowledge base reset to empty state."}

        chunker = TextChunker(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            min_chunk_size=Config.MIN_CHUNK_SIZE
        )
        chunks = chunker.chunk_documents(all_active_pages)
        if not chunks:
            return {"success": False, "message": "Active documents produced 0 chunks during re-indexing."}

        embedder = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts_to_embed, normalize=True)

        # Build and save fresh index atomically
        vector_store.build_index(embeddings, chunks)
        self._notify_cache_reload()

        return {"success": True, "chunk_count": len(chunks), "document_count": len(active_docs)}

    def _notify_cache_reload(self) -> None:
        """Notify ComponentRegistry singleton to reload in-memory FAISS and BM25 index."""
        try:
            from backend.dependencies import ComponentRegistry
            ComponentRegistry.reload_vector_store()
        except Exception as e:
            logger.debug(f"ComponentRegistry reload notification skipped: {str(e)}")

    def archive_document(self, doc_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Archive a document (Faculty or Admin).
        Moves governance_status to 'archived', disables retrieval, and updates FAISS index
        so student RAG queries never retrieve archived content.
        """
        require_role(ROLE_FACULTY, user)
        username = user.get("username", "unknown") if user else "unknown"
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return {"success": False, "message": f"Document ID '{doc_id}' not found."}

        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    UPDATE documents
                    SET governance_status = 'archived',
                        retrieval_enabled = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (doc_id,))
        finally:
            conn.close()

        self.log_audit_event(doc_id, "archived", username)
        self.rebuild_active_faiss_index()
        self.sync_manifest()

        return {"success": True, "message": f"Document '{doc['title']}' archived successfully."}

    def restore_document(self, doc_id: str, target_governance: str = "pending_review", user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Restore an archived document (Admin ONLY).
        Restores governance_status to 'pending_review' (safe default) or 'approved'.
        Does NOT create duplicate vectors.
        """
        require_role(ROLE_ADMIN, user)
        username = user.get("username", "unknown") if user else "unknown"
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return {"success": False, "message": f"Document ID '{doc_id}' not found."}

        gov_state = target_governance if target_governance in ("pending_review", "approved") else "pending_review"
        retrieval_flag = 1 if (gov_state == "approved" and doc["status"] == "indexed") else 0

        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    UPDATE documents
                    SET governance_status = ?,
                        retrieval_enabled = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (gov_state, retrieval_flag, doc_id))
        finally:
            conn.close()

        self.log_audit_event(doc_id, "restored", username, details=f"Restored to {gov_state}")
        reindex_res = self.rebuild_active_faiss_index()
        self.sync_manifest()

        if not reindex_res["success"]:
            return {"success": False, "message": f"Restored document metadata, but re-indexing failed: {reindex_res['message']}"}

        return {"success": True, "message": f"Document '{doc['title']}' restored to '{gov_state}' successfully."}

    def delete_document(self, doc_id: str, user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Permanently delete a document (Faculty for own uploaded documents, Admin for any).
        Removes DB metadata, quality issues, physical file from disk, logs audit, and rebuilds FAISS index.
        """
        if not user or not user.get("authenticated", False):
            raise PermissionError("Authentication required. Please log in.")

        role = user.get("role", ROLE_STUDENT)
        username = user.get("username", "unknown")

        if role == ROLE_STUDENT:
            raise PermissionError("Forbidden: Students do not have document deletion permissions.")

        doc = self.get_document_by_id(doc_id)
        if not doc:
            return {"success": False, "message": f"Document ID '{doc_id}' not found."}

        # Faculty ownership check
        if role == ROLE_FACULTY:
            uploaded_by = doc.get("uploaded_by", "")
            if uploaded_by.lower() != username.lower():
                raise PermissionError("Forbidden: You can only delete documents that you uploaded.")

        stored_path = Path(doc["stored_path"])
        self.log_audit_event(doc_id, "deleted", username, details=f"Permanently deleted '{doc['title']}'")

        conn = self.get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM documents WHERE document_id = ?", (doc_id,))
                conn.execute("DELETE FROM document_quality_issues WHERE document_a_id = ? OR document_b_id = ?", (doc_id, doc_id))
            
            # Remove physical file
            if stored_path.exists():
                try:
                    os.remove(stored_path)
                except Exception as e:
                    logger.warning(f"Could not remove physical file '{stored_path}': {str(e)}")

            # Rebuild FAISS index safely
            self.rebuild_active_faiss_index()
            self.sync_manifest()

            return {"success": True, "message": f"Document '{doc['title']}' permanently deleted."}
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            return {"success": False, "message": f"Deletion failed: {str(e)}"}
        finally:
            conn.close()

    def sync_manifest(self) -> None:
        """Sync active documents from SQLite DB to data/documents_manifest.json."""
        if str(self.db_path) != str(Config.AUTH_DATABASE_PATH):
            logger.debug("Skipping root manifest sync for custom test DB path: %s", self.db_path)
            return

        docs = self.list_documents()
        manifest_records = []
        for d in docs:
            manifest_records.append({
                "document_id": d["document_id"],
                "file_name": d["original_filename"],
                "relative_path": d["original_filename"],
                "document_type": d["document_type"],
                "academic_year": d["academic_year"],
                "version": d["version"],
                "effective_date": d["effective_date"],
                "page_count": d["page_count"],
                "file_hash": d["file_hash"],
                "authority": d.get("authority", "faculty_uploaded"),
                "governance_status": d.get("governance_status", "pending_review"),
                "status": "active" if d["status"] == "indexed" and d.get("governance_status") == "approved" and d["retrieval_enabled"] == 1 else d["status"]
            })
            
        manifest_path = Config.DATA_DIR / "documents_manifest.json"
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_records, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not sync documents_manifest.json: {str(e)}")

    def _update_status(
        self,
        doc_id: str,
        status: str,
        retrieval_enabled: int,
        error_message: Optional[str] = None
    ) -> None:
        """Helper to update document status and retrieval flag."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    UPDATE documents
                    SET status = ?, retrieval_enabled = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (status, retrieval_enabled, error_message, doc_id))
        finally:
            conn.close()

    def _update_doc_counts_and_status(
        self,
        doc_id: str,
        status: str,
        retrieval_enabled: int,
        page_count: int,
        chunk_count: int,
        ocr_count: int
    ) -> None:
        """Helper to update doc counts and status upon successful processing."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute("""
                    UPDATE documents
                    SET status = ?, retrieval_enabled = ?, page_count = ?, chunk_count = ?,
                        ocr_page_count = ?, error_message = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE document_id = ?
                """, (status, retrieval_enabled, page_count, chunk_count, ocr_count, doc_id))
        finally:
            conn.close()

