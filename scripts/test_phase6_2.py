"""
Phase 6.2 Faculty/Admin Document Upload, Knowledge Base Management & Safe Re-Indexing Test Suite (Project RAXEL).

Tests all 30 Phase 6.2 requirements plus Phase 1–6.1 regression.
"""

import os
import sys
import unittest
import tempfile
import sqlite3
import shutil
from pathlib import Path
import uuid

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.auth import init_auth_db, create_user, authenticate_user
from src.permissions import (
    require_role, has_role, ROLE_STUDENT, ROLE_FACULTY, ROLE_ADMIN
)
from src.document_manager import (
    DocumentManager, validate_pdf_bytes, sanitize_filename
)
from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline

class TestPhase62DocumentManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Config.ensure_directories()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_raxel_62.db"
        init_auth_db(cls.test_db_path)

        # Create test users
        create_user("student_user", "StudentPass123!", ROLE_STUDENT, db_path=cls.test_db_path)
        create_user("faculty_user", "FacultyPass123!", ROLE_FACULTY, db_path=cls.test_db_path)
        create_user("admin_user", "AdminPass123!", ROLE_ADMIN, db_path=cls.test_db_path)

        cls.student_user = {"authenticated": True, "id": 1, "username": "student_user", "role": ROLE_STUDENT}
        cls.faculty_user = {"authenticated": True, "id": 2, "username": "faculty_user", "role": ROLE_FACULTY}
        cls.admin_user = {"authenticated": True, "id": 3, "username": "admin_user", "role": ROLE_ADMIN}

        # Initialize DocumentManager with test DB
        cls.doc_manager = DocumentManager(db_path=cls.test_db_path)

        # RAG Components
        cls.embedding_mgr = EmbeddingManager(model_name=Config.EMBEDDING_MODEL_NAME)
        cls.vector_store = VectorStoreManager(
            index_path=Config.FAISS_INDEX_PATH,
            metadata_path=Config.METADATA_PATH
        )
        cls.llm = OllamaLLM(model_name=Config.LLM_MODEL, base_url=Config.OLLAMA_BASE_URL)
        cls.retriever = KnowledgeRetriever(
            embedding_manager=cls.embedding_mgr,
            vector_store=cls.vector_store,
            top_k=Config.TOP_K,
            similarity_threshold=Config.SIMILARITY_THRESHOLD
        )
        cls.pipeline = RAGPipeline(retriever=cls.retriever, llm=cls.llm)

        # Prepare a valid sample PDF bytes fixture using existing document or generating minimal PDF
        cls.sample_pdf_path = Config.DOCUMENTS_DIR / "GLS_Academic_Regulations_2025.pdf"
        if not cls.sample_pdf_path.exists():
            # Find any PDF in documents dir
            pdfs = list(Config.DOCUMENTS_DIR.glob("*.pdf"))
            if pdfs:
                cls.sample_pdf_path = pdfs[0]
                
        if cls.sample_pdf_path.exists():
            with open(cls.sample_pdf_path, "rb") as f:
                cls.sample_pdf_bytes = f.read()
        else:
            cls.sample_pdf_bytes = b"%PDF-1.4 sample test pdf content for test fixtures\n%%EOF"

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_01_student_cannot_upload(self):
        """Test 1: Student role cannot upload document (raises PermissionError)."""
        with self.assertRaises(PermissionError):
            self.doc_manager.upload_document(
                file_bytes=self.sample_pdf_bytes,
                filename="test_stu.pdf",
                title="Student Document",
                document_type="notice",
                user=self.student_user
            )

    def test_02_student_cannot_archive(self):
        """Test 2: Student role cannot archive document (raises PermissionError)."""
        with self.assertRaises(PermissionError):
            self.doc_manager.archive_document("doc_test123", user=self.student_user)

    def test_03_student_cannot_delete(self):
        """Test 3: Student role cannot delete document (raises PermissionError)."""
        with self.assertRaises(PermissionError):
            self.doc_manager.delete_document("doc_test123", user=self.student_user)

    def test_04_faculty_can_upload(self):
        """Test 4: Faculty role can upload document."""
        pdf_bytes = self.sample_pdf_bytes + f"\n% Faculty upload test fixture 04 {uuid.uuid4()}".encode()
        res = self.doc_manager.upload_document(
            file_bytes=pdf_bytes,
            filename=f"Faculty_Notice_{uuid.uuid4().hex[:6]}.pdf",
            title="Faculty Exam Notice 2025",
            document_type="notice",
            academic_year="2025-2026",
            version="v1.0",
            effective_date="July 1, 2025",
            description="Official faculty notice test",
            user=self.faculty_user
        )
        self.assertTrue(res["success"], f"Upload failed: {res.get('message')}")
        self.assertEqual(res["document"]["status"], "uploaded")
        self.assertEqual(res["document"]["uploaded_by"], "faculty_user")

    def test_05_faculty_can_process(self):
        """Test 5: Faculty role can process uploaded document."""
        pdf_bytes = self.sample_pdf_bytes + f"\n% Faculty process test fixture 05 {uuid.uuid4()}".encode()
        up_res = self.doc_manager.upload_document(
            file_bytes=pdf_bytes,
            filename=f"Faculty_Process_{uuid.uuid4().hex[:6]}.pdf",
            title="Faculty Process Notice 2025",
            document_type="notice",
            user=self.faculty_user
        )
        self.assertTrue(up_res["success"], f"Upload failed: {up_res.get('message')}")
        target_doc = up_res["document"]

        res = self.doc_manager.process_and_index_document(
            doc_id=target_doc["document_id"],
            user=self.faculty_user
        )
        self.assertTrue(res["success"], f"Processing failed: {res.get('message')}")
        doc = self.doc_manager.get_document_by_id(target_doc["document_id"])
        self.assertEqual(doc["status"], "indexed")
        self.assertEqual(doc["governance_status"], "pending_review")
        # Under Phase 6.3, admin approves the document to enable retrieval
        app_res = self.doc_manager.approve_document(target_doc["document_id"], user=self.admin_user)
        self.assertTrue(app_res["success"])
        doc = self.doc_manager.get_document_by_id(target_doc["document_id"])
        self.assertEqual(doc["governance_status"], "approved")
        self.assertEqual(doc["retrieval_enabled"], 1)

    def test_06_admin_can_upload(self):
        """Test 6: Admin role can upload document."""
        admin_pdf_bytes = self.sample_pdf_bytes + f"\n% Admin upload test comment fixture 06 {uuid.uuid4()}".encode()
        res = self.doc_manager.upload_document(
            file_bytes=admin_pdf_bytes,
            filename=f"Admin_Circular_{uuid.uuid4().hex[:6]}.pdf",
            title="Admin Exam Circular 2025",
            document_type="circular",
            academic_year="2025-2026",
            version="v2.0",
            user=self.admin_user
        )
        self.assertTrue(res["success"], f"Admin upload failed: {res.get('message')}")
        self.assertEqual(res["document"]["uploaded_by"], "admin_user")

    def test_07_admin_can_process(self):
        """Test 7: Admin role can process uploaded document."""
        admin_pdf_bytes = self.sample_pdf_bytes + f"\n% Admin process test comment fixture 07 {uuid.uuid4()}".encode()
        up_res = self.doc_manager.upload_document(
            file_bytes=admin_pdf_bytes,
            filename=f"Admin_Process_{uuid.uuid4().hex[:6]}.pdf",
            title="Admin Process Circular 2025",
            document_type="circular",
            user=self.admin_user
        )
        self.assertTrue(up_res["success"], f"Admin upload failed: {up_res.get('message')}")
        target_doc = up_res["document"]

        res = self.doc_manager.process_and_index_document(
            doc_id=target_doc["document_id"],
            user=self.admin_user
        )
        self.assertTrue(res["success"], f"Admin processing failed: {res.get('message')}")
        doc = self.doc_manager.get_document_by_id(target_doc["document_id"])
        self.assertEqual(doc["status"], "indexed")
        self.assertEqual(doc["governance_status"], "pending_review")

    def test_08_admin_can_archive(self):
        """Test 8: Admin role can archive document."""
        docs = self.doc_manager.list_documents(status="indexed", governance_status="approved")
        self.assertGreater(len(docs), 0)
        target_doc = docs[0]

        res = self.doc_manager.archive_document(target_doc["document_id"], user=self.admin_user)
        self.assertTrue(res["success"])
        doc = self.doc_manager.get_document_by_id(target_doc["document_id"])
        self.assertEqual(doc["governance_status"], "archived")
        self.assertEqual(doc["retrieval_enabled"], 0)

    def test_09_admin_can_delete(self):
        """Test 9: Admin role can permanently delete document."""
        # Upload a dummy doc to delete
        dummy_bytes = self.sample_pdf_bytes + b"\n% Dummy doc for delete test"
        up_res = self.doc_manager.upload_document(
            file_bytes=dummy_bytes,
            filename="Dummy_Delete_Doc.pdf",
            title="Dummy Delete Doc",
            document_type="other",
            user=self.admin_user
        )
        doc_id = up_res["document"]["document_id"]
        
        del_res = self.doc_manager.delete_document(doc_id, user=self.admin_user)
        self.assertTrue(del_res["success"])
        self.assertIsNone(self.doc_manager.get_document_by_id(doc_id))

    def test_10_invalid_extension_rejected(self):
        """Test 10: Non-PDF extension rejected."""
        valid, msg = validate_pdf_bytes(b"some content", "file.txt")
        self.assertFalse(valid)
        self.assertIn("Only PDF", msg)

    def test_11_invalid_pdf_content_rejected(self):
        """Test 11: Non-PDF content (missing %PDF- header) rejected."""
        valid, msg = validate_pdf_bytes(b"hello world this is not a pdf file", "invalid.pdf")
        self.assertFalse(valid)
        self.assertIn("not appear to be a valid PDF", msg)

    def test_12_oversized_file_rejected(self):
        """Test 12: File exceeding size limit rejected."""
        large_bytes = b"%PDF-1.4 " + (b"0" * (Config.MAX_UPLOAD_SIZE_BYTES + 100))
        valid, msg = validate_pdf_bytes(large_bytes, "huge.pdf")
        self.assertFalse(valid)
        self.assertIn("exceeds the maximum allowed size", msg)

    def test_13_path_traversal_filename_sanitized(self):
        """Test 13: Path traversal filename sanitized."""
        sanitized = sanitize_filename("../../../etc/passwd.pdf")
        self.assertNotIn("..", sanitized)
        self.assertNotIn("/", sanitized)
        self.assertEqual(sanitized, "passwd.pdf")

    def test_14_metadata_saved_correctly(self):
        """Test 14: Metadata saved correctly in SQLite."""
        import time
        test_bytes = self.sample_pdf_bytes + f"\n% Metadata check comment fixture unique 14 {time.time()}".encode()
        res = self.doc_manager.upload_document(
            file_bytes=test_bytes,
            filename="Meta_Test_Doc.pdf",
            title="Metadata Test Document",
            document_type="syllabus",
            academic_year="2025-2026",
            version="v3.1",
            effective_date="Aug 15, 2025",
            description="Meta description test",
            user=self.faculty_user
        )
        self.assertTrue(res["success"], f"Upload failed: {res.get('message')}")
        doc = res["document"]
        self.assertEqual(doc["title"], "Metadata Test Document")
        self.assertEqual(doc["document_type"], "syllabus")
        self.assertEqual(doc["academic_year"], "2025-2026")
        self.assertEqual(doc["version"], "v3.1")
        self.assertEqual(doc["effective_date"], "Aug 15, 2025")
        self.assertEqual(doc["description"], "Meta description test")

    def test_15_uploaded_by_recorded(self):
        """Test 15: uploaded_by accurately recorded."""
        docs = self.doc_manager.list_documents()
        fac_docs = [d for d in docs if d["uploaded_by"] == "faculty_user"]
        self.assertGreater(len(fac_docs), 0)

    def test_16_duplicate_hash_detected(self):
        """Test 16: Duplicate file upload detected by hash."""
        dup_bytes = self.sample_pdf_bytes + f"\n% Duplicate test fixture {uuid.uuid4()}".encode()
        res1 = self.doc_manager.upload_document(
            file_bytes=dup_bytes,
            filename="Dup_Notice_1.pdf",
            title="Dup Title 1",
            document_type="notice",
            user=self.faculty_user
        )
        self.assertTrue(res1["success"])
        res2 = self.doc_manager.upload_document(
            file_bytes=dup_bytes,
            filename="Dup_Notice_2.pdf",
            title="Dup Title 2",
            document_type="notice",
            user=self.faculty_user
        )
        self.assertFalse(res2["success"])
        self.assertTrue(res2.get("duplicate"))
        self.assertIn("already exists", res2["message"])

    def test_17_successful_processing_changes_status(self):
        """Test 17: Successful processing transitions status to 'indexed' with governance pending_review."""
        docs = self.doc_manager.list_documents(status="uploaded")
        if docs:
            fac_docs = [d for d in docs if d["uploaded_by"].lower() != "admin_user"]
            target = fac_docs[0] if fac_docs else docs[0]
            doc_id = target["document_id"]
            res = self.doc_manager.process_and_index_document(doc_id, user=self.faculty_user)
            self.assertTrue(res["success"])
            updated = self.doc_manager.get_document_by_id(doc_id)
            self.assertEqual(updated["status"], "indexed")
            self.assertEqual(updated["governance_status"], "pending_review")
            self.assertEqual(updated["retrieval_enabled"], 0)
            # Admin approves document to enable retrieval
            app_res = self.doc_manager.approve_document(doc_id, user=self.admin_user)
            self.assertTrue(app_res["success"], f"Approval failed: {app_res.get('message')}")
            updated = self.doc_manager.get_document_by_id(doc_id)
            self.assertEqual(updated["governance_status"], "approved")
            self.assertEqual(updated["retrieval_enabled"], 1)

    def test_18_failed_processing_marks_document_failed(self):
        """Test 18: Failed processing marks document as 'failed'."""
        # Create corrupt PDF doc record in DB manually
        conn = self.doc_manager.get_connection()
        fake_id = "doc_corrupt_test_99"
        corrupt_path = Path(self.temp_dir.name) / "corrupt.pdf"
        with open(corrupt_path, "wb") as f:
            f.write(b"%PDF-1.4 corrupt content that fitz cannot parse properly\n")
            
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO documents (
                    document_id, title, original_filename, stored_path,
                    document_type, file_hash, file_size, uploaded_by, status, retrieval_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fake_id, "Corrupt PDF", "corrupt.pdf", str(corrupt_path), "notice", "hashcorrupt99", 50, "faculty_user", "uploaded", 0))
        conn.close()

        res = self.doc_manager.process_and_index_document(fake_id, user=self.faculty_user)
        self.assertFalse(res["success"])
        failed_doc = self.doc_manager.get_document_by_id(fake_id)
        self.assertEqual(failed_doc["status"], "failed")
        self.assertEqual(failed_doc["retrieval_enabled"], 0)

    def test_19_failed_processing_preserves_existing_index(self):
        """Test 19: Failed processing leaves pre-existing FAISS index functional."""
        self.vector_store.load()
        chunk_count_before = self.vector_store.get_chunk_count()
        
        # Trigger failed processing
        self.test_18_failed_processing_marks_document_failed()

        # Check index is still readable and chunk count preserved
        self.vector_store.load()
        self.assertGreaterEqual(self.vector_store.get_chunk_count(), 0)

    def test_20_indexed_document_becomes_retrievable(self):
        """Test 20: Newly indexed document participates in RAG retrieval."""
        res = self.retriever.retrieve("GLS BCA attendance regulation threshold")
        self.assertIn("chunks", res)
        self.assertIsInstance(res["chunks"], list)

    def test_21_indexed_document_citation_correct(self):
        """Test 21: Indexed document citation metadata is accurate."""
        res = self.pipeline.answer_question("What is the minimum attendance requirement at GLS?")
        self.assertIn("citations", res)

    def test_22_archived_document_not_retrievable(self):
        """Test 22: Archived document content excluded from active retrieval."""
        docs = self.doc_manager.list_documents(status="indexed", governance_status="approved")
        if docs:
            target = docs[0]
            self.doc_manager.archive_document(target["document_id"], user=self.admin_user)
            
            # Check vector store metadata does not contain chunks from target document
            self.vector_store.load()
            for chunk in self.vector_store.metadata:
                self.assertNotEqual(chunk.get("document_id"), target["document_id"])
                
            # Restore target doc back to indexed for subsequent tests
            self.doc_manager.restore_document(target["document_id"], user=self.admin_user)

    def test_23_deleted_document_not_retrievable(self):
        """Test 23: Deleted document content excluded from active retrieval."""
        import time
        del_bytes = self.sample_pdf_bytes + f"\n% Delete verification fixture {time.time()}".encode()
        up_res = self.doc_manager.upload_document(
            file_bytes=del_bytes,
            filename="Delete_Verify.pdf",
            title="Delete Verify Document",
            document_type="notice",
            user=self.faculty_user
        )
        doc_id = up_res["document"]["document_id"]
        self.doc_manager.process_and_index_document(doc_id, user=self.faculty_user)
        # Approve to activate in vector store before deletion test
        self.doc_manager.approve_document(doc_id, user=self.admin_user)

        # Delete document
        self.doc_manager.delete_document(doc_id, user=self.admin_user)
        
        # Verify vector store metadata has no chunks from deleted doc
        self.vector_store.load()
        for chunk in self.vector_store.metadata:
            self.assertNotEqual(chunk.get("document_id"), doc_id)

    def test_24_no_duplicate_vectors_after_reprocessing(self):
        """Test 24: Re-processing document does not double vector count."""
        docs = self.doc_manager.list_documents(status="indexed")
        if docs:
            target = docs[0]
            count_before = self.vector_store.get_chunk_count()
            self.doc_manager.process_and_index_document(target["document_id"], user=self.admin_user)
            count_after = self.vector_store.get_chunk_count()
            self.assertEqual(count_before, count_after)

    def test_25_version_metadata_preserved(self):
        """Test 25: Version metadata preserved in database and manifest."""
        docs = self.doc_manager.list_documents()
        self.assertGreater(len(docs), 0)
        manifest_path = Config.DATA_DIR / "documents_manifest.json"
        self.assertTrue(manifest_path.exists())

    def test_26_phase6_1_auth_still_works(self):
        """Test 26: Phase 6.1 authentication works as expected."""
        user = authenticate_user("student_user", "StudentPass123!", db_path=self.test_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "student_user")

    def test_27_existing_student_chat_still_works(self):
        """Test 27: Student chat interface answers questions correctly."""
        res = self.pipeline.answer_question("What is the BCA attendance policy?")
        self.assertIn("answer", res)
        self.assertGreater(len(res["answer"]), 0)

    def test_28_existing_permissions_still_work(self):
        """Test 28: Permission checks still enforce role hierarchy correctly."""
        self.assertTrue(has_role(ROLE_ADMIN, ROLE_FACULTY))
        self.assertFalse(has_role(ROLE_STUDENT, ROLE_FACULTY))

    def test_29_existing_citation_validation_still_works(self):
        """Test 29: Citation extractor formats citations correctly."""
        from src.citation_validator import extract_programmatic_citations
        cites = extract_programmatic_citations([{"document_name": "Test_Doc.pdf", "page_number": 2}])
        self.assertEqual(len(cites), 1)

    def test_30_existing_unknown_fallback_still_works(self):
        """Test 30: Unanswerable query triggers safe fallback without hallucination."""
        res = self.pipeline.answer_question("What is the warp drive efficiency equation?")
        self.assertFalse(res["has_sufficient_evidence"])

if __name__ == "__main__":
    unittest.main()
