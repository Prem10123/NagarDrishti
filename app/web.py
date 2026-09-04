from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .security.csrf import ensure_csrf_token
from .services.store import get_store

templates = Jinja2Templates(directory="templates")
templates.env.autoescape = True
templates.env.cache = None


def configure_sessions(app) -> None:
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.SECRET_KEY,
        session_cookie="nd_session",
        same_site="lax",
        https_only=config.SESSION_HTTPS_ONLY,
        max_age=config.CITIZEN_SESSION_SECONDS,
    )


def render(request: Request, name: str, **ctx):
    ctx["request"] = request
    ctx["user"] = request.session.get("user")
    ctx["is_admin"] = request.session.get("is_admin", False)
    ctx["cloud_enabled"] = get_store().is_cloud
    ctx["message"] = ctx.get("message") or request.query_params.get("msg", "")
    ctx["csrf_token"] = ensure_csrf_token(request)
    html = templates.env.get_template(name).render(**ctx)
    return HTMLResponse(html)


def redirect(path: str, msg: str = "") -> RedirectResponse:
    url = path
    if msg:
        joiner = "&" if "?" in path else "?"
        url = f"{path}{joiner}msg={quote(msg)}"
    return RedirectResponse(url=url, status_code=303)
