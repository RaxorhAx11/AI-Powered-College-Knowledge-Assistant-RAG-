"""
Phase 6.1 Authentication, Role Separation & Basic Panels Test Suite (Project RAXEL).

Tests:
1. User creation in SQLite auth DB
2. Password hashing & salt verification
3. Correct login authentication
4. Incorrect password rejection
5. Unknown user rejection
6. Inactive user rejection
7. Student role assignment
8. Faculty role assignment
9. Admin role assignment
10. Protected faculty function execution
11. Protected admin function execution
12. Student denied faculty access
13. Student denied admin access
14. Logout execution
15. Session state cleared
16. Student A history isolation from Student B
17. RAG chat working after login
18. Citation accuracy after login
19. Safe fallback mechanism after login
20. Phase 1 regression
21. Phase 2 regression
22. Phase 3 regression
23. Phase 4 regression
24. Phase 5 regression
25. Phase 5.1 regression
"""

import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.auth import (
    init_auth_db,
    create_user,
    authenticate_user,
    hash_password,
    verify_password,
    get_user_by_username
)
from src.permissions import (
    has_role,
    require_role,
    login_user,
    logout_user,
    get_current_user,
    ROLE_STUDENT,
    ROLE_FACULTY,
    ROLE_ADMIN
)
from src.pdf_processor import PDFProcessor
from src.chunker import TextChunker
from src.embeddings import EmbeddingManager
from src.vector_store import VectorStoreManager
from src.retriever import KnowledgeRetriever
from src.llm import OllamaLLM
from src.rag_pipeline import RAGPipeline

class TestPhase61AuthAndRoles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Config.ensure_directories()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_raxel.db"
        init_auth_db(cls.test_db_path)
        
        # Initialize RAG components for regression testing
        cls.processor = PDFProcessor()
        cls.chunker = TextChunker(chunk_size=Config.CHUNK_SIZE, chunk_overlap=Config.CHUNK_OVERLAP)
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

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_01_user_creation(self):
        """Test 1: User creation in SQLite auth DB using create_user."""
        res = create_user("test_user_01", "Password123!", "student", db_path=self.test_db_path)
        self.assertTrue(res)
        user = get_user_by_username("test_user_01", db_path=self.test_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "test_user_01")
        self.assertEqual(user["role"], "student")

    def test_02_password_hashing(self):
        """Test 2: Password hashing produces PBKDF2 salt format and verify_password works."""
        pwd = "SecretPassword456!"
        hashed = hash_password(pwd)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertNotIn(pwd, hashed)  # Plaintext password must NOT be in hash string
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword!", hashed))

    def test_03_correct_login(self):
        """Test 3: Correct login authentication returns user dictionary."""
        create_user("valid_user", "ValidPass789!", "student", db_path=self.test_db_path)
        user = authenticate_user("valid_user", "ValidPass789!", db_path=self.test_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "valid_user")
        self.assertEqual(user["role"], "student")
        self.assertNotIn("password_hash", user)  # Password hash not exposed in auth return

    def test_04_incorrect_password(self):
        """Test 4: Incorrect password returns None."""
        create_user("user_wrong_pwd", "CorrectPassword1!", "faculty", db_path=self.test_db_path)
        user = authenticate_user("user_wrong_pwd", "WrongPassword1!", db_path=self.test_db_path)
        self.assertIsNone(user)

    def test_05_unknown_user(self):
        """Test 5: Unknown username returns None."""
        user = authenticate_user("nonexistent_user_99", "SomePassword!", db_path=self.test_db_path)
        self.assertIsNone(user)

    def test_06_inactive_user(self):
        """Test 6: Inactive user cannot authenticate."""
        create_user("inactive_user", "Password123!", "student", active=False, db_path=self.test_db_path)
        user = authenticate_user("inactive_user", "Password123!", db_path=self.test_db_path)
        self.assertIsNone(user)

    def test_07_student_role(self):
        """Test 7: Student role assignment and verification."""
        create_user("student_role_user", "Pass123!", "student", db_path=self.test_db_path)
        user = get_user_by_username("student_role_user", db_path=self.test_db_path)
        self.assertEqual(user["role"], ROLE_STUDENT)
        self.assertTrue(has_role(user["role"], ROLE_STUDENT))

    def test_08_faculty_role(self):
        """Test 8: Faculty role assignment and permission hierarchy."""
        create_user("faculty_role_user", "Pass123!", "faculty", db_path=self.test_db_path)
        user = get_user_by_username("faculty_role_user", db_path=self.test_db_path)
        self.assertEqual(user["role"], ROLE_FACULTY)
        self.assertTrue(has_role(user["role"], ROLE_FACULTY))
        self.assertTrue(has_role(user["role"], ROLE_STUDENT))  # Faculty includes student level

    def test_09_admin_role(self):
        """Test 9: Admin role assignment and full permission hierarchy."""
        create_user("admin_role_user", "Pass123!", "admin", db_path=self.test_db_path)
        user = get_user_by_username("admin_role_user", db_path=self.test_db_path)
        self.assertEqual(user["role"], ROLE_ADMIN)
        self.assertTrue(has_role(user["role"], ROLE_ADMIN))
        self.assertTrue(has_role(user["role"], ROLE_FACULTY))
        self.assertTrue(has_role(user["role"], ROLE_STUDENT))

    def test_10_protected_faculty_function(self):
        """Test 10: Faculty user can invoke faculty-protected function."""
        faculty_user = {"authenticated": True, "id": 2, "username": "fac1", "role": "faculty"}
        self.assertTrue(require_role(ROLE_FACULTY, faculty_user))

    def test_11_protected_admin_function(self):
        """Test 11: Admin user can invoke admin-protected function."""
        admin_user = {"authenticated": True, "id": 3, "username": "adm1", "role": "admin"}
        self.assertTrue(require_role(ROLE_ADMIN, admin_user))

    def test_12_student_denied_faculty_access(self):
        """Test 12: Student is denied faculty-level function access."""
        student_user = {"authenticated": True, "id": 1, "username": "stu1", "role": "student"}
        with self.assertRaises(PermissionError):
            require_role(ROLE_FACULTY, student_user)

    def test_13_student_denied_admin_access(self):
        """Test 13: Student is denied admin-level function access."""
        student_user = {"authenticated": True, "id": 1, "username": "stu1", "role": "student"}
        with self.assertRaises(PermissionError):
            require_role(ROLE_ADMIN, student_user)

    def test_14_logout(self):
        """Test 14: Logout clears authentication state."""
        session = {"authenticated": True, "user_id": 1, "username": "stu1", "role": "student", "messages": ["hello"]}
        logout_user(session)
        self.assertFalse(session["authenticated"])
        self.assertNotIn("user_id", session)
        self.assertNotIn("username", session)
        self.assertNotIn("role", session)

    def test_15_session_state_cleared(self):
        """Test 15: Session state cleared upon logout."""
        session = {}
        user_dict = {"id": 1, "username": "student_a", "role": "student"}
        login_user(session, user_dict)
        self.assertTrue(session["authenticated"])
        logout_user(session)
        self.assertFalse(session["authenticated"])
        self.assertFalse(get_current_user(session).get("authenticated"))

    def test_16_chat_history_isolation(self):
        """Test 16: Student A chat history does not leak to Student B."""
        session = {}
        # Student A logs in and asks question
        student_a = {"id": 10, "username": "student_a", "role": "student"}
        login_user(session, student_a)
        session["messages"].append({"role": "user", "content": "What is Student A GPA?"})
        session["messages"].append({"role": "assistant", "content": "GPA is 3.8."})
        self.assertEqual(len(session["messages"]), 2)

        # Student A logs out
        logout_user(session)
        self.assertEqual(len(session["messages"]), 0)

        # Student B logs in
        student_b = {"id": 11, "username": "student_b", "role": "student"}
        login_user(session, student_b)
        self.assertEqual(len(session["messages"]), 0)  # Student A history MUST be empty for Student B

    def test_17_rag_chat_still_works(self):
        """Test 17: Existing RAG pipeline answers questions after authentication."""
        if not self.vector_store.is_indexed() or self.vector_store.get_chunk_count() == 0:
            self.skipTest("Vector store not populated; skipping live RAG query assertion.")
        res = self.pipeline.answer_question("What is the minimum attendance requirement at GLS?")
        self.assertIn("answer", res)
        self.assertGreater(len(res["answer"]), 0)

    def test_18_citations_still_work(self):
        """Test 18: RAG citations structure is preserved after authentication integration."""
        if not self.vector_store.is_indexed() or self.vector_store.get_chunk_count() == 0:
            self.skipTest("Vector store not populated; skipping citation assertion.")
        res = self.pipeline.answer_question("What are the attendance rules for BCA?")
        self.assertIn("citations", res)
        self.assertIsInstance(res["citations"], list)

    def test_19_safe_fallback_still_works(self):
        """Test 19: Unsupported queries trigger safe grounded fallback."""
        res = self.pipeline.answer_question("What is the quantum computing algorithm for warp drive?")
        self.assertIn("answer", res)
        self.assertFalse(res["has_sufficient_evidence"])

    def test_20_phase1_regression(self):
        """Test 20: Phase 1 regression - PDF processor and text chunker integrity."""
        pages = self.processor.process_directory(Config.DOCUMENTS_DIR)
        self.assertGreater(len(pages), 0)
        chunks = self.chunker.chunk_documents(pages[:2])
        self.assertGreater(len(chunks), 0)

    def test_21_phase2_regression(self):
        """Test 21: Phase 2 regression - Vector store embedding & retrieval engine."""
        stats = self.vector_store.get_stats()
        self.assertIn("chunk_count", stats)
        self.assertIn("document_count", stats)

    def test_22_phase3_regression(self):
        """Test 22: Phase 3 regression - Evidence gating and similarity threshold."""
        query_res = self.retriever.retrieve("GLS BCA attendance regulation threshold")
        self.assertIn("chunks", query_res)
        self.assertIsInstance(query_res["chunks"], list)

    def test_23_phase4_regression(self):
        """Test 23: Phase 4 regression - Citation validator and answer formatting."""
        from src.citation_validator import extract_programmatic_citations
        cites = extract_programmatic_citations([{"document_name": "GLS_Academic_Regulations_2025.pdf", "page_number": 1}])
        self.assertEqual(len(cites), 1)

    def test_24_phase5_regression(self):
        """Test 24: Phase 5 regression - Synthetic document classification and metadata manifest."""
        manifest_path = Config.DOCUMENTS_DIR.parent / "documents_manifest.json"
        self.assertTrue(manifest_path.exists())

    def test_25_phase5_1_regression(self):
        """Test 25: Phase 5.1 regression - Query resolution and follow-up handling."""
        from src.query_resolver import needs_resolution
        self.assertTrue(needs_resolution("What about it?"))
        self.assertFalse(needs_resolution("What is the minimum attendance requirement at GLS University?"))

if __name__ == "__main__":
    unittest.main()
