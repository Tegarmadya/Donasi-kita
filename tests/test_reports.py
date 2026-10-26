"""
Unit and Integration Tests for Platform Reports, Analytics, and CSV Export.
Verifies data aggregation consistency and Excel export compatibility.
"""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import auth_service, report_service, campaign_service
import db


class TestReportsService(unittest.TestCase):

    def setUp(self):
        res_a = auth_service.login("admin@donasikita.id", "password123")
        self.admin_token = res_a["session_token"]

    def test_tc17_admin_summary_matches_db(self):
        """TC-REP-01: Admin dashboard metrics strictly match raw database queries."""
        summary_res = report_service.get_admin_dashboard_summary(self.admin_token)
        self.assertTrue(summary_res["success"])
        s = summary_res["summary"]

        # Raw DB sum of success donations
        raw_sum = db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) as total FROM donations WHERE status = 'success'",
            fetch_one=True
        )["total"]
        self.assertEqual(s["total_donation_volume"], float(raw_sum))

        # Raw DB active campaigns count
        raw_camps = db.execute_query(
            "SELECT COUNT(*) as cnt FROM campaigns WHERE status = 'active'",
            fetch_one=True
        )["cnt"]
        self.assertEqual(s["active_campaigns"], int(raw_camps))

    def test_tc18_top_donors_only_count_success(self):
        """TC-REP-02: Top donors query strictly excludes pending and failed donations."""
        detail = campaign_service.get_campaign_detail("bantu-dek-rayyan-berjuang-leukemia")
        top_donors = detail["campaign"]["top_donors"]

        for td in top_donors:
            # Query status of donations by this amount and campaign
            match = db.execute_query(
                "SELECT status FROM donations WHERE campaign_id = %s AND amount = %s LIMIT 1",
                (detail["campaign"]["id"], td["amount"]),
                fetch_one=True
            )
            if match:
                self.assertEqual(match["status"], "success", "Top donor must have successful donation status")

    def test_tc19_csv_export_format_and_bom(self):
        """TC-REP-03: CSV export creates file with UTF-8 BOM encoding for Excel."""
        res = report_service.export_donations_csv(self.admin_token)
        self.assertTrue(res["success"])
        self.assertTrue(Path(res["file_path"]).exists(), "Exported CSV file must physically exist")

        with open(res["file_path"], "rb") as f:
            header_bytes = f.read(3)
            # UTF-8 BOM signature is EF BB BF
            self.assertEqual(header_bytes, b'\xef\xbb\xbf', "CSV must begin with UTF-8 BOM for Excel compatibility")


if __name__ == "__main__":
    unittest.main()
