"""
DonasiKita - Main Application Entrypoint
Integrates Python backend services with modern Eel frontend.
Exposes secure API functions to the client-side JavaScript layer.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import eel
import config
import db
from services import (
    auth_service,
    campaign_service,
    donation_service,
    payment_service,
    report_service,
    certificate_service
)

# Initialize Eel with web directory
eel.init(str(config.WEB_DIR))


# =============================================================================
# 1. Authentication & User Management Eel APIs
# =============================================================================

@eel.expose
def py_login(email, password):
    try:
        return auth_service.login(email, password)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_register(full_name, email, password, role="donatur", phone=""):
    try:
        return auth_service.register(full_name, email, password, role, phone)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_logout(session_token):
    try:
        return auth_service.logout(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_current_user_profile(session_token):
    try:
        return auth_service.get_current_user_profile(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_all_users(session_token):
    try:
        return auth_service.get_all_users(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_update_user_status(session_token, target_user_id, new_status):
    try:
        return auth_service.update_user_status(session_token, target_user_id, new_status)
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# 2. Public Catalog & Campaigns Eel APIs
# =============================================================================

@eel.expose
def py_get_landing_page_data():
    try:
        return campaign_service.get_landing_page_data()
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_categories():
    try:
        return campaign_service.get_categories()
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_campaigns(category_slug="all", search_keyword="", status="active", sort_by="newest"):
    try:
        return campaign_service.get_campaigns(category_slug, search_keyword, status, sort_by)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_campaign_detail(slug_or_id):
    try:
        return campaign_service.get_campaign_detail(slug_or_id)
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# 3. Fundraiser Campaign Management Eel APIs
# =============================================================================

@eel.expose
def py_create_campaign(session_token, title, category_id, target_amount, deadline_date, short_description, story, image_url=""):
    try:
        return campaign_service.create_campaign(
            session_token, title, int(category_id), float(target_amount),
            deadline_date, short_description, story, image_url
        )
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_fundraiser_campaigns(session_token):
    try:
        return campaign_service.get_fundraiser_campaigns(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_update_campaign(session_token, campaign_id, title, category_id, target_amount, deadline_date, short_description, story, image_url=""):
    try:
        return campaign_service.update_campaign(
            session_token, int(campaign_id), title, int(category_id),
            float(target_amount), deadline_date, short_description, story, image_url
        )
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_delete_campaign(session_token, campaign_id):
    try:
        return campaign_service.delete_campaign(session_token, int(campaign_id))
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_add_campaign_update(session_token, campaign_id, title, content, image_url=""):
    try:
        return campaign_service.add_campaign_update(session_token, int(campaign_id), title, content, image_url)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_add_fund_usage_report(session_token, campaign_id, expense_title, expense_category, amount, expense_date, description, proof_document=""):
    try:
        return campaign_service.add_fund_usage_report(
            session_token, int(campaign_id), expense_title, expense_category,
            float(amount), expense_date, description, proof_document
        )
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_fundraiser_dashboard_summary(session_token):
    try:
        return report_service.get_fundraiser_dashboard_summary(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# 4. Donation & Payment Simulation Eel APIs
# =============================================================================

@eel.expose
def py_create_donation(session_token, campaign_id, amount, is_anonymous=False, prayer_message="", payment_method="bank_transfer", payment_channel="BCA Virtual Account"):
    try:
        return donation_service.create_donation(
            session_token, int(campaign_id), float(amount),
            bool(is_anonymous), prayer_message, payment_method, payment_channel
        )
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_donation_by_code(donation_code):
    try:
        return donation_service.get_donation_by_code(donation_code)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_simulate_payment(payment_code, action="success"):
    try:
        return payment_service.simulate_payment(payment_code, action)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_user_donations(session_token):
    try:
        return donation_service.get_user_donations(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# 5. Digital Certificate Eel APIs
# =============================================================================

@eel.expose
def py_get_certificate_detail(certificate_number):
    try:
        return certificate_service.get_certificate_detail(certificate_number)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_certificate_by_donation_code(donation_code):
    try:
        return certificate_service.get_certificate_by_donation_code(donation_code)
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# 6. Admin Analytics & Operations Eel APIs
# =============================================================================

@eel.expose
def py_get_admin_dashboard_summary(session_token):
    try:
        return report_service.get_admin_dashboard_summary(session_token)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_all_campaigns_admin(session_token, status_filter="all"):
    try:
        return campaign_service.get_all_campaigns_admin(session_token, status_filter)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_approve_campaign(session_token, campaign_id):
    try:
        return campaign_service.approve_campaign(session_token, int(campaign_id))
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_reject_campaign(session_token, campaign_id, reason=""):
    try:
        return campaign_service.reject_campaign(session_token, int(campaign_id), reason)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_complete_campaign(session_token, campaign_id):
    try:
        return campaign_service.complete_campaign(session_token, int(campaign_id))
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_get_all_donations_admin(session_token, status_filter="all"):
    try:
        return donation_service.get_all_donations_admin(session_token, status_filter)
    except Exception as e:
        return {"success": False, "message": str(e)}


@eel.expose
def py_export_donations_csv(session_token, campaign_id=None):
    try:
        c_id = int(campaign_id) if campaign_id else None
        return report_service.export_donations_csv(session_token, c_id)
    except Exception as e:
        return {"success": False, "message": str(e)}


# =============================================================================
# Application Startup
# =============================================================================

def start_app(browser_mode="default", port=None):
    """Starts Eel web desktop application."""
    # Validasi integritas konfigurasi aplikasi sebelum server dijalankan
    try:
        config.validate_config()
    except ValueError as cfg_err:
        print("=" * 65)
        print(f"[FATAL ERROR] Kegagalan Konfigurasi Sistem:")
        print(f"{cfg_err}")
        print("=" * 65)
        sys.exit(1)

    # Deteksi dan gunakan port bebas jika port default sedang digunakan
    import socket
    def find_free_port(start_port, host=config.APP_HOST):
        p = start_port
        while p < start_port + 20:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((host, p))
                    return p
                except OSError:
                    p += 1
        return start_port

    if port is None:
        target_port = find_free_port(config.APP_PORT)
        if target_port != config.APP_PORT:
            print(f"[INFO] Port {config.APP_PORT} sedang digunakan. Mengalihkan ke port bebas: {target_port}")
        app_port = target_port
    else:
        app_port = port

    print("=" * 65)
    print(f" {config.APP_NAME} v{config.APP_VERSION}")
    print(f" {config.APP_TAGLINE}")
    print(f" Server running at: http://{config.APP_HOST}:{app_port}/")
    print(f" Browser Mode: {browser_mode}")
    print("=" * 65)

    try:
        # Check database connection on startup
        conn_check = db.test_connection()
        if conn_check["status"] == "success":
            print(f"[DB OK] Terhubung ke MySQL ({conn_check['database']} - {conn_check['version']})")
        else:
            print(f"[DB WARN] Koneksi database bermasalah: {conn_check['message']}")
            print("Pastikan XAMPP / MySQL service telah berjalan.")
    except Exception as db_err:
        print(f"[DB ERROR] {db_err}")

    # Eel browser mode options: 'chrome', 'edge', 'default', None (server only)
    mode = None if browser_mode == "none" else ("edge" if browser_mode == "edge" else "default")
    
    try:
        eel.start(
            "index.html",
            host=config.APP_HOST,
            port=app_port,
            size=(1280, 850),
            mode=mode,
            close_callback=lambda page, sockets: None
        )
    except (SystemExit, MemoryError, KeyboardInterrupt):
        print("\n[INFO] DonasiKita dimatikan dengan aman.")
    except OSError as os_err:
        if getattr(os_err, 'winerror', None) == 10048 or "10048" in str(os_err) or "address" in str(os_err).lower():
            print(f"\n[ERROR] Port {app_port} sudah digunakan oleh proses lain.")
            print(f"Jalankan aplikasi dengan port lain, contoh: python main.py --port {app_port + 1}")
        else:
            print(f"\n[ERROR] Kesalahan jaringan: {os_err}")
    except Exception as err:
        print(f"\n[INFO] Mode desktop window fallback ke server browser: {err}")
        try:
            # Fallback to headless/standard browser if specific browser binary not detected
            eel.start("index.html", host=config.APP_HOST, port=app_port, mode=None)
        except Exception as e2:
            print(f"[ERROR] Gagal membuka browser fallback: {e2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DonasiKita E-Donation Platform")
    parser.add_argument("--mode", default="default", help="Browser mode: default, edge, chrome, none")
    parser.add_argument("--port", type=int, default=config.APP_PORT, help="Port to run web server")
    args = parser.parse_args()

    start_app(browser_mode=args.mode, port=args.port)
