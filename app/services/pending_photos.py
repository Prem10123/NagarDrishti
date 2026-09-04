import time
from pathlib import Path

from fastapi import Request

from .. import config

_TTL_SECONDS = 30 * 60


def stash_pending_photo(request: Request, image_bytes: bytes) -> None:
    user = request.session.get("user") or {}
    user_id = user.get("id")
    if not user_id or not image_bytes:
        return
    _purge_expired()
    token = f"{int(user_id)}_{int(time.time())}_{len(image_bytes)}"
    path = _path_for(user_id)
    path.write_bytes(image_bytes)
    request.session["pending_photo_at"] = time.time()
    request.session["pending_photo_token"] = token


def take_pending_photo(request: Request) -> bytes | None:
    user = request.session.get("user") or {}
    user_id = user.get("id")
    stamped = float(request.session.get("pending_photo_at") or 0)
    if not user_id or time.time() - stamped > _TTL_SECONDS:
        return None
    path = _path_for(user_id)
    if not path.is_file():
        return None
    data = path.read_bytes()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    request.session.pop("pending_photo_at", None)
    request.session.pop("pending_photo_token", None)
    return data or None


def _path_for(user_id: int) -> Path:
    return config.UPLOAD_DIR / f"pending-{int(user_id)}.jpg"


def _purge_expired() -> None:
    cutoff = time.time() - _TTL_SECONDS
    for path in config.UPLOAD_DIR.glob("pending-*.jpg"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            pass
