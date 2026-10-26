"""
Unit and Integration Tests for Electronic Donations and Payment Simulation.
Tests transaction creation, payment idempotency, balance increment integrity,
and certificate generation conditions.
"""

import sys
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import auth_service, campaign_service, donation_service, payment_service, certificate_service
import db


class TestDonationPaymentService(unittest.TestCase):

    def setUp(self):
        # Donor session
        res_d = auth_service.login("budi@donasikita.id", "password123")
        self.donor_token = res_d["session_token"]

        # Active campaign ID
        detail = campaign_service.get_campaign_detail("bantu-dek-rayyan-berjuang-leukemia")
        self.active_camp_id = detail["campaign"]["id"]

        # Rejected/Non-active campaign ID
        rej_camp = db.execute_query("SELECT id FROM campaigns WHERE status = 'rejected' LIMIT 1", fetch_one=True)
        self.rejected_camp_id = rej_camp["id"] if rej_camp else None

    def test_tc12_donation_minimum_validation(self):
        """TC-DON-01: Donation below Rp10.000 must be rejected."""
        res = donation_service.create_donation(
            self.donor_token, self.active_camp_id, 5000.0, False, "Uji donasi kecil"
        )
        self.assertFalse(res["success"], "Donation below 10.000 should be rejected")
        self.assertIn("minimal", res["message"].lower())

    def test_tc13_donation_on_inactive_campaign_rejected(self):
        """TC-DON-02: Donation on non-active campaign must be rejected."""
        if not self.rejected_camp_id:
            self.skipTest("No rejected campaign found")
        
        res = donation_service.create_donation(
            self.donor_token, self.rejected_camp_id, 50000.0, False, "Uji campaign non-aktif"
        )
        self.assertFalse(res["success"], "Donation on non-active campaign must be rejected")
        self.assertIn("tidak dapat menerima donasi", res["message"])

    def test_tc14_successful_payment_workflow(self):
        """TC-PAY-01: Payment success atomically updates balance and issues certificate."""
        # 1. Check initial campaign collected balance
        camp_before = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        initial_balance = float(camp_before["collected_amount"])

        # 2. Create pending donation
        nominal = 200000.0
        don_res = donation_service.create_donation(
            self.donor_token, self.active_camp_id, nominal, False, "Doa sukses pengujian",
            "bank_transfer", "BCA Virtual Account"
        )
        self.assertTrue(don_res["success"])
        pay_code = don_res["payment_code"]
        don_code = don_res["donation_code"]

        # 3. Simulate Payment Success
        pay_res = payment_service.simulate_payment(pay_code, "success")
        self.assertTrue(pay_res["success"])
        self.assertEqual(pay_res["status"], "success")
        cert_no = pay_res["certificate_number"]
        self.assertIsNotNone(cert_no)

        # 4. Check balance increased by exact nominal
        camp_after = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        new_balance = float(camp_after["collected_amount"])
        self.assertEqual(new_balance, initial_balance + nominal, "Campaign collected amount must increase by exact donation amount")

        # 5. Check certificate is valid and accessible
        cert_res = certificate_service.get_certificate_detail(cert_no)
        self.assertTrue(cert_res["success"], "Issued certificate must be retrievable")
        self.assertEqual(cert_res["certificate"]["amount"], nominal)

    def test_tc15_failed_payment_workflow(self):
        """TC-PAY-02: Payment failure does NOT increment campaign balance and does NOT issue certificate."""
        camp_before = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        initial_balance = float(camp_before["collected_amount"])

        nominal = 75000.0
        don_res = donation_service.create_donation(
            self.donor_token, self.active_camp_id, nominal, False, "Doa uji gagal",
            "ewallet", "GoPay"
        )
        self.assertTrue(don_res["success"])
        pay_code = don_res["payment_code"]
        don_code = don_res["donation_code"]

        # Simulate Failed
        pay_res = payment_service.simulate_payment(pay_code, "failed")
        self.assertTrue(pay_res["success"])
        self.assertEqual(pay_res["status"], "failed")

        # Balance must remain unchanged!
        camp_after = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        self.assertEqual(float(camp_after["collected_amount"]), initial_balance, "Balance must not increase on failed payment")

        # Certificate must NOT exist
        cert_res = certificate_service.get_certificate_by_donation_code(don_code)
        self.assertFalse(cert_res["success"], "Failed donation must not have a certificate")

    def test_tc16_idempotency_double_click_prevention(self):
        """TC-PAY-03: Double-clicking confirmation does NOT duplicate balance addition."""
        don_res = donation_service.create_donation(
            self.donor_token, self.active_camp_id, 100000.0, False, "Uji idempotensi ganda"
        )
        pay_code = don_res["payment_code"]

        # First click
        pay1 = payment_service.simulate_payment(pay_code, "success")
        self.assertTrue(pay1["success"])

        camp_mid = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        balance_after_first = float(camp_mid["collected_amount"])

        # Second click (duplicate)
        pay2 = payment_service.simulate_payment(pay_code, "success")
        self.assertTrue(pay2.get("already_processed"), "Second click must be recognized as already processed")

        # Balance must NOT increase again!
        camp_final = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        self.assertEqual(float(camp_final["collected_amount"]), balance_after_first, "Duplicate click must not double count")

    def test_tc20_concurrent_payment_processing(self):
        """TC-PAY-04: Concurrent payment requests cannot duplicate balance or certificate."""
        camp_before = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        initial_balance = float(camp_before["collected_amount"])

        nominal = 125000.0
        don_res = donation_service.create_donation(
            self.donor_token, self.active_camp_id, nominal, False, "Uji pembayaran konkuren",
            "bank_transfer", "BCA Virtual Account"
        )
        self.assertTrue(don_res["success"])
        pay_code = don_res["payment_code"]
        don_rec = db.execute_query("SELECT id FROM donations WHERE donation_code = %s", (don_res["donation_code"],), fetch_one=True)
        donation_id = don_rec["id"]

        num_threads = 5
        def execute_concurrent_payment():
            return payment_service.simulate_payment(pay_code, "success")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(execute_concurrent_payment) for _ in range(num_threads)]
            results = [f.result() for f in futures]

        # Exactly 1 thread must be the initial processor (already_processed is False/None)
        first_processed = [r for r in results if r.get("success") and not r.get("already_processed")]
        already_processed = [r for r in results if r.get("already_processed")]

        self.assertEqual(len(first_processed), 1, "Exactly one thread should execute initial payment")
        self.assertEqual(len(already_processed), num_threads - 1, f"Remaining {num_threads - 1} threads must receive already_processed")

        # Campaign collected balance must increase by EXACTLY nominal once
        camp_after = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        final_balance = float(camp_after["collected_amount"])
        self.assertEqual(final_balance, initial_balance + nominal, "Campaign balance must only increase by single donation nominal")

        # Exactly 1 certificate must exist in database for this donation
        certs = db.execute_query("SELECT COUNT(*) as count FROM certificates WHERE donation_id = %s", (donation_id,), fetch_one=True)
        self.assertEqual(certs["count"], 1, "Exactly one certificate must be issued for concurrent requests")

    def test_tc21_transaction_rollback_on_failure(self):
        """TC-PAY-05: Database transaction rollback on simulated payment failure."""
        camp_before = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        initial_balance = float(camp_before["collected_amount"])

        nominal = 80000.0
        don_res = donation_service.create_donation(
            self.donor_token, self.active_camp_id, nominal, False, "Uji rollback transaksi",
            "ewallet", "GoPay"
        )
        self.assertTrue(don_res["success"])
        pay_code = don_res["payment_code"]
        don_rec = db.execute_query("SELECT id FROM donations WHERE donation_code = %s", (don_res["donation_code"],), fetch_one=True)
        donation_id = don_rec["id"]

        # Simulate a crash during certificate generation/insertion by patching hashlib.sha256
        with patch("hashlib.sha256", side_effect=RuntimeError("Simulasi kegagalan sertifikat mid-transaksi")):
            pay_res = payment_service.simulate_payment(pay_code, "success")
            self.assertFalse(pay_res["success"])
            self.assertIn("Simulasi kegagalan", pay_res["message"])

        # Transaction rollback must ensure:
        # 1. Campaign balance remains unchanged
        camp_after = db.execute_query("SELECT collected_amount FROM campaigns WHERE id = %s", (self.active_camp_id,), fetch_one=True)
        self.assertEqual(float(camp_after["collected_amount"]), initial_balance, "Balance must not change on rolled back transaction")

        # 2. Payment status is still 'pending'
        pay_check = db.execute_query("SELECT payment_status FROM payments WHERE payment_code = %s", (pay_code,), fetch_one=True)
        self.assertEqual(pay_check["payment_status"], "pending", "Payment status must roll back to pending")

        # 3. Donation status is still 'pending'
        don_check = db.execute_query("SELECT status FROM donations WHERE id = %s", (donation_id,), fetch_one=True)
        self.assertEqual(don_check["status"], "pending", "Donation status must roll back to pending")

        # 4. No certificate was created
        cert_check = db.execute_query("SELECT id FROM certificates WHERE donation_id = %s", (donation_id,), fetch_one=True)
        self.assertIsNone(cert_check, "No certificate should exist after transaction rollback")


if __name__ == "__main__":
    unittest.main()
