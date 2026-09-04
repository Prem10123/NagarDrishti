import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
STORAGE_BUCKET = os.getenv("SUPABASE_BUCKET", "complaint-photos")

SWACHHATA_API_URL = os.getenv("SWACHHATA_API_URL", "https://api.swachh.city/sbm/v1")
SWACHHATA_VENDOR = os.getenv("SWACHHATA_VENDOR_NAME", "")
SWACHHATA_ACCESS_KEY = os.getenv("SWACHHATA_ACCESS_KEY", "")

CLOUD_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)

ENV = os.getenv("APP_ENV", "development").strip().lower() or "development"
SESSION_HTTPS_ONLY = _bool("SESSION_HTTPS_ONLY", default=ENV == "production")
TRUST_PROXY = _bool("TRUST_PROXY", default=False)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

MAX_UPLOAD_BYTES = _int("MAX_UPLOAD_BYTES", 8 * 1024 * 1024)
MAX_REQUEST_BYTES = _int("MAX_REQUEST_BYTES", 10 * 1024 * 1024)
CITIZEN_SESSION_SECONDS = _int("CITIZEN_SESSION_SECONDS", 60 * 60 * 24 * 7)
ADMIN_SESSION_SECONDS = _int("ADMIN_SESSION_SECONDS", 60 * 60 * 2)
PASSWORD_MIN_LENGTH = _int("PASSWORD_MIN_LENGTH", 8)

UPLOAD_DIR = ROOT / "var" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing. Copy .env.example to .env and set a long random value.")
if SECRET_KEY in {"change-this-to-a-long-random-string", "changeme", "secret"}:
    if ENV == "production":
        raise RuntimeError("SECRET_KEY is still the example value. Generate a new random secret.")
