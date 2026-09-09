"""
Automated Test Suite for RAXEL Phase 7 Backend API & Security Matrix.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestPhase7BackendAPI(unittest.TestCase):

    def test_01_health_check(self):
        res = client.get("/api/health_check")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_02_guest_me(self):
        res = client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["authenticated"])
        self.assertEqual(data["role"], "student")
        self.assertEqual(data["username"], "Guest Student")

    def test_03_guest_chat(self):
        res = client.post("/api/chat", json={"message": "What is the minimum attendance requirement?"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("citations", data)
        self.assertIn("has_sufficient_evidence", data)

    def test_04_auth_flow(self):
        import uuid
        username = f"test_student_{uuid.uuid4().hex[:8]}"
        password = "password123"

        # Signup as student explicitly
        signup_res = client.post("/api/auth/signup", json={
            "username": username,
            "password": password
        })
        self.assertEqual(signup_res.status_code, 200)

        # Login
        login_res = client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["token"]
        self.assertTrue(token)

        # Authenticated Me
        me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertTrue(me_res.json()["authenticated"])
        self.assertEqual(me_res.json()["username"], username)
        self.assertEqual(me_res.json()["role"], "student")

    def test_05_signup_role_restrictions(self):
        """
        Verify that public signup defaults to Student and rejects Faculty/Admin role requests.
        """
        import uuid
        uid = str(uuid.uuid4())[:8]

        # 1. Default role registration (no role specified)
        res_default = client.post("/api/auth/signup", json={
            "username": f"user_default_{uid}",
            "password": "Password123!"
        })
        self.assertEqual(res_default.status_code, 200)
        self.assertEqual(res_default.json()["role"], "student")

        # 2. Reject public signup with Faculty role
        res_fac = client.post("/api/auth/signup", json={
            "username": f"user_fac_{uid}",
            "password": "Password123!",
            "role": "faculty"
        })
        self.assertEqual(res_fac.status_code, 400)
        self.assertIn("Public registration is only allowed for the Student role", res_fac.json()["detail"])

        # 3. Reject public signup with Admin role
        res_adm = client.post("/api/auth/signup", json={
            "username": f"user_adm_{uid}",
            "password": "Password123!",
            "role": "admin"
        })
        self.assertEqual(res_adm.status_code, 400)
        self.assertIn("Public registration is only allowed for the Student role", res_adm.json()["detail"])

    def test_06_rbac_security_matrix(self):
        """
        Negative Security Matrix:
        - Guest -> Admin (/api/admin/users) -> FAIL (401)
        - Student -> Admin (/api/admin/users) -> FAIL (403)
        - Student -> Role Change -> FAIL (403)
        """
        import uuid
        st_user = f"st_matrix_{uuid.uuid4().hex[:8]}"
        st_pass = "password123"

        # Create fresh student user
        signup_res = client.post("/api/auth/signup", json={"username": st_user, "password": st_pass})
        self.assertEqual(signup_res.status_code, 200)

        # Guest to Admin
        guest_res = client.get("/api/admin/users")
        self.assertIn(guest_res.status_code, [401, 403])

        # Student to Admin
        st_login = client.post("/api/auth/login", json={"username": st_user, "password": st_pass})
        self.assertEqual(st_login.status_code, 200)
        st_token = st_login.json()["token"]
        headers = {"Authorization": f"Bearer {st_token}"}

        st_admin_res = client.get("/api/admin/users", headers=headers)
        self.assertEqual(st_admin_res.status_code, 403)

        st_role_change = client.patch(f"/api/admin/users/{st_user}/role", json={"role": "admin"}, headers=headers)
        self.assertEqual(st_role_change.status_code, 403)

        # Student to Document Delete -> FAIL (403)
        st_del_res = client.delete("/api/documents/doc_test_123", headers=headers)
        self.assertEqual(st_del_res.status_code, 403)

        # Student to Upload Document -> FAIL (403)
        st_up_res = client.post("/api/documents/upload", headers=headers)
        self.assertEqual(st_up_res.status_code, 403)

if __name__ == "__main__":
    unittest.main()
