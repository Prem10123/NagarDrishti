import secrets
import time
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from .. import config
from .http import safe_next_url


def is_mutating(method: str) -> bool:
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}


def cycle_session(request: Request, **values) -> None:
    request.session.clear()
    request.session["csrf_token"] = secrets.token_urlsafe(32)
    for key, value in values.items():
        request.session[key] = value


def redirect(path: str, msg: str = "") -> RedirectResponse:
    from urllib.parse import quote

    url = path
    if msg:
        joiner = "&" if "?" in path else "?"
        url = f"{path}{joiner}msg={quote(msg)}"
    return RedirectResponse(url=url, status_code=303)


def login_citizen(request: Request, user) -> None:
    cycle_session(
        request,
        user={
            "id": user.id,
            "full_name": user.full_name,
            "mobile_number": user.mobile_number,
        },
    )


def login_admin(request: Request) -> None:
    cycle_session(
        request,
        is_admin=True,
        admin_auth_at=time.time(),
    )


def require_citizen(request: Request) -> Optional[RedirectResponse]:
    user = request.session.get("user")
    if not user or not user.get("id"):
        nxt = safe_next_url(request.url.path)
        return redirect("/login?next=" + quote_path(nxt), "Please log in first.")
    return None


def require_admin(request: Request) -> Optional[RedirectResponse]:
    if not request.session.get("is_admin"):
        return redirect("/admin/login", "Admin login required.")
    started = float(request.session.get("admin_auth_at") or 0)
    if time.time() - started > config.ADMIN_SESSION_SECONDS:
        request.session.pop("is_admin", None)
        request.session.pop("admin_auth_at", None)
        return redirect("/admin/login", "Admin session expired. Sign in again.")
    return None


def quote_path(path: str) -> str:
    from urllib.parse import quote

    return quote(path, safe="/")
