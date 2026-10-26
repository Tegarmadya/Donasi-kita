"""
Unit and Integration Tests for Campaign Management and Fund Usage.
Tests CRUD, status workflow (pending -> active -> rejected),
fund usage limitations, and anonymous masking.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import auth_service, campaign_service
import db


class TestCampaignService(unittest.TestCase):

    def setUp(self):
        # Fundraiser session
        res_f = auth_service.login("lentera@donasikita.id", "password123")
        self.fundraiser_token = res_f["session_token"]

        # Admin session
        res_a = auth_service.login("admin@donasikita.id", "password123")
        self.admin_token = res_a["session_token"]

    def test_tc08_campaign_creation_validation(self):
        """TC-CAMP-01: Form validation for campaign creation."""
        # Invalid short title
        res1 = campaign_service.create_campaign(
            self.fundraiser_token, "Pendek", 1, 50000000.0, "2026-12-31",
            "Deskripsi yang cukup panjang untuk kebutuhan validasi.",
            "Cerita lengkap yang memenuhi batas minimal karakter validasi cerita...",
            "campaign_default.jpg"
        )
        self.assertFalse(res1["success"], "Short title should be rejected")

        # Invalid target < 100k
        res2 = campaign_service.create_campaign(
            self.fundraiser_token, "Program Validasi Target Dana Terlalu Kecil", 1, 50000.0, "2026-12-31",
            "Deskripsi yang cukup panjang untuk kebutuhan validasi.",
            "Cerita lengkap yang memenuhi batas minimal karakter validasi cerita...",
            "campaign_default.jpg"
        )
        self.assertFalse(res2["success"], "Target below 100.000 should be rejected")

    def test_tc09_campaign_lifecycle_approval(self):
        """TC-CAMP-02: Campaign creation enters pending, approved by admin."""
        deadline = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
        create_res = campaign_service.create_campaign(
            self.fundraiser_token,
            "Program Uji Kurasi Admin DonasiKita Batch 2",
            1,
            25000000.0,
            deadline,
            "Deskripsi uji kurasi program sosial kemanusiaan.",
            "Cerita lengkap program yang diuji dalam rangkaian pengujian otomatis sistem donasi...",
            "campaign_default.jpg"
        )
        self.assertTrue(create_res["success"], f"Creation failed: {create_res}")
        camp_id = create_res["campaign_id"]

        # Check DB status is 'pending'
        camp_row = db.execute_query("SELECT status FROM campaigns WHERE id = %s", (camp_id,), fetch_one=True)
        self.assertEqual(camp_row["status"], "pending", "Initial status must be pending")

        # Admin approves
        app_res = campaign_service.approve_campaign(self.admin_token, camp_id)
        self.assertTrue(app_res["success"])

        # Check DB status is now 'active'
        camp_row2 = db.execute_query("SELECT status FROM campaigns WHERE id = %s", (camp_id,), fetch_one=True)
        self.assertEqual(camp_row2["status"], "active", "Status should be active after approval")

    def test_tc10_fund_usage_cannot_exceed_collected(self):
        """TC-CAMP-03: Fund usage expense cannot exceed collected balance."""
        detail = campaign_service.get_campaign_detail("bantu-dek-rayyan-berjuang-leukemia")
        camp_id = detail["campaign"]["id"]
        collected = float(detail["campaign"]["collected_amount"])

        # Attempt to record expense much higher than collected balance
        excessive_amount = collected + 500000000.0
        res = campaign_service.add_fund_usage_report(
            self.fundraiser_token,
            camp_id,
            "Pengeluaran Fiktif Melebihi Saldo",
            "Lain-lain",
            excessive_amount,
            "2026-10-19",
            "Harus ditolak oleh sistem karena melebihi batas saldo terkumpul."
        )
        self.assertFalse(res["success"], "Expense exceeding collected funds must be rejected")
        self.assertIn("melebihi", res["message"].lower())

    def test_tc11_anonymous_donor_public_masking(self):
        """TC-CAMP-04: Anonymous donor names are masked as 'Hamba Allah' publicly."""
        detail = campaign_service.get_campaign_detail("bantu-dek-rayyan-berjuang-leukemia")
        recent = detail["campaign"]["recent_donations"]
        
        # Check that any donation with is_anonymous == 1 has name "Hamba Allah"
        anon_found = False
        for d in recent:
            if d["is_anonymous"] == 1:
                anon_found = True
                self.assertEqual(d["donor_name"], "Hamba Allah", "Anonymous donor name must be masked")
        self.assertTrue(anon_found, "Should have tested at least one anonymous donor")


if __name__ == "__main__":
    unittest.main()
