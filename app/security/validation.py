import math
import re
from typing import Optional

from .. import config
from ..views import CATEGORY_NAMES

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_mobile(value: str) -> Optional[str]:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) != 10:
        return None
    return digits


def normalize_full_name(value: str) -> Optional[str]:
    name = _CONTROL.sub("", (value or "")).strip()
    name = re.sub(r"\s+", " ", name)
    if len(name) < 2 or len(name) > 80:
        return None
    return name


def normalize_address(value: str) -> Optional[str]:
    address = _CONTROL.sub("", (value or "")).strip()
    address = re.sub(r"\s+", " ", address)
    if len(address) < 3 or len(address) > 400:
        return None
    return address


def normalize_description(value: str) -> str:
    text = _CONTROL.sub("", value or "").strip()
    return text[:2000]


def validate_password(password: str) -> Optional[str]:
    if not password or len(password) < config.PASSWORD_MIN_LENGTH:
        return f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters."
    if len(password) > 128:
        return "Password is too long."
    if password.strip() != password:
        return "Password cannot start or end with spaces."
    return None


def parse_category_id(raw) -> Optional[int]:
    try:
        category_id = int(raw)
    except (TypeError, ValueError):
        return None
    if category_id not in CATEGORY_NAMES:
        return None
    return category_id


def clamp_coords(lat: float, lon: float) -> tuple[float, float]:
    if not math.isfinite(lat) or not math.isfinite(lon):
        return 0.0, 0.0
    lat = max(-90.0, min(90.0, lat))
    lon = max(-180.0, min(180.0, lon))
    return lat, lon
