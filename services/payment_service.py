"""
Payment Simulation Service for DonasiKita.
Simulates electronic payment confirmations (Bank Transfer, QRIS, E-Wallet).
Guarantees transaction idempotency, prevents duplicate balance additions,
and issues donation certificates upon successful completion.
"""

import hashlib
import random
from datetime import datetime, date
import db


def simulate_payment(payment_code: str, action: str = "success"):
    """
    Simulates electronic payment execution with strict ACID transaction guarantees.
    
    Protects against race conditions, double-clicks, and concurrent payment processing
    using MySQL/MariaDB row-level locking ('SELECT ... FOR UPDATE'). Ensures that
    concurrent payment confirmations cannot duplicate balance increments or certificates,
    and guarantees automatic transaction rollback on failure.
    
    Args:
        payment_code (str): Unique payment code (e.g. PAY-20261019-XXXXX).
        action (str): 'success' or 'failed'.
        
    Returns:
        dict: Status of payment processing, updated records, and certificate.
    """
    action = action.lower().strip()
    if action not in ("success", "failed"):
        return {"success": False, "message": "Aksi simulasi tidak valid. Harus 'success' atau 'failed'."}

    try:
        with db.get_db_cursor(commit=True) as (cursor, conn):
            # 1. Fetch payment, donation, and campaign details with row-level locking (FOR UPDATE).
            # This serializes concurrent requests for the same payment record at the MySQL/MariaDB engine level,
            # eliminating race conditions between concurrent webhook/user requests.
            sql = """
                SELECT 
                    p.id as payment_id, p.payment_code, p.payment_status, p.payment_method, p.payment_channel,
                    d.id as donation_id, d.donation_code, d.amount, d.is_anonymous, d.donor_name,
                    d.status as donation_status,
                    c.id as campaign_id, c.title as campaign_title, c.collected_amount, c.target_amount
                FROM payments p
                JOIN donations d ON p.donation_id = d.id
                JOIN campaigns c ON d.campaign_id = c.id
                WHERE p.payment_code = %s
                FOR UPDATE
            """
            cursor.execute(sql, (payment_code,))
            record = cursor.fetchone()
            if not record:
                return {"success": False, "message": "Data pembayaran tidak ditemukan."}

            # 2. Strict Idempotency Check under exclusive row lock:
            # If the payment was already successfully processed (e.g. by an earlier concurrent thread),
            # return existing details without modifying campaign balance or creating a duplicate certificate.
            if record["payment_status"] == "success":
                cursor.execute(
                    "SELECT certificate_number FROM certificates WHERE donation_id = %s",
                    (record["donation_id"],)
                )
                cert = cursor.fetchone()
                return {
                    "success": True,
                    "already_processed": True,
                    "status": "success",
                    "message": "Pembayaran ini sudah sukses sebelumnya. Dana telah tercatat.",
                    "donation_code": record["donation_code"],
                    "campaign_id": record["campaign_id"],
                    "certificate_number": cert["certificate_number"] if cert else None
                }

            if record["payment_status"] == "failed":
                return {
                    "success": False,
                    "already_processed": True,
                    "status": "failed",
                    "message": "Pembayaran ini telah dinyatakan gagal sebelumnya dan tidak dapat diproses ulang.",
                    "donation_code": record["donation_code"],
                    "campaign_id": record["campaign_id"]
                }

            # 3. Atomic processing for pending payment
            now_dt = datetime.now()

            if action == "success":
                # Defense-in-depth: conditional update ensures state is still pending
                cursor.execute(
                    "UPDATE payments SET payment_status = 'success', paid_at = %s WHERE id = %s AND payment_status = 'pending'",
                    (now_dt, record["payment_id"])
                )
                if cursor.rowcount == 0:
                    # Concurrency guard: status was updated concurrently
                    cursor.execute("SELECT certificate_number FROM certificates WHERE donation_id = %s", (record["donation_id"],))
                    cert = cursor.fetchone()
                    return {
                        "success": True,
                        "already_processed": True,
                        "status": "success",
                        "message": "Pembayaran ini sudah sukses sebelumnya. Dana telah tercatat.",
                        "donation_code": record["donation_code"],
                        "campaign_id": record["campaign_id"],
                        "certificate_number": cert["certificate_number"] if cert else None
                    }

                # Update Donation status to success
                cursor.execute(
                    "UPDATE donations SET status = 'success', updated_at = %s WHERE id = %s",
                    (now_dt, record["donation_id"])
                )

                # Update Campaign Collected Balance atomically
                donation_amount = float(record["amount"])
                cursor.execute(
                    "UPDATE campaigns SET collected_amount = collected_amount + %s, updated_at = %s WHERE id = %s",
                    (donation_amount, now_dt, record["campaign_id"])
                )

                # Generate & Issue Official Digital Donation Certificate
                cert_month = now_dt.strftime("%Y%m")
                cert_rand = f"{random.randint(1000, 9999)}"
                cert_no = f"DK-CERT/{cert_month}/{record['donation_id']}{cert_rand}"
                
                display_name = "Hamba Allah" if record["is_anonymous"] else record["donor_name"]
                raw_hash = f"{cert_no}-{record['donation_code']}-{donation_amount}-{now_dt}"
                verif_code = hashlib.sha256(raw_hash.encode()).hexdigest()[:24].upper()

                cursor.execute(
                    """
                    INSERT INTO certificates (
                        certificate_number, donation_id, donor_name_display,
                        campaign_title, amount, issue_date, verification_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cert_no,
                        record["donation_id"],
                        display_name,
                        record["campaign_title"],
                        donation_amount,
                        now_dt.date(),
                        verif_code
                    )
                )

                return {
                    "success": True,
                    "status": "success",
                    "message": "Simulasi pembayaran BERHASIL. Terima kasih atas kedermawanan Anda!",
                    "donation_code": record["donation_code"],
                    "amount": float(record["amount"]),
                    "campaign_id": record["campaign_id"],
                    "campaign_title": record["campaign_title"],
                    "certificate_number": cert_no
                }

            else:
                # Action is failed: update status without modifying campaign collected balance
                cursor.execute(
                    "UPDATE payments SET payment_status = 'failed', updated_at = %s WHERE id = %s AND payment_status = 'pending'",
                    (now_dt, record["payment_id"])
                )
                cursor.execute(
                    "UPDATE donations SET status = 'failed', updated_at = %s WHERE id = %s",
                    (now_dt, record["donation_id"])
                )

                return {
                    "success": True,
                    "status": "failed",
                    "message": "Simulasi pembayaran GAGAL. Transaksi dibatalkan dan tidak ada dana yang ditambahkan.",
                    "donation_code": record["donation_code"],
                    "amount": float(record["amount"]),
                    "campaign_id": record["campaign_id"],
                    "campaign_title": record["campaign_title"]
                }
    except Exception as e:
        # Note: db.get_db_cursor automatically executes conn.rollback() on exception
        return {
            "success": False,
            "message": f"Terjadi kesalahan saat memproses transaksi pembayaran: {str(e)}"
        }
