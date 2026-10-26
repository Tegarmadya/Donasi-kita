"""
Unit and Integration Tests for Authentication & Session Management.
Tests valid/invalid login, duplicate email handling, bcrypt hashing,
and role verification.
"""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import auth_service
import db


class TestAuthService(unittest.TestCase):

    def setUp(self):
        self.valid_email = "admin@donasikita.id"
        self.valid_password = "password123"

    def test_tc01_login_success(self):
        """TC-AUTH-01: Login with correct credentials."""
        res = auth_service.login(self.valid_email, self.valid_password)
        self.assertTrue(res["success"], "Login should succeed with valid credentials")
        self.assertIn("session_token", res)
        self.assertEqual(res["user"]["role"], "admin")

    def test_tc02_login_invalid_password(self):
        """TC-AUTH-02: Login with incorrect password."""
        res = auth_service.login(self.valid_email, "wrongpassword999")
        self.assertFalse(res["success"], "Login should fail with wrong password")
        self.assertIn("tidak cocok", res["message"])

    def test_tc03_login_nonexistent_user(self):
        """TC-AUTH-03: Login with email that does not exist."""
        res = auth_service.login("nonexistent_user@donasikita.id", "password123")
        self.assertFalse(res["success"], "Login should fail for non-existent user")

    def test_tc04_password_is_hashed_bcrypt(self):
        """TC-AUTH-04: Verify password in database is hashed using bcrypt."""
        user = db.execute_query(
            "SELECT password_hash FROM users WHERE email = %s",
            (self.valid_email,),
            fetch_one=True
        )
        self.assertIsNotNone(user)
        pwd_hash = user["password_hash"]
        self.assertTrue(pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$"), "Password must be bcrypt hashed")
        self.assertNotEqual(pwd_hash, self.valid_password)

    def test_tc05_register_duplicate_email(self):
        """TC-AUTH-05: Registration fails when email already exists."""
        res = auth_service.register(
            full_name="Duplicate User",
            email=self.valid_email,
            password="newpassword123",
            role="donatur"
        )
        self.assertFalse(res["success"], "Registration should reject duplicate email")
        self.assertIn("sudah terdaftar", res["message"])

    def test_tc06_role_access_control(self):
        """TC-AUTH-06: Role authorization middleware enforcement."""
        # Donor session
        donor_res = auth_service.login("budi@donasikita.id", "password123")
        donor_token = donor_res["session_token"]

        # Donor trying to access admin-only user list should raise PermissionError
        with self.assertRaises(PermissionError):
            auth_service.get_all_users(donor_token)

    def test_tc07_logout_terminates_session(self):
        """TC-AUTH-07: Logout invalidates active session token."""
        login_res = auth_service.login("siti@donasikita.id", "password123")
        token = login_res["session_token"]
        
        self.assertIsNotNone(auth_service.get_session_user(token))
        auth_service.logout(token)
        self.assertIsNone(auth_service.get_session_user(token))


if __name__ == "__main__":
    unittest.main()
