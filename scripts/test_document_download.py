"""
Test Document View and Download API Endpoints
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.dependencies import ComponentRegistry

client = TestClient(app)

class TestDocumentDownload(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ComponentRegistry.initialize()
        doc_mgr = ComponentRegistry.get_doc_manager()
        docs = doc_mgr.list_documents()
        cls.test_doc_id = docs[0]["document_id"] if docs else None

    def test_01_view_document_inline(self):
        if not self.test_doc_id:
            self.skipTest("No test documents found in DB")

        res = client.get(f"/api/documents/{self.test_doc_id}/download?disposition=inline")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")
        self.assertIn("inline", res.headers.get("content-disposition", ""))

    def test_02_download_document_attachment(self):
        if not self.test_doc_id:
            self.skipTest("No test documents found in DB")

        res = client.get(f"/api/documents/{self.test_doc_id}/download?disposition=attachment")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")
        self.assertIn("attachment", res.headers.get("content-disposition", ""))

    def test_03_download_with_query_token(self):
        if not self.test_doc_id:
            self.skipTest("No test documents found in DB")

        # Signup & Login as faculty
        import uuid
        username = f"fac_test_{uuid.uuid4().hex[:6]}"
        from src.auth import create_user
        from src.permissions import ROLE_FACULTY
        create_user(username, "password123", role=ROLE_FACULTY)

        login_res = client.post("/api/auth/login", json={"username": username, "password": "password123"})
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["token"]

        res = client.get(f"/api/documents/{self.test_doc_id}/download?token={token}&disposition=inline")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")

if __name__ == "__main__":
    unittest.main()
