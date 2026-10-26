"""
Campaign Service for DonasiKita.
Manages crowdfunding campaigns, categories, updates, fund usage transparency,
and administrative approvals.
"""

import re
from datetime import datetime, date
from decimal import Decimal
import db
from services import auth_service


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from text."""
    text = (text or "").lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text or "campaign"


def format_campaign_record(camp: dict) -> dict:
    """Formats numeric, date, and progress fields of a campaign record."""
    if not camp:
        return None
    
    target = float(camp.get("target_amount") or 0.0)
    collected = float(camp.get("collected_amount") or 0.0)
    
    progress_raw = (collected / target * 100.0) if target > 0 else 0.0
    progress_bar = min(100.0, round(progress_raw, 1))
    
    deadline = camp.get("deadline_date")
    days_left = 0
    is_today_deadline = False
    is_expired = False
    if deadline:
        if isinstance(deadline, str):
            deadline = datetime.strptime(deadline[:10], "%Y-%m-%d").date()
        camp["deadline_date"] = str(deadline)
        today = date.today()
        days_diff = (deadline - today).days
        days_left = max(0, days_diff)
        is_today_deadline = (deadline == today)
        is_expired = (deadline < today and camp.get("status") == "active")
    
    camp["target_amount"] = target
    camp["collected_amount"] = collected
    camp["progress_raw"] = round(progress_raw, 1)
    camp["progress_percentage"] = progress_bar
    camp["days_left"] = days_left
    camp["is_today_deadline"] = is_today_deadline
    camp["is_expired"] = is_expired
    if is_expired:
        camp["days_left_text"] = "Telah Berakhir"
    elif is_today_deadline:
        camp["days_left_text"] = "Hari Terakhir"
    else:
        camp["days_left_text"] = f"{days_left} hari lagi"
    
    if camp.get("created_at"):
        camp["created_at"] = str(camp["created_at"])
    if camp.get("updated_at"):
        camp["updated_at"] = str(camp["updated_at"])
        
    return camp


# -----------------------------------------------------------------------------
# Public & Catalog Functions
# -----------------------------------------------------------------------------

def get_categories():
    """Returns list of active campaign categories with active campaign count."""
    sql = """
        SELECT c.id, c.name, c.slug, c.description, c.icon,
               COUNT(camp.id) as campaign_count
        FROM categories c
        LEFT JOIN campaigns camp ON c.id = camp.category_id AND camp.status = 'active'
        WHERE c.is_active = 1
        GROUP BY c.id
        ORDER BY c.id ASC
    """
    categories = db.execute_query(sql, fetch_all=True)
    return {"success": True, "categories": categories}


def get_landing_page_data():
    """
    Returns aggregated metrics, featured campaigns, recent campaigns,
    and categories for the public homepage.
    """
    # 1. Platform aggregate metrics
    sql_metrics = """
        SELECT 
            COALESCE(SUM(amount), 0) as total_donation_volume,
            COUNT(DISTINCT id) as total_success_donations,
            COUNT(DISTINCT donor_email) as total_unique_donors
        FROM donations
        WHERE status = 'success'
    """
    metrics = db.execute_query(sql_metrics, fetch_one=True)
    
    active_camps_count = db.execute_query(
        "SELECT COUNT(*) as cnt FROM campaigns WHERE status = 'active'",
        fetch_one=True
    )["cnt"]

    # 2. Featured Campaigns (highest collected percentage among active)
    sql_featured = """
        SELECT c.*, cat.name as category_name, cat.slug as category_slug, u.full_name as organizer_name
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.user_id = u.id
        WHERE c.status = 'active'
        ORDER BY (c.collected_amount / c.target_amount) DESC, c.id DESC
        LIMIT 3
    """
    featured = [format_campaign_record(c) for c in db.execute_query(sql_featured, fetch_all=True)]

    # 3. Urgent Campaigns (closest deadline among active)
    sql_urgent = """
        SELECT c.*, cat.name as category_name, cat.slug as category_slug, u.full_name as organizer_name
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.user_id = u.id
        WHERE c.status = 'active' AND c.deadline_date >= CURRENT_DATE()
        ORDER BY c.deadline_date ASC
        LIMIT 3
    """
    urgent = [format_campaign_record(c) for c in db.execute_query(sql_urgent, fetch_all=True)]

    # 4. Recent Campaigns
    sql_recent = """
        SELECT c.*, cat.name as category_name, cat.slug as category_slug, u.full_name as organizer_name
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.user_id = u.id
        WHERE c.status = 'active'
        ORDER BY c.id DESC
        LIMIT 6
    """
    recent = [format_campaign_record(c) for c in db.execute_query(sql_recent, fetch_all=True)]

    # 5. Categories
    cats = get_categories()["categories"]

    return {
        "success": True,
        "metrics": {
            "total_volume": float(metrics["total_donation_volume"]),
            "total_donations": int(metrics["total_success_donations"]),
            "total_donors": int(metrics["total_unique_donors"]),
            "active_campaigns": int(active_camps_count)
        },
        "featured_campaigns": featured,
        "urgent_campaigns": urgent,
        "recent_campaigns": recent,
        "categories": cats
    }


def get_campaigns(category_slug=None, search_keyword=None, status="active", sort_by="newest"):
    """
    Returns list of campaigns with flexible filtering and sorting.
    """
    conditions = ["1=1"]
    params = []

    if status and status != "all":
        conditions.append("c.status = %s")
        params.append(status)

    if category_slug and category_slug != "all":
        conditions.append("cat.slug = %s")
        params.append(category_slug)

    if search_keyword and search_keyword.strip():
        kw = f"%{search_keyword.strip()}%"
        conditions.append("(c.title LIKE %s OR c.short_description LIKE %s)")
        params.extend([kw, kw])

    order_clause = "c.id DESC"
    if sort_by == "urgent":
        order_clause = "c.deadline_date ASC"
    elif sort_by == "popular":
        order_clause = "(c.collected_amount / c.target_amount) DESC"
    elif sort_by == "oldest":
        order_clause = "c.id ASC"

    where_str = " AND ".join(conditions)
    sql = f"""
        SELECT c.*, cat.name as category_name, cat.slug as category_slug, u.full_name as organizer_name
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.user_id = u.id
        WHERE {where_str}
        ORDER BY {order_clause}
    """
    campaigns = [format_campaign_record(c) for c in db.execute_query(sql, params, fetch_all=True)]
    return {"success": True, "campaigns": campaigns, "total": len(campaigns)}


def get_campaign_detail(identifier):
    """
    Returns complete campaign details, donor history, top donors,
    updates, and fund usage reports.
    identifier can be slug (str) or campaign id (int).
    """
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        where_clause = "c.id = %s"
        param = int(identifier)
    else:
        where_clause = "c.slug = %s"
        param = str(identifier)

    sql = f"""
        SELECT c.*, cat.name as category_name, cat.slug as category_slug,
               u.full_name as organizer_name, u.avatar as organizer_avatar, u.role as organizer_role
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.user_id = u.id
        WHERE {where_clause}
    """
    camp = db.execute_query(sql, (param,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}

    camp = format_campaign_record(camp)
    campaign_id = camp["id"]

    # 1. Donor count (success only)
    sql_cnt = "SELECT COUNT(*) as cnt FROM donations WHERE campaign_id = %s AND status = 'success'"
    camp["donor_count"] = db.execute_query(sql_cnt, (campaign_id,), fetch_one=True)["cnt"]

    # 2. Public recent donations (success only, masks identity if is_anonymous = 1)
    sql_donors = """
        SELECT id, donation_code, donor_name, amount, is_anonymous, prayer_message, created_at
        FROM donations
        WHERE campaign_id = %s AND status = 'success'
        ORDER BY id DESC
        LIMIT 20
    """
    recent_donors = db.execute_query(sql_donors, (campaign_id,), fetch_all=True)
    for d in recent_donors:
        d["amount"] = float(d["amount"])
        if d["is_anonymous"]:
            d["donor_name"] = "Hamba Allah"
        if d.get("created_at"):
            d["created_at"] = str(d["created_at"])
    camp["recent_donations"] = recent_donors

    # 3. Top Donors (success only, ordered by highest amount, respecting anonymous flag)
    sql_top = """
        SELECT donor_name, is_anonymous, amount, created_at
        FROM donations
        WHERE campaign_id = %s AND status = 'success'
        ORDER BY amount DESC, id ASC
        LIMIT 5
    """
    top_donors = db.execute_query(sql_top, (campaign_id,), fetch_all=True)
    for td in top_donors:
        td["amount"] = float(td["amount"])
        if td["is_anonymous"]:
            td["donor_name"] = "Hamba Allah"
        if td.get("created_at"):
            td["created_at"] = str(td["created_at"])
    camp["top_donors"] = top_donors

    # 4. Campaign Updates
    sql_upd = """
        SELECT id, title, content, image_url, created_at
        FROM campaign_updates
        WHERE campaign_id = %s
        ORDER BY id DESC
    """
    updates = db.execute_query(sql_upd, (campaign_id,), fetch_all=True)
    for u in updates:
        if u.get("created_at"):
            u["created_at"] = str(u["created_at"])
    camp["updates"] = updates

    # 5. Fund Usage Reports (Transparansi Pengeluaran Dana)
    sql_fu = """
        SELECT id, expense_title, expense_category, amount, expense_date, description, proof_document, created_at
        FROM fund_usage_reports
        WHERE campaign_id = %s
        ORDER BY expense_date DESC, id DESC
    """
    fund_usages = db.execute_query(sql_fu, (campaign_id,), fetch_all=True)
    total_spent = 0.0
    for fu in fund_usages:
        fu["amount"] = float(fu["amount"])
        total_spent += fu["amount"]
        if fu.get("expense_date"):
            fu["expense_date"] = str(fu["expense_date"])
        if fu.get("created_at"):
            fu["created_at"] = str(fu["created_at"])
            
    camp["fund_usages"] = fund_usages
    camp["total_spent"] = total_spent
    camp["remaining_fund"] = max(0.0, camp["collected_amount"] - total_spent)

    return {"success": True, "campaign": camp}


# -----------------------------------------------------------------------------
# Fundraiser Management Functions
# -----------------------------------------------------------------------------

def create_campaign(session_token: str, title: str, category_id: int, target_amount: float,
                    deadline_date: str, short_description: str, story: str, image_url: str):
    """
    Creates a new campaign. Accessible by fundraiser or admin.
    Initial status is set to 'pending' awaiting admin curation.
    """
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    
    title = (title or "").strip()
    short_description = (short_description or "").strip()
    story = (story or "").strip()
    image_url = (image_url or "campaign_default.jpg").strip()
    
    if not title or len(title) < 10:
        return {"success": False, "message": "Judul campaign minimal 10 karakter."}
    if not short_description or len(short_description) < 20:
        return {"success": False, "message": "Deskripsi singkat minimal 20 karakter."}
    if not story or len(story) < 50:
        return {"success": False, "message": "Cerita lengkap penggalangan dana minimal 50 karakter."}
    
    try:
        target_val = float(target_amount)
        if target_val < 100000:
            return {"success": False, "message": "Target donasi minimal Rp 100.000."}
    except (ValueError, TypeError):
        return {"success": False, "message": "Target donasi tidak valid."}

    try:
        deadline_obj = datetime.strptime(deadline_date[:10], "%Y-%m-%d").date()
        if deadline_obj <= date.today():
            return {"success": False, "message": "Tenggat waktu harus lebih dari hari ini."}
    except Exception:
        return {"success": False, "message": "Format tanggal tenggat waktu tidak valid (YYYY-MM-DD)."}

    # Verify category
    cat = db.execute_query("SELECT id FROM categories WHERE id = %s", (category_id,), fetch_one=True)
    if not cat:
        return {"success": False, "message": "Kategori yang dipilih tidak valid."}

    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while db.execute_query("SELECT id FROM campaigns WHERE slug = %s", (slug,), fetch_one=True):
        slug = f"{base_slug}-{counter}"
        counter += 1

    sql = """
        INSERT INTO campaigns (
            user_id, category_id, title, slug, short_description, story,
            target_amount, collected_amount, deadline_date, image_url, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0.00, %s, %s, 'pending')
    """
    res = db.execute_query(sql, (
        user["user_id"],
        category_id,
        title,
        slug,
        short_description,
        story,
        target_val,
        str(deadline_obj),
        image_url
    ), commit=True)

    return {
        "success": True,
        "message": "Campaign berhasil dibuat dan sedang menunggu persetujuan admin.",
        "campaign_id": res["last_insert_id"],
        "slug": slug
    }


def get_fundraiser_campaigns(session_token: str):
    """Returns all campaigns created by the authenticated fundraiser."""
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    
    sql = """
        SELECT c.*, cat.name as category_name
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        WHERE c.user_id = %s
        ORDER BY c.id DESC
    """
    campaigns = [format_campaign_record(c) for c in db.execute_query(sql, (user["user_id"],), fetch_all=True)]
    return {"success": True, "campaigns": campaigns}


def update_campaign(session_token: str, campaign_id: int, title: str, category_id: int,
                    target_amount: float, deadline_date: str, short_description: str,
                    story: str, image_url: str):
    """
    Updates campaign details. Only owner or admin can edit.
    Enforces business rule: target amount cannot be lower than already collected amount.
    """
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    
    camp = db.execute_query("SELECT * FROM campaigns WHERE id = %s", (campaign_id,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}

    if user["role"] != "admin" and camp["user_id"] != user["user_id"]:
        return {"success": False, "message": "Anda tidak memiliki hak untuk mengubah campaign ini."}

    try:
        target_val = float(target_amount)
        collected_val = float(camp["collected_amount"])
        if target_val < collected_val:
            return {
                "success": False,
                "message": f"Target donasi tidak boleh lebih kecil dari dana yang sudah terkumpul (Rp {collected_val:,.0f})."
            }
    except (ValueError, TypeError):
        return {"success": False, "message": "Target donasi tidak valid."}

    try:
        deadline_obj = datetime.strptime(deadline_date[:10], "%Y-%m-%d").date()
    except Exception:
        return {"success": False, "message": "Format tanggal tenggat waktu tidak valid."}

    sql = """
        UPDATE campaigns
        SET title = %s, category_id = %s, target_amount = %s, deadline_date = %s,
            short_description = %s, story = %s, image_url = %s
        WHERE id = %s
    """
    db.execute_query(sql, (
        title.strip(),
        category_id,
        target_val,
        str(deadline_obj),
        short_description.strip(),
        story.strip(),
        image_url.strip() or camp["image_url"],
        campaign_id
    ), commit=True)

    return {"success": True, "message": "Campaign berhasil diperbarui."}


def delete_campaign(session_token: str, campaign_id: int):
    """
    Deletes campaign. Only allowed if collected_amount == 0 and no success donations exist.
    """
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    
    camp = db.execute_query("SELECT * FROM campaigns WHERE id = %s", (campaign_id,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}

    if user["role"] != "admin" and camp["user_id"] != user["user_id"]:
        return {"success": False, "message": "Akses ditolak."}

    if float(camp["collected_amount"]) > 0:
        return {
            "success": False,
            "message": "Campaign yang sudah memiliki donasi berhasil tidak dapat dihapus demi audit & transparansi."
        }

    db.execute_query("DELETE FROM campaigns WHERE id = %s", (campaign_id,), commit=True)
    return {"success": True, "message": "Campaign berhasil dihapus."}


def add_campaign_update(session_token: str, campaign_id: int, title: str, content: str, image_url: str = None):
    """Adds a progress update / kabar terbaru to a campaign."""
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    
    camp = db.execute_query("SELECT user_id FROM campaigns WHERE id = %s", (campaign_id,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}

    if user["role"] != "admin" and camp["user_id"] != user["user_id"]:
        return {"success": False, "message": "Akses ditolak."}

    title = (title or "").strip()
    content = (content or "").strip()
    if not title or not content:
        return {"success": False, "message": "Judul dan isi kabar terbaru wajib diisi."}

    sql = """
        INSERT INTO campaign_updates (campaign_id, title, content, image_url)
        VALUES (%s, %s, %s, %s)
    """
    db.execute_query(sql, (campaign_id, title, content, image_url or "default_update.jpg"), commit=True)
    return {"success": True, "message": "Kabar terbaru berhasil dipublikasikan."}


def add_fund_usage_report(session_token: str, campaign_id: int, expense_title: str,
                          expense_category: str, amount: float, expense_date: str,
                          description: str, proof_document: str = None):
    """
    Records a fund usage transparency report.
    Enforces business constraint: sum of expenses cannot exceed collected_amount!
    """
    user = auth_service.require_auth(session_token, allowed_roles=["fundraiser", "admin"])
    
    camp = db.execute_query("SELECT user_id, collected_amount FROM campaigns WHERE id = %s", (campaign_id,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}

    if user["role"] != "admin" and camp["user_id"] != user["user_id"]:
        return {"success": False, "message": "Akses ditolak."}

    try:
        amt = float(amount)
        if amt <= 0:
            return {"success": False, "message": "Nominal pengeluaran harus lebih besar dari 0."}
    except Exception:
        return {"success": False, "message": "Nominal pengeluaran tidak valid."}

    # Calculate already recorded expenses
    sql_spent = "SELECT COALESCE(SUM(amount), 0) as total_spent FROM fund_usage_reports WHERE campaign_id = %s"
    current_spent = float(db.execute_query(sql_spent, (campaign_id,), fetch_one=True)["total_spent"])
    collected = float(camp["collected_amount"])

    if (current_spent + amt) > collected:
        available = max(0.0, collected - current_spent)
        return {
            "success": False,
            "message": f"Pengeluaran (Rp {amt:,.0f}) melebihi sisa dana yang terkumpul (Rp {available:,.0f})."
        }

    sql = """
        INSERT INTO fund_usage_reports (
            campaign_id, expense_title, expense_category, amount,
            expense_date, description, proof_document
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    db.execute_query(sql, (
        campaign_id,
        expense_title.strip(),
        expense_category.strip(),
        amt,
        expense_date,
        description.strip(),
        proof_document or "kwitansi_pendukung.pdf"
    ), commit=True)

    return {"success": True, "message": "Laporan penggunaan dana berhasil disimpan."}


# -----------------------------------------------------------------------------
# Admin Management Functions
# -----------------------------------------------------------------------------

def get_all_campaigns_admin(session_token: str, status_filter=None):
    """Admin function: returns all campaigns with full operational metadata."""
    auth_service.require_auth(session_token, allowed_roles=["admin"])
    
    conditions = ["1=1"]
    params = []
    if status_filter and status_filter != "all":
        conditions.append("c.status = %s")
        params.append(status_filter)

    where_str = " AND ".join(conditions)
    sql = f"""
        SELECT c.*, cat.name as category_name, u.full_name as organizer_name, u.email as organizer_email
        FROM campaigns c
        JOIN categories cat ON c.category_id = cat.id
        JOIN users u ON c.user_id = u.id
        WHERE {where_str}
        ORDER BY 
            CASE c.status 
                WHEN 'pending' THEN 1 
                WHEN 'active' THEN 2 
                ELSE 3 
            END,
            c.id DESC
    """
    campaigns = [format_campaign_record(c) for c in db.execute_query(sql, params, fetch_all=True)]
    return {"success": True, "campaigns": campaigns}


def approve_campaign(session_token: str, campaign_id: int):
    """Admin approves pending campaign into active."""
    auth_service.require_auth(session_token, allowed_roles=["admin"])
    
    db.execute_query(
        "UPDATE campaigns SET status = 'active', rejection_reason = NULL WHERE id = %s",
        (campaign_id,),
        commit=True
    )
    return {"success": True, "message": "Campaign berhasil disetujui dan kini berstatus aktif publik."}


def reject_campaign(session_token: str, campaign_id: int, reason: str):
    """Admin rejects pending campaign with reason."""
    auth_service.require_auth(session_token, allowed_roles=["admin"])
    
    reason = (reason or "Dokumen atau informasi campaign belum memenuhi kriteria sosial DonasiKita.").strip()
    db.execute_query(
        "UPDATE campaigns SET status = 'rejected', rejection_reason = %s WHERE id = %s",
        (reason, campaign_id),
        commit=True
    )
    return {"success": True, "message": "Campaign telah ditolak dengan catatan verifikasi."}


def complete_campaign(session_token: str, campaign_id: int):
    """Admin or owner closes campaign as completed."""
    user = auth_service.require_auth(session_token, allowed_roles=["admin", "fundraiser"])
    
    camp = db.execute_query("SELECT user_id FROM campaigns WHERE id = %s", (campaign_id,), fetch_one=True)
    if not camp:
        return {"success": False, "message": "Campaign tidak ditemukan."}
    if user["role"] != "admin" and camp["user_id"] != user["user_id"]:
        return {"success": False, "message": "Akses ditolak."}

    db.execute_query("UPDATE campaigns SET status = 'completed' WHERE id = %s", (campaign_id,), commit=True)
    return {"success": True, "message": "Campaign ditandai selesai."}
