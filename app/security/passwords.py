import hashlib
import hmac
import os
from typing import Optional

NEW_ROUNDS = 210_000
LEGACY_ROUNDS = 120_000
_DUMMY_SALT = bytes(16)
_DUMMY_DIGEST = hashlib.pbkdf2_hmac("sha256", b"timing-guard", _DUMMY_SALT, LEGACY_ROUNDS)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, NEW_ROUNDS)
    return f"pbkdf2$sha256${NEW_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    password_bytes = password.encode("utf-8")
    parsed = _parse_hash(stored)
    if parsed is None:
        actual = hashlib.pbkdf2_hmac("sha256", password_bytes, _DUMMY_SALT, LEGACY_ROUNDS)
        hmac.compare_digest(actual, _DUMMY_DIGEST)
        return False
    salt, expected, rounds = parsed
    actual = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, rounds)
    return hmac.compare_digest(actual, expected)


def secrets_match(given: str, expected: str) -> bool:
    left = hashlib.sha256((given or "").encode("utf-8")).digest()
    right = hashlib.sha256((expected or "").encode("utf-8")).digest()
    return hmac.compare_digest(left, right)


def _parse_hash(stored: Optional[str]):
    if not stored or "$" not in stored:
        return None
    try:
        if stored.startswith("pbkdf2$"):
            _scheme, _algo, rounds_s, salt_hex, digest_hex = stored.split("$", 4)
            return bytes.fromhex(salt_hex), bytes.fromhex(digest_hex), int(rounds_s)
        salt_hex, digest_hex = stored.split("$", 1)
        return bytes.fromhex(salt_hex), bytes.fromhex(digest_hex), LEGACY_ROUNDS
    except (ValueError, TypeError):
        return None
