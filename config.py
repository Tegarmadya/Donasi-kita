"""
Configuration module for DonasiKita E-Donation Platform.
Loads environment variables and provides global configuration settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Database Settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "donasikita_db")

# Application Settings
# APP_SECRET_KEY wajib diisi melalui variabel lingkungan / .env dan tidak lagi memiliki fallback statis.
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
APP_HOST = os.getenv("APP_HOST", "localhost")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
APP_DEBUG = os.getenv("APP_DEBUG", "True").lower() in ("true", "1", "t")

# Daftar kunci rahasia statis/lemah yang dilarang digunakan
INSECURE_SECRET_KEYS = {
    "donasikita-secret-key-uts-2026-secure",
    "secret",
    "secretkey",
    "changeme",
    "default",
    "admin",
    "12345678",
    "password",
}

_DEFAULT_KEY = object()


def validate_config(secret_key=_DEFAULT_KEY, strict=True):
    """
    Memvalidasi integritas konfigurasi aplikasi DonasiKita.
    Memastikan APP_SECRET_KEY terdefinisi secara eksplisit, memiliki panjang memadai,
    dan tidak menggunakan nilai default statis yang tidak aman.
    
    Args:
        secret_key (str, optional): Nilai secret key yang akan diuji. Jika tidak diberikan, menggunakan config.APP_SECRET_KEY.
        strict (bool): Jika True, akan memunculkan ValueError saat konfigurasi tidak valid.
        
    Returns:
        tuple: (bool, str) status validasi dan pesan penjelasan.
        
    Raises:
        ValueError: Jika strict=True dan konfigurasi tidak valid.
    """
    key = APP_SECRET_KEY if secret_key is _DEFAULT_KEY else secret_key

    if not key or not str(key).strip():
        err_msg = (
            "Konfigurasi tidak valid: APP_SECRET_KEY belum disetel di file .env atau environment. "
            "Aplikasi DonasiKita tidak lagi menggunakan kunci rahasia statis bawaan demi keamanan. "
            "Silakan buat kunci rahasia baru yang aman dengan menjalankan:\n"
            "    python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "kemudian simpan nilainya ke dalam variabel APP_SECRET_KEY pada file .env lokal Anda."
        )
        if strict:
            raise ValueError(err_msg)
        return False, err_msg

    key_str = str(key).strip()
    if key_str in INSECURE_SECRET_KEYS:
        err_msg = (
            f"Konfigurasi tidak aman: APP_SECRET_KEY terdeteksi menggunakan kunci default statis ('{key_str}'). "
            "Ketergantungan pada kunci statis bawaan telah dihilangkan demi mencegah kerentanan keamanan. "
            "Silakan buat kunci rahasia acak yang unik di file .env lokal Anda menggunakan:\n"
            "    python -c \"import secrets; print(secrets.token_hex(32))\""
        )
        if strict:
            raise ValueError(err_msg)
        return False, err_msg

    if len(key_str) < 16:
        err_msg = (
            f"Konfigurasi tidak valid: APP_SECRET_KEY terlalu pendek ({len(key_str)} karakter). "
            "Panjang minimal adalah 16 karakter (disarankan 64 karakter heksadesimal acak)."
        )
        if strict:
            raise ValueError(err_msg)
        return False, err_msg

    return True, "Konfigurasi APP_SECRET_KEY valid dan aman."


# Validasi konfigurasi secara otomatis saat modul dimuat, kecuali dibypass untuk isolated testing
if os.getenv("DONASIKITA_SKIP_CONFIG_VALIDATION") != "1":
    validate_config(strict=True)

# Directory Paths
WEB_DIR = BASE_DIR / "web"
DATABASE_DIR = BASE_DIR / "database"
DOCS_DIR = BASE_DIR / "docs"
EVIDENCE_DIR = BASE_DIR / "evidence"
DELIVERABLES_DIR = BASE_DIR / "deliverables"

# Ensure essential output directories exist
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
(EVIDENCE_DIR / "screenshots").mkdir(parents=True, exist_ok=True)
DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)

# Application Metadata
APP_NAME = "DonasiKita"
APP_TAGLINE = "Platform E-Donation & E-Crowdfunding Amanah & Terpercaya"
APP_VERSION = "1.0.0"
