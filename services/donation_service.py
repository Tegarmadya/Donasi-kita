"""
Donation Service for DonasiKita.
Handles donation creation, validation, transaction lifecycle,
and donor history.
"""

import random
from datetime import datetime, date
import db
from services import auth_service


def generate_code(prefix: str) -> str:
    """Generates unique transaction code with date and random digits."""
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = f"{random.randint(10000, 99999)}"
    return f"{prefix}-{date_str}-{rand_str}"


def create_donation(session_token: str, campaign_id: int, amount: float,
                    is_anonymous: bool = False, prayer_message: str = "",
                    payment_method: str = "bank_transfer", payment_channel: str = "BCA Virtual Account"):
    """
    Creates a new pending donation and linked payment record.
    Requires user authentication as specified in business requirements.
    """
    user = auth_service.require_auth(session_token)
    
    # 1. Validate Campaign
    sql_camp = "SELECT id, title, status, deadline_date, collected_amount, target_amount FROM campaigns WHERE id = %s"
    camp = db.execute_query(sql_camp, (campaign_id,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}

    if camp["status"] != "active":
        return {
            "success": False,
            "message": f"Campaign ini sedang berstatus '{camp['status']}' dan tidak dapat menerima donasi."
        }

    # Check deadline
    deadline = camp["deadline_date"]
    if isinstance(deadline, str):
        deadline = datetime.strptime(deadline[:10], "%Y-%m-%d").date()
    if deadline < date.today():
        return {
            "success": False,
            "message": "Campaign ini telah melewati batas waktu tenggat penggalangan dana."
        }

    # 2. Validate Amount
    try:
        nominal = float(amount)
        if nominal < 10000:
            return {"success": False, "message": "Nominal donasi minimal Rp 10.000."}
    except (ValueError, TypeError):
        return {"success": False, "message": "Nominal donasi tidak valid."}

    # 3. Create Codes
    donation_code = generate_code("DON")
    payment_code = generate_code("PAY")

    # Payment method normalization
    valid_methods = {
        "bank_transfer": "Transfer Bank (Virtual Account)",
        "qris": "QRIS (Quick Response Code)",
        "ewallet": "Dompet Digital (E-Wallet)"
    }
    if payment_method not in valid_methods:
        payment_method = "bank_transfer"

    payment_channel = (payment_channel or "BCA Virtual Account").strip()
    instructions = f"Silakan selesaikan simulasi pembayaran melalui {payment_channel} dengan nominal tepat Rp {nominal:,.0f}."

    # 4. Insert into database using transaction
    with db.get_db_cursor(commit=True) as (cursor, conn):
        sql_don = """
            INSERT INTO donations (
                donation_code, campaign_id, user_id, donor_name, donor_email,
                amount, is_anonymous, prayer_message, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
        """
        cursor.execute(sql_don, (
            donation_code,
            campaign_id,
            user["user_id"],
            user["full_name"],
            user["email"],
            nominal,
            1 if is_anonymous else 0,
            (prayer_message or "").strip()
        ))
        donation_id = cursor.lastrowid

        sql_pay = """
            INSERT INTO payments (
                payment_code, donation_id, payment_method, payment_channel,
                payment_status, payment_reference, instructions
            ) VALUES (%s, %s, %s, %s, 'pending', %s, %s)
        """
        ref_no = f"SIM-{donation_code}"
        cursor.execute(sql_pay, (
            payment_code,
            donation_id,
            payment_method,
            payment_channel,
            ref_no,
            instructions
        ))

    return {
        "success": True,
        "message": "Donasi berhasil diinisiasi. Silakan lanjutkan simulasi pembayaran.",
        "donation_code": donation_code,
        "payment_code": payment_code,
        "amount": nominal,
        "campaign_title": camp["title"],
        "payment_method": payment_method,
        "payment_channel": payment_channel
    }


def get_donation_by_code(donation_code: str):
    """Returns comprehensive information regarding a donation and its payment status."""
    sql = """
        SELECT 
            d.id as donation_id, d.donation_code, d.amount, d.is_anonymous, d.prayer_message,
            d.status as donation_status, d.created_at, d.donor_name, d.donor_email,
            p.id as payment_id, p.payment_code, p.payment_method, p.payment_channel,
            p.payment_status, p.payment_reference, p.instructions, p.paid_at,
            c.id as campaign_id, c.title as campaign_title, c.slug as campaign_slug,
            cert.certificate_number
        FROM donations d
        JOIN payments p ON d.id = p.donation_id
        JOIN campaigns c ON d.campaign_id = c.id
        LEFT JOIN certificates cert ON d.id = cert.donation_id
        WHERE d.donation_code = %s
    """
    row = db.execute_query(sql, (donation_code,), fetch_one=True)
    if not row:
        return {"success": False, "message": "Data donasi tidak ditemukan."}

    row["amount"] = float(row["amount"])
    if row.get("created_at"):
        row["created_at"] = str(row["created_at"])
    if row.get("paid_at"):
        row["paid_at"] = str(row["paid_at"])

    return {"success": True, "donation": row}


def get_user_donations(session_token: str):
    """Returns all donations made by the authenticated user."""
    user = auth_service.require_auth(session_token)

    sql = """
        SELECT 
            d.id, d.donation_code, d.amount, d.is_anonymous, d.prayer_message,
            d.status, d.created_at,
            p.payment_method, p.payment_channel,
            c.id as campaign_id, c.title as campaign_title, c.slug as campaign_slug,
            cert.certificate_number
        FROM donations d
        JOIN campaigns c ON d.campaign_id = c.id
        LEFT JOIN payments p ON d.id = p.donation_id
        LEFT JOIN certificates cert ON d.id = cert.donation_id
        WHERE d.user_id = %s
        ORDER BY d.id DESC
    """
    donations = db.execute_query(sql, (user["user_id"],), fetch_all=True)
    for d in donations:
        d["amount"] = float(d["amount"])
        if d.get("created_at"):
            d["created_at"] = str(d["created_at"])

    return {"success": True, "donations": donations}


def get_all_donations_admin(session_token: str, status_filter=None):
    """Admin function: returns all transactions across the platform with search & filters."""
    auth_service.require_auth(session_token, allowed_roles=["admin"])

    conditions = ["1=1"]
    params = []
    if status_filter and status_filter != "all":
        conditions.append("d.status = %s")
        params.append(status_filter)

    where_str = " AND ".join(conditions)
    sql = f"""
        SELECT 
            d.id, d.donation_code, d.donor_name, d.donor_email, d.amount,
            d.is_anonymous, d.status, d.created_at,
            p.payment_method, p.payment_channel, p.payment_code, p.paid_at,
            c.title as campaign_title, cert.certificate_number
        FROM donations d
        JOIN campaigns c ON d.campaign_id = c.id
        LEFT JOIN payments p ON d.id = p.donation_id
        LEFT JOIN certificates cert ON d.id = cert.donation_id
        WHERE {where_str}
        ORDER BY d.id DESC
    """
    donations = db.execute_query(sql, params, fetch_all=True)
    for d in donations:
        d["amount"] = float(d["amount"])
        if d.get("created_at"):
            d["created_at"] = str(d["created_at"])
        if d.get("paid_at"):
            d["paid_at"] = str(d["paid_at"])

    return {"success": True, "donations": donations}
