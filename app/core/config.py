# app/core/config.py
"""
Application configuration - loads from environment variables.
Single source of truth for all settings.
"""
import os
from typing import Optional
from urllib.parse import quote_plus
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# ────────────────────────────────────────────
# WhatsApp Configuration
# ────────────────────────────────────────────
PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "")
CALLBACK_URL: str = os.getenv("CALLBACK_URL", "")

APP_ID: Optional[str] = os.getenv("FB_APP_ID") or os.getenv("META_APP_ID")
APP_SECRET: Optional[str] = os.getenv("FB_APP_SECRET") or os.getenv("META_APP_SECRET")

WEBHOOK_DELAY: float = float(os.getenv("WEBHOOK_CHALLENGE_DELAY", "0"))
VALIDATE_UPDATES: bool = os.getenv("VALIDATE_UPDATES", "true").lower() not in ("0", "false", "no")

FLOW_ID: Optional[str] = os.getenv("FLOW_ID")
FLOW_TOKEN: Optional[str] = os.getenv("FLOW_TOKEN")
FLOW_CTA: str = os.getenv("FLOW_CTA", "Open")
FLOW_ACTION: str = os.getenv("FLOW_ACTION", "navigate")
FLOW_SCREEN: Optional[str] = os.getenv("FLOW_SCREEN")

MAX_BUFFER: int = int(os.getenv("MESSAGE_BUFFER", "200"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ────────────────────────────────────────────
# Tenant / Multi-tenant
# ────────────────────────────────────────────
DEFAULT_TENANT_ID: str = os.getenv("TENANT_ID") or os.getenv("DEFAULT_TENANT_ID") or "bc531d42-ac91-41df-817e-26c339af6b3a"
# ────────────────────────────────────────────
# Database Configuration
# ────────────────────────────────────────────
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "whatspy_db")
DATABASE_URL = os.getenv("DATABASE_URL")

# Build DATABASE_URL
if DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    encoded_password = quote_plus(DB_PASSWORD)
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ────────────────────────────────────────────
# Authentication
# ────────────────────────────────────────────
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin@123")
SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "change-this-secret-key")
SESSION_MAX_AGE: int = 86400

# ────────────────────────────────────────────
# JWT Configuration
# ────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_LIFETIME_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "60"))

if not JWT_SECRET_KEY:
    import warnings
    warnings.warn("JWT_SECRET_KEY not set!")

# ────────────────────────────────────────────
# Settings Class
# ────────────────────────────────────────────
class Settings:
    DATABASE_URL: str = DATABASE_URL
    PHONE_ID: str = PHONE_ID
    TOKEN: str = TOKEN
    VERIFY_TOKEN: str = VERIFY_TOKEN
    ADMIN_USERNAME: str = ADMIN_USERNAME
    ADMIN_PASSWORD: str = ADMIN_PASSWORD
    SESSION_SECRET_KEY: str = SESSION_SECRET_KEY
    JWT_SECRET_KEY: str = JWT_SECRET_KEY
    JWT_ALGORITHM: str = JWT_ALGORITHM
    LOG_LEVEL: str = LOG_LEVEL
    MAX_BUFFER: int = MAX_BUFFER

settings = Settings()