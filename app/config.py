import os
import secrets

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
SWACHHATA_API_URL = os.getenv("SWACHHATA_API_URL", "https://api.swachh.city/sbm/v1")
SWACHHATA_VENDOR = os.getenv("SWACHHATA_VENDOR_NAME", "")
SWACHHATA_ACCESS_KEY = os.getenv("SWACHHATA_ACCESS_KEY", "")

CLOUD_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)
STORAGE_BUCKET = os.getenv("SUPABASE_BUCKET", "complaint-photos")
