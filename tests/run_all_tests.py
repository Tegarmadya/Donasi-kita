"""
Master Test Runner for DonasiKita.
Runs all unit and integration test suites, aggregating results.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tests.test_auth import TestAuthService
from tests.test_campaign import TestCampaignService
from tests.test_donation_payment import TestDonationPaymentService
from tests.test_reports import TestReportsService
from tests.test_config import TestConfigSecurity


def run_suites():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestAuthService))
    suite.addTests(loader.loadTestsFromTestCase(TestCampaignService))
    suite.addTests(loader.loadTestsFromTestCase(TestDonationPaymentService))
    suite.addTests(loader.loadTestsFromTestCase(TestReportsService))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigSecurity))

    print("=" * 70)
    print(" MENJALANKAN SELURUH PENGUJIAN OTOMATIS APLIKASI DONASIKITA")
    print("=" * 70)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f" TOTAL TEST CASES   : {result.testsRun}")
    print(f" BERHASIL (PASS)    : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f" GAGAL (FAILURES)   : {len(result.failures)}")
    print(f" KESALAHAN (ERRORS) : {len(result.errors)}")
    print("=" * 70)

    if result.wasSuccessful():
        print(">> STATUS: SELURUH PENGUJIAN SISTEM LULUS 100%! <<\n")
        return 0
    else:
        print(">> STATUS: TERDAPAT PENGUJIAN YANG GAGAL. <<\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_suites())
