from fastapi import APIRouter, Depends, Form, Request

from ..security.csrf import csrf_guard
from ..security.http import client_ip, safe_next_url
from ..security.passwords import hash_password, secrets_match, verify_password
from ..security.rate_limit import limiter
from ..security.session import cycle_session, login_admin, login_citizen
from ..security.validation import normalize_full_name, normalize_mobile, validate_password
from .. import config
from ..services.store import get_store
from ..services.swachhata import SwachhataClient
from ..web import redirect, render

router = APIRouter(dependencies=[Depends(csrf_guard)])
store = get_store()
try:
    api_client = SwachhataClient()
except Exception as exc:
    print(f"Warning: API Client failed to load. {exc}")
    api_client = None


@router.get("/register")
def show_register_page(request: Request):
    if request.session.get("user"):
        return redirect("/", "You are already logged in.")
    return render(request, "register.html")


@router.post("/register")
async def register_user(
    request: Request,
    full_name: str = Form(...),
    mobile_number: str = Form(...),
    password: str = Form(...),
):
    if not limiter.allow(f"register:{client_ip(request)}", 5, 15 * 60):
        return render(request, "register.html", error="Too many attempts. Wait a few minutes.")
    name = normalize_full_name(full_name)
    mobile = normalize_mobile(mobile_number)
    password_error = validate_password(password)
    if not name:
        return render(request, "register.html", error="Enter your full name (2–80 characters).")
    if not mobile:
        return render(request, "register.html", error="Enter a valid 10-digit mobile number.")
    if password_error:
        return render(request, "register.html", error=password_error)
    if store.get_user_by_mobile(mobile):
        return render(request, "register.html", error="This mobile number is already registered. Please log in.")

    swachhata_id = None
    if api_client:
        try:
            swachhata_id = api_client.register_user(name, mobile)
        except Exception:
            pass

    user = store.create_user(
        full_name=name,
        mobile=mobile,
        password_hash=hash_password(password),
        swachhata_user_id=swachhata_id,
    )
    login_citizen(request, user)
    return redirect("/", "Account created. You can report issues from any device with this login.")


@router.get("/login")
def show_login(request: Request):
    if request.session.get("user"):
        return redirect("/")
    return render(request, "login.html", next_url=safe_next_url(request.query_params.get("next", "/")))


@router.post("/login")
async def do_login(
    request: Request,
    mobile_number: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/"),
):
    if not limiter.allow(f"login:{client_ip(request)}", 10, 15 * 60):
        return render(
            request,
            "login.html",
            error="Too many attempts. Wait a few minutes.",
            next_url=safe_next_url(next_url),
        )
    mobile = normalize_mobile(mobile_number)
    user = store.get_user_by_mobile(mobile) if mobile else None
    if not user:
        verify_password(password, None)
        return render(
            request,
            "login.html",
            error="Invalid mobile number or password.",
            next_url=safe_next_url(next_url),
        )
    if not verify_password(password, user.password_hash):
        return render(
            request,
            "login.html",
            error="Invalid mobile number or password.",
            next_url=safe_next_url(next_url),
        )
    login_citizen(request, user)
    return redirect(safe_next_url(next_url), "Logged in.")


@router.post("/logout")
def logout(request: Request):
    cycle_session(request)
    return redirect("/", "Logged out.")


@router.get("/logout")
def logout_get(request: Request):
    cycle_session(request)
    return redirect("/", "Logged out.")


@router.get("/admin/login")
def admin_login_page(request: Request):
    if request.session.get("is_admin"):
        return redirect("/admin")
    return render(request, "admin_login.html")


@router.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(""),
    password: str = Form(...),
):
    if not limiter.allow(f"admin-login:{client_ip(request)}", 5, 15 * 60):
        return render(request, "admin_login.html", error="Too many attempts. Wait a few minutes.")
    if not config.ADMIN_PASSWORD:
        return render(request, "admin_login.html", error="Admin access is not configured.")
    user_ok = secrets_match((username or "").strip(), config.ADMIN_USERNAME)
    pass_ok = secrets_match(password, config.ADMIN_PASSWORD)
    if not (user_ok and pass_ok):
        return render(request, "admin_login.html", error="Invalid admin credentials.")
    login_admin(request)
    return redirect("/admin", "Admin access granted.")


@router.post("/admin/logout")
def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    request.session.pop("admin_auth_at", None)
    return redirect("/", "Admin logged out.")


@router.get("/admin/logout")
def admin_logout_get(request: Request):
    request.session.pop("is_admin", None)
    request.session.pop("admin_auth_at", None)
    return redirect("/", "Admin logged out.")
