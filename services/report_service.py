"""
Reporting and Analytics Service for DonasiKita.
Aggregates performance metrics, generates role-specific dashboard summaries,
and exports donation transaction reports to Excel-friendly CSV.
"""

import csv
import io
from datetime import datetime, date
from pathlib import Path
import config
import db
from services import auth_service


def get_admin_dashboard_summary(session_token: str):
    """
    Returns comprehensive platform analytics for the Admin Dashboard.
    All figures are computed directly from active MySQL tables.
    """
    auth_service.require_auth(session_token, allowed_roles=["admin"])

    # 1. User breakdown
    sql_users = """
        SELECT 
            COUNT(*) as total_users,
            SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_count,
            SUM(CASE WHEN role = 'fundraiser' THEN 1 ELSE 0 END) as fundraiser_count,
            SUM(CASE WHEN role = 'donatur' THEN 1 ELSE 0 END) as donatur_count
        FROM users
    """
    users_stat = db.execute_query(sql_users, fetch_one=True)

    # 2. Campaign breakdown
    sql_camps = """
        SELECT 
            COUNT(*) as total_campaigns,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
        FROM campaigns
    """
    camps_stat = db.execute_query(sql_camps, fetch_one=True)

    # 3. Donation and Financial breakdown
    sql_donations = """
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'success' THEN amount ELSE 0 END), 0) as total_success_amount,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
            COUNT(*) as total_transactions
        FROM donations
    """
    don_stat = db.execute_query(sql_donations, fetch_one=True)

    # 4. Total Fund Usage (Disbursed)
    sql_used = "SELECT COALESCE(SUM(amount), 0) as total_used FROM fund_usage_reports"
    total_disbursed = float(db.execute_query(sql_used, fetch_one=True)["total_used"])

    # 5. Pending Campaigns requiring urgent admin review
    sql_pending_camps = """
        SELECT c.id, c.title, c.target_amount, c.deadline_date, c.created_at, u.full_name as organizer_name
        FROM campaigns c
        JOIN users u ON c.user_id = u.id
        WHERE c.status = 'pending'
        ORDER BY c.id ASC
    """
    pending_list = db.execute_query(sql_pending_camps, fetch_all=True)
    for pc in pending_list:
        pc["target_amount"] = float(pc["target_amount"])
        if pc.get("created_at"):
            pc["created_at"] = str(pc["created_at"])
        if pc.get("deadline_date"):
            pc["deadline_date"] = str(pc["deadline_date"])

    # 6. Recent 10 Transactions
    sql_recent_tx = """
        SELECT 
            d.id, d.donation_code, d.donor_name, d.amount, d.is_anonymous,
            d.status, d.created_at,
            c.title as campaign_title, p.payment_method, p.payment_channel
        FROM donations d
        JOIN campaigns c ON d.campaign_id = c.id
        LEFT JOIN payments p ON d.id = p.donation_id
        ORDER BY d.id DESC
        LIMIT 10
    """
    recent_tx = db.execute_query(sql_recent_tx, fetch_all=True)
    for tx in recent_tx:
        tx["amount"] = float(tx["amount"])
        if tx.get("created_at"):
            tx["created_at"] = str(tx["created_at"])

    # 7. Category distribution (total collected funds)
    sql_cat_dist = """
        SELECT cat.name as category_name, COALESCE(SUM(camp.collected_amount), 0) as total_collected
        FROM categories cat
        LEFT JOIN campaigns camp ON cat.id = camp.category_id
        GROUP BY cat.id
        ORDER BY total_collected DESC
    """
    cat_dist = db.execute_query(sql_cat_dist, fetch_all=True)
    for cd in cat_dist:
        cd["total_collected"] = float(cd["total_collected"])

    return {
        "success": True,
        "summary": {
            "total_users": int(users_stat["total_users"] or 0),
            "admin_count": int(users_stat["admin_count"] or 0),
            "fundraiser_count": int(users_stat["fundraiser_count"] or 0),
            "donatur_count": int(users_stat["donatur_count"] or 0),
            "total_campaigns": int(camps_stat["total_campaigns"] or 0),
            "pending_campaigns": int(camps_stat["pending_count"] or 0),
            "active_campaigns": int(camps_stat["active_count"] or 0),
            "completed_campaigns": int(camps_stat["completed_count"] or 0),
            "total_donation_volume": float(don_stat["total_success_amount"] or 0.0),
            "total_success_count": int(don_stat["success_count"] or 0),
            "total_pending_count": int(don_stat["pending_count"] or 0),
            "total_failed_count": int(don_stat["failed_count"] or 0),
            "total_transactions": int(don_stat["total_transactions"] or 0),
            "total_disbursed": total_disbursed
        },
        "pending_campaigns_list": pending_list,
        "recent_transactions": recent_tx,
        "category_distribution": cat_dist
    }


def get_fundraiser_dashboard_summary(session_token: str):
    """
    Returns aggregated metrics and campaign list for the authenticated fundraiser.
    """
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    user_id = user["user_id"]

    # 1. Campaigns summary
    sql_stats = """
        SELECT 
            COUNT(*) as total_campaigns,
            COALESCE(SUM(collected_amount), 0) as total_collected,
            COALESCE(SUM(target_amount), 0) as total_target
        FROM campaigns
        WHERE user_id = %s
    """
    camp_stats = db.execute_query(sql_stats, (user_id,), fetch_one=True)

    # 2. Total successful donors across fundraiser's campaigns
    sql_donors = """
        SELECT COUNT(DISTINCT d.id) as total_donations_received
        FROM donations d
        JOIN campaigns c ON d.campaign_id = c.id
        WHERE c.user_id = %s AND d.status = 'success'
    """
    donor_count = db.execute_query(sql_donors, (user_id,), fetch_one=True)["total_donations_received"]

    # 3. Total reported fund usage
    sql_spent = """
        SELECT COALESCE(SUM(fu.amount), 0) as total_disbursed
        FROM fund_usage_reports fu
        JOIN campaigns c ON fu.campaign_id = c.id
        WHERE c.user_id = %s
    """
    disbursed = float(db.execute_query(sql_spent, (user_id,), fetch_one=True)["total_disbursed"])

    total_coll = float(camp_stats["total_collected"])
    
    return {
        "success": True,
        "summary": {
            "total_campaigns": int(camp_stats["total_campaigns"] or 0),
            "total_collected": total_coll,
            "total_target": float(camp_stats["total_target"] or 0.0),
            "total_donations_received": int(donor_count or 0),
            "total_disbursed": disbursed,
            "remaining_balance": max(0.0, total_coll - disbursed)
        }
    }


def export_donations_csv(session_token: str, campaign_id: int = None):
    """
    Generates a structured CSV report of donations with UTF-8 BOM encoding
    for direct opening in Microsoft Excel without character corruption.
    """
    auth_service.require_auth(session_token, allowed_roles=["admin", "fundraiser"])

    conditions = ["1=1"]
    params = []

    if campaign_id:
        conditions.append("d.campaign_id = %s")
        params.append(campaign_id)

    where_str = " AND ".join(conditions)
    sql = f"""
        SELECT 
            d.donation_code,
            d.created_at as donation_date,
            d.donor_name,
            d.donor_email,
            d.is_anonymous,
            d.amount,
            d.status as donation_status,
            d.prayer_message,
            c.title as campaign_title,
            cat.name as category_name,
            p.payment_code,
            p.payment_method,
            p.payment_channel,
            p.paid_at,
            cert.certificate_number
        FROM donations d
        JOIN campaigns c ON d.campaign_id = c.id
        JOIN categories cat ON c.category_id = cat.id
        LEFT JOIN payments p ON d.id = p.donation_id
        LEFT JOIN certificates cert ON d.id = cert.donation_id
        WHERE {where_str}
        ORDER BY d.id DESC
    """
    records = db.execute_query(sql, params, fetch_all=True)

    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens it with correct encoding
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # Header
    writer.writerow([
        "No",
        "Kode Donasi",
        "Waktu Transaksi",
        "Nama Donatur",
        "Status Anonim",
        "Email Donatur",
        "Judul Campaign",
        "Kategori",
        "Metode Pembayaran",
        "Saluran Pembayaran",
        "Nominal (Rp)",
        "Status Transaksi",
        "Waktu Lunas",
        "Nomor Sertifikat",
        "Doa / Pesan"
    ])

    for idx, r in enumerate(records, start=1):
        writer.writerow([
            idx,
            r["donation_code"],
            str(r["donation_date"]),
            r["donor_name"],
            "Ya (Hamba Allah)" if r["is_anonymous"] else "Tidak",
            r["donor_email"],
            r["campaign_title"],
            r["category_name"],
            r["payment_method"] or "-",
            r["payment_channel"] or "-",
            f"{float(r['amount']):.2f}",
            r["donation_status"].upper(),
            str(r["paid_at"]) if r["paid_at"] else "-",
            r["certificate_number"] or "-",
            r["prayer_message"] or "-"
        ])

    csv_content = output.getvalue()
    output.close()

    # Clean up older export dumps in deliverables to prevent clutter accumulation
    try:
        for old_csv in config.DELIVERABLES_DIR.glob("Laporan_Donasi_*.csv"):
            old_csv.unlink(missing_ok=True)
    except Exception:
        pass

    # Save a physical copy in deliverables folder as well
    file_name = f"Laporan_Donasi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_path = config.DELIVERABLES_DIR / file_name
    with open(file_path, "w", encoding="utf-8-sig") as f:
        f.write(csv_content)

    return {
        "success": True,
        "file_name": file_name,
        "file_path": str(file_path),
        "total_records": len(records),
        "csv_content": csv_content
    }
