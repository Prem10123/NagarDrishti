import hmac
import secrets

from fastapi import Request

from .session import is_mutating


class CSRFError(Exception):
    pass


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token or not isinstance(token, str) or len(token) < 16:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


async def require_csrf(request: Request) -> None:
    if not is_mutating(request.method):
        return
    expected = request.session.get("csrf_token")
    if not expected:
        raise CSRFError()
    supplied = request.headers.get("x-csrf-token")
    if not supplied:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            raw = form.get("csrf_token")
            supplied = raw if isinstance(raw, str) else None
    if not supplied or not hmac.compare_digest(str(supplied), str(expected)):
        raise CSRFError()


async def csrf_guard(request: Request) -> None:
    await require_csrf(request)
