import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from concurrent.futures import ThreadPoolExecutor
from services import auth_service, campaign_service, donation_service, payment_service, report_service, certificate_service


def main():
    print("--- 0. Testing Configuration & Secret Key Security ---")
    valid, msg = config.validate_config(strict=False)
    assert valid, f"Configuration validation failed: {msg}"
    print(" Active .env configuration is valid and secure.")

    try:
        config.validate_config("donasikita-secret-key-uts-2026-secure", strict=True)
        assert False, "Static secret key should have been rejected!"
    except ValueError:
        print(" Static default secret key properly rejected by validation.")

    print("\n--- 1. Testing Auth Service ---")
    admin_res = auth_service.login("admin@donasikita.id", "password123")
    assert admin_res["success"], f"Admin login failed: {admin_res}"
    admin_token = admin_res["session_token"]
    print(" Admin login OK. Role:", admin_res["user"]["role"])

    donor_res = auth_service.login("budi@donasikita.id", "password123")
    assert donor_res["success"], f"Donor login failed: {donor_res}"
    donor_token = donor_res["session_token"]
    print(" Donor login OK. Name:", donor_res["user"]["full_name"])

    print("\n--- 2. Testing Campaign Service ---")
    lp = campaign_service.get_landing_page_data()
    assert lp["success"], "Landing page fetch failed"
    print(f" Landing page OK. Active campaigns: {lp['metrics']['active_campaigns']}, Total Vol: Rp {lp['metrics']['total_volume']:,.0f}")

    detail = campaign_service.get_campaign_detail("bantu-dek-rayyan-berjuang-leukemia")
    assert detail["success"], "Campaign detail fetch failed"
    camp_id = detail["campaign"]["id"]
    print(f" Campaign detail OK: {detail['campaign']['title']}, Collected: Rp {detail['campaign']['collected_amount']:,.0f}")

    print("\n--- 3. Testing Donation Creation ---")
    don_res = donation_service.create_donation(
        session_token=donor_token,
        campaign_id=camp_id,
        amount=150000.0,
        is_anonymous=False,
        prayer_message="Doa terbaik untuk kesembuhan Rayyan.",
        payment_method="bank_transfer",
        payment_channel="BCA Virtual Account"
    )
    assert don_res["success"], f"Donation creation failed: {don_res}"
    don_code = don_res["donation_code"]
    pay_code = don_res["payment_code"]
    print(f" Donation created OK: {don_code}, Payment Code: {pay_code}")

    print("\n--- 4. Testing Payment Simulation (SUCCESS) ---")
    pay_res = payment_service.simulate_payment(pay_code, action="success")
    assert pay_res["success"] and pay_res["status"] == "success", f"Payment simulation failed: {pay_res}"
    cert_no = pay_res["certificate_number"]
    print(f" Payment success OK. Certificate issued: {cert_no}")

    print("\n--- 5. Testing Payment Idempotency (Double-Click Prevention) ---")
    pay_double = payment_service.simulate_payment(pay_code, action="success")
    assert pay_double.get("already_processed"), "Duplicate processing was not caught!"
    print(f" Idempotency verified OK: {pay_double['message']}")

    print("\n--- 5b. Testing Concurrent Payment Processing (Multi-Threaded) ---")
    don_conc = donation_service.create_donation(
        session_token=donor_token,
        campaign_id=camp_id,
        amount=100000.0,
        is_anonymous=False,
        prayer_message="Uji multi-threaded concurrency",
        payment_method="qris",
        payment_channel="QRIS Dinamis"
    )
    assert don_conc["success"]
    pay_conc_code = don_conc["payment_code"]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futs = [executor.submit(payment_service.simulate_payment, pay_conc_code, "success") for _ in range(4)]
        conc_results = [f.result() for f in futs]
    
    first_ok = [r for r in conc_results if r.get("success") and not r.get("already_processed")]
    already_ok = [r for r in conc_results if r.get("already_processed")]
    assert len(first_ok) == 1, f"Expected 1 primary processor, got {len(first_ok)}"
    assert len(already_ok) == 3, f"Expected 3 already_processed, got {len(already_ok)}"
    print(f" Concurrency verified OK: 1 primary processed, 3 idempotently handled.")

    print("\n--- 6. Testing Digital Certificate Service ---")
    cert_res = certificate_service.get_certificate_detail(cert_no)
    assert cert_res["success"], f"Certificate fetch failed: {cert_res}"
    print(f" Certificate verified OK for: {cert_res['certificate']['donor_name_display']} - Rp {cert_res['certificate']['amount']:,.0f}")

    print("\n--- 7. Testing Fund Usage Limitation (Cannot Exceed Collected) ---")
    fund_res = campaign_service.add_fund_usage_report(
        session_token=admin_token,
        campaign_id=camp_id,
        expense_title="Pengeluaran Tidak Wajar",
        expense_category="Lain-lain",
        amount=999999999.0,  # Exceeds collected balance
        expense_date="2026-10-19",
        description="Harus ditolak karena melebihi dana"
    )
    assert not fund_res["success"], "Fund usage should have been rejected for exceeding collected balance!"
    print(f" Fund usage limit verified OK: {fund_res['message']}")

    print("\n--- 8. Testing Admin Summary & CSV Export ---")
    admin_sum = report_service.get_admin_dashboard_summary(admin_token)
    assert admin_sum["success"], "Admin summary failed"
    print(f" Admin summary OK. Total volume: Rp {admin_sum['summary']['total_donation_volume']:,.0f}")

    csv_res = report_service.export_donations_csv(admin_token)
    assert csv_res["success"], "CSV export failed"
    print(f" CSV export OK. Generated file: {csv_res['file_name']}")

    print("\n==========================================")
    print("ALL CORE BACKEND BUSINESS LOGIC VERIFIED!")
    print("==========================================")


if __name__ == "__main__":
    main()
