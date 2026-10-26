"""
Certificate Service for DonasiKita.
Retrieves and validates digital donation certificates issued to donors.
"""

from datetime import datetime
import db


def get_certificate_detail(certificate_number: str):
    """
    Fetches official certificate data by its unique number.
    Ensures that certificates are only delivered for successful donations.
    """
    certificate_number = (certificate_number or "").strip()
    if not certificate_number:
        return {"success": False, "message": "Nomor sertifikat tidak boleh kosong."}

    sql = """
        SELECT 
            cert.id, cert.certificate_number, cert.donor_name_display,
            cert.campaign_title, cert.amount, cert.issue_date, cert.verification_code,
            cert.created_at,
            d.donation_code, d.is_anonymous, d.prayer_message, d.created_at as donation_date,
            p.payment_method, p.payment_channel, p.paid_at,
            c.slug as campaign_slug
        FROM certificates cert
        JOIN donations d ON cert.donation_id = d.id
        JOIN campaigns c ON d.campaign_id = c.id
        LEFT JOIN payments p ON d.id = p.donation_id
        WHERE cert.certificate_number = %s AND d.status = 'success'
    """
    cert = db.execute_query(sql, (certificate_number,), fetch_one=True)
    if not cert:
        return {"success": False, "message": "Sertifikat tidak ditemukan atau donasi belum sukses."}

    cert["amount"] = float(cert["amount"])
    if cert.get("issue_date"):
        cert["issue_date"] = str(cert["issue_date"])
    if cert.get("created_at"):
        cert["created_at"] = str(cert["created_at"])
    if cert.get("donation_date"):
        cert["donation_date"] = str(cert["donation_date"])
    if cert.get("paid_at"):
        cert["paid_at"] = str(cert["paid_at"])

    return {"success": True, "certificate": cert}


def get_certificate_by_donation_code(donation_code: str):
    """Fetches certificate by donation code."""
    donation_code = (donation_code or "").strip()
    sql = """
        SELECT cert.certificate_number
        FROM certificates cert
        JOIN donations d ON cert.donation_id = d.id
        WHERE d.donation_code = %s AND d.status = 'success'
    """
    row = db.execute_query(sql, (donation_code,), fetch_one=True)
    if not row:
        return {"success": False, "message": "Sertifikat belum tersedia untuk transaksi ini."}
    
    return get_certificate_detail(row["certificate_number"])
