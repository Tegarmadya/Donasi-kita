"""
Authentication and Authorization Service for DonasiKita.
Handles password hashing (bcrypt), session tokens, multi-role access control,
and user management.
"""

import secrets
from datetime import datetime, timedelta
import bcrypt
import db


# Server-side active session store: session_token -> dict of user data
# In a desktop/Eel application, this provides fast, safe, server-enforced state.
import json
from pathlib import Path
import config

SESSION_FILE = config.BASE_DIR / ".sessions.json"

def _load_sessions():
    """Loads active sessions from persistent JSON file."""
    if not SESSION_FILE.exists():
        return {}
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            sessions = {}
            now = datetime.now()
            for token, data in raw.items():
                exp = datetime.fromisoformat(data["expires_at"])
                if exp > now:
                    data["expires_at"] = exp
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                    sessions[token] = data
            return sessions
    except Exception:
        return {}

def _save_sessions(sessions):
    """Saves active sessions to persistent JSON file."""
    try:
        serializable = {}
        for token, data in sessions.items():
            copy_data = dict(data)
            copy_data["created_at"] = str(copy_data["created_at"])
            copy_data["expires_at"] = str(copy_data["expires_at"])
            serializable[token] = copy_data
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to persist session: {e}")

ACTIVE_SESSIONS = _load_sessions()


def hash_password(plain_password: str) -> str:
    """Hash password with bcrypt using 12 salt rounds."""
    if not plain_password:
        raise ValueError("Password tidak boleh kosong.")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_session(user: dict) -> str:
    """Creates a new authenticated session token."""
    global ACTIVE_SESSIONS
    ACTIVE_SESSIONS = _load_sessions()
    token = secrets.token_hex(24)
    ACTIVE_SESSIONS[token] = {
        "user_id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "avatar": user.get("avatar") or "default_avatar.png",
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(days=7)
    }
    _save_sessions(ACTIVE_SESSIONS)
    return token


def get_session_user(session_token: str):
    """
    Validates session token and returns active user info, or None if invalid/expired.
    """
    global ACTIVE_SESSIONS
    if not session_token:
        return None
    ACTIVE_SESSIONS = _load_sessions()
    if session_token not in ACTIVE_SESSIONS:
        return None
    session = ACTIVE_SESSIONS[session_token]
    if datetime.now() > session["expires_at"]:
        del ACTIVE_SESSIONS[session_token]
        _save_sessions(ACTIVE_SESSIONS)
        return None
    return session


def require_auth(session_token: str, allowed_roles=None):
    """
    Validates that the session is active and role is authorized.
    Raises PermissionError or ValueError if unauthorized.
    """
    user = get_session_user(session_token)
    if not user:
        raise PermissionError("Sesi Anda telah berakhir atau tidak valid. Silakan login kembali.")
    if allowed_roles:
        if isinstance(allowed_roles, str):
            allowed_roles = [allowed_roles]
        if user["role"] not in allowed_roles:
            raise PermissionError(f"Akses ditolak. Fitur ini memerlukan hak akses: {', '.join(allowed_roles)}.")
    return user


def register(full_name: str, email: str, password: str, role: str = "donatur", phone: str = None):
    """
    Registers a new user account.
    Validates email format, unique constraint, password length, and allowed roles.
    """
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    password = (password or "").strip()
    phone = (phone or "").strip()
    
    if not full_name or len(full_name) < 3:
        return {"success": False, "message": "Nama lengkap minimal 3 karakter."}
    if not email or "@" not in email or "." not in email:
        return {"success": False, "message": "Format alamat email tidak valid."}
    if not password or len(password) < 6:
        return {"success": False, "message": "Kata sandi minimal 6 karakter."}
    
    # Validasi role: pengunjung umum hanya boleh daftar sebagai donatur atau fundraiser
    if role not in ("donatur", "fundraiser"):
        role = "donatur"
    
    # Periksa apakah email sudah terdaftar
    existing = db.execute_query(
        "SELECT id FROM users WHERE email = %s",
        (email,),
        fetch_one=True
    )
    if existing:
        return {"success": False, "message": "Alamat email ini sudah terdaftar. Silakan gunakan email lain atau login."}
    
    password_hash = hash_password(password)
    avatar = "default_avatar.png"
    
    try:
        sql = """
            INSERT INTO users (full_name, email, password_hash, role, phone, avatar, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'active')
        """
        res = db.execute_query(sql, (full_name, email, password_hash, role, phone, avatar), commit=True)
        new_user_id = res["last_insert_id"]
        
        user_info = {
            "id": new_user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "avatar": avatar
        }
        token = create_session(user_info)
        
        return {
            "success": True,
            "message": "Registrasi berhasil. Selamat bergabung di DonasiKita!",
            "session_token": token,
            "user": user_info
        }
    except Exception as e:
        return {"success": False, "message": f"Terjadi kesalahan saat pendaftaran: {str(e)}"}


def login(email: str, password: str):
    """
    Authenticates user with email and plain password.
    Enforces active account status and bcrypt hash match.
    """
    email = (email or "").strip().lower()
    password = (password or "").strip()
    
    if not email or not password:
        return {"success": False, "message": "Email dan kata sandi wajib diisi."}
    
    user = db.execute_query(
        "SELECT id, full_name, email, password_hash, role, phone, avatar, status FROM users WHERE email = %s",
        (email,),
        fetch_one=True
    )
    
    if not user:
        return {"success": False, "message": "Email atau kata sandi tidak cocok."}
    
    if user["status"] != "active":
        return {"success": False, "message": "Akun Anda sedang dinonaktifkan. Hubungi administrator DonasiKita."}
    
    if not verify_password(password, user["password_hash"]):
        return {"success": False, "message": "Email atau kata sandi tidak cocok."}
    
    user_info = {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "avatar": user.get("avatar") or "default_avatar.png"
    }
    token = create_session(user_info)
    
    return {
        "success": True,
        "message": f"Selamat datang kembali, {user['full_name']}!",
        "session_token": token,
        "user": user_info
    }


def logout(session_token: str):
    """Terminates active session."""
    global ACTIVE_SESSIONS
    ACTIVE_SESSIONS = _load_sessions()
    if session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_token]
        _save_sessions(ACTIVE_SESSIONS)
    return {"success": True, "message": "Berhasil logout."}


def get_current_user_profile(session_token: str):
    """Returns profile data of the currently logged-in user from DB."""
    session = get_session_user(session_token)
    if not session:
        return {"success": False, "message": "Sesi tidak valid."}
    
    user = db.execute_query(
        "SELECT id, full_name, email, role, phone, avatar, status, created_at FROM users WHERE id = %s",
        (session["user_id"],),
        fetch_one=True
    )
    if not user:
        return {"success": False, "message": "Pengguna tidak ditemukan."}
    
    # Format created_at to string
    if user.get("created_at"):
        user["created_at"] = str(user["created_at"])
        
    return {"success": True, "user": user}


def get_all_users(session_token: str):
    """Admin function: returns all registered users with their roles and status."""
    require_auth(session_token, allowed_roles=["admin"])
    
    users = db.execute_query(
        """
        SELECT id, full_name, email, role, phone, status, created_at
        FROM users
        ORDER BY id DESC
        """,
        fetch_all=True
    )
    for u in users:
        if u.get("created_at"):
            u["created_at"] = str(u["created_at"])
    return {"success": True, "users": users}


def update_user_status(session_token: str, target_user_id: int, new_status: str):
    """Admin function: toggles user status between 'active' and 'suspended'."""
    admin = require_auth(session_token, allowed_roles=["admin"])
    
    if new_status not in ("active", "suspended"):
        return {"success": False, "message": "Status tidak valid."}
    
    # Prevent admin from suspending themselves
    if int(target_user_id) == admin["user_id"]:
        return {"success": False, "message": "Anda tidak dapat menonaktifkan akun admin Anda sendiri."}
    
    db.execute_query(
        "UPDATE users SET status = %s WHERE id = %s",
        (new_status, target_user_id),
        commit=True
    )
    return {"success": True, "message": f"Status pengguna berhasil diperbarui menjadi {new_status}."}
