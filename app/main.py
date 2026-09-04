import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import hmac
import traceback
from io import BytesIO
from urllib.parse import quote
from uuid import uuid4

import httpx
from PIL import Image
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import config, database, swachhata_client
from .security import hash_password, verify_password
from .store import get_store
from .views import CATEGORY_NAMES, STRICT_CATEGORIES

database.Base.metadata.create_all(bind=database.engine)
database.ensure_schema()

_model = None


def get_model():
    global _model
    if _model is None:
        import tensorflow as tf

        print("Loading ResNet50 Model...")
        _model = tf.keras.applications.ResNet50(weights="imagenet")
        print("AI Model Loaded.")
    return _model

app = FastAPI(title="Nagardrishti")
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 14,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.cache = None
os.makedirs("static/uploads", exist_ok=True)

store = get_store()
try:
    api_client = swachhata_client.SwachhataClient()
except Exception as exc:
    print(f"Warning: API Client failed to load. {exc}")
    api_client = None


def render(request: Request, name: str, **ctx):
    ctx["request"] = request
    ctx["user"] = request.session.get("user")
    ctx["is_admin"] = request.session.get("is_admin", False)
    ctx["cloud_enabled"] = store.is_cloud
    ctx["message"] = ctx.get("message") or request.query_params.get("msg", "")
    ctx["categories"] = CATEGORY_NAMES
    html = templates.env.get_template(name).render(**ctx)
    return HTMLResponse(html)


def redirect(path: str, msg: str = ""):
    url = path
    if msg:
        joiner = "&" if "?" in path else "?"
        url = f"{path}{joiner}msg={quote(msg)}"
    return RedirectResponse(url=url, status_code=303)


def login_user(request: Request, user):
    request.session["user"] = {
        "id": user.id,
        "full_name": user.full_name,
        "mobile_number": user.mobile_number,
    }


def require_citizen(request: Request):
    if not request.session.get("user"):
        return redirect("/login?next=" + quote(request.url.path), "Please log in first.")
    return None


def detect_category_from_image(image_path: str):
    try:
        import numpy as np
        import tensorflow as tf

        model = get_model()
        with Image.open(image_path) as img:
            img = img.convert("RGB").resize((224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img)

        img_array = np.expand_dims(img_array, axis=0)
        img_array = tf.keras.applications.resnet50.preprocess_input(img_array)
        preds = model.predict(img_array)
        decoded = tf.keras.applications.resnet50.decode_predictions(preds, top=10)[0]

        for (_code, label, score) in decoded:
            label = label.lower()
            if score < 0.02:
                continue
            for cat_id, keywords in STRICT_CATEGORIES.items():
                if any(k in label for k in keywords) or any(label in k for k in keywords):
                    return cat_id, CATEGORY_NAMES[cat_id]
        return None, None
    except Exception as exc:
        print(f"AI Error: {exc}")
        return None, None


def compress_upload(upload: UploadFile) -> bytes:
    raw = upload.file.read()
    with Image.open(BytesIO(raw)) as img:
        img = img.convert("RGB")
        img.thumbnail((1280, 1280))
        out = BytesIO()
        img.save(out, format="JPEG", quality=80, optimize=True)
        return out.getvalue()


@app.get("/")
def home(request: Request):
    msg = request.query_params.get("msg", "")
    return render(request, "index.html", message=msg)


@app.get("/register")
def show_register_page(request: Request):
    if request.session.get("user"):
        return redirect("/", "You are already logged in.")
    return render(request, "register.html")


@app.post("/register")
def register_user(
    request: Request,
    full_name: str = Form(...),
    mobile_number: str = Form(...),
    password: str = Form(...),
):
    mobile_number = mobile_number.strip()
    full_name = full_name.strip()
    if len(mobile_number) != 10 or not mobile_number.isdigit():
        return render(request, "register.html", error="Enter a valid 10-digit mobile number.")
    if len(password) < 6:
        return render(request, "register.html", error="Password must be at least 6 characters.")
    if store.get_user_by_mobile(mobile_number):
        return render(request, "register.html", error="This mobile number is already registered. Please log in.")

    swachhata_id = None
    if api_client:
        try:
            swachhata_id = api_client.register_user(full_name, mobile_number)
        except Exception:
            pass

    user = store.create_user(
        full_name=full_name,
        mobile=mobile_number,
        password_hash=hash_password(password),
        swachhata_user_id=swachhata_id,
    )
    login_user(request, user)
    return redirect("/", "Account created. You can report issues from any device with this login.")


@app.get("/login")
def show_login(request: Request):
    if request.session.get("user"):
        return redirect("/")
    return render(request, "login.html", next_url=request.query_params.get("next", "/"))


@app.post("/login")
def do_login(
    request: Request,
    mobile_number: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/"),
):
    user = store.get_user_by_mobile(mobile_number.strip())
    if not user or not verify_password(password, user.password_hash):
        return render(
            request,
            "login.html",
            error="Invalid mobile number or password.",
            next_url=next_url or "/",
        )
    login_user(request, user)
    target = next_url if next_url.startswith("/") else "/"
    return redirect(target, "Logged in.")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/", "Logged out.")


@app.post("/detect-category")
async def api_detect_category(file: UploadFile = File(...)):
    temp_path = os.path.join("static", "uploads", f"temp_{uuid4().hex}.jpg")
    try:
        data = compress_upload(file)
        with open(temp_path, "wb") as buffer:
            buffer.write(data)
        cat_id, cat_name = detect_category_from_image(temp_path)
    except Exception as exc:
        print(f"Detect error: {exc}")
        return {"suggested_id": None, "category_name": "Unknown"}
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    if cat_id is None:
        return {"suggested_id": None, "category_name": "Unknown"}
    return {"suggested_id": cat_id, "category_name": cat_name}


@app.get("/api/reverse-geocode")
async def reverse_geocode(lat: float, lon: float):
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": "Nagardrishti/1.0 (civic-reporting)"},
            )
        response.raise_for_status()
        payload = response.json()
        return {"address": payload.get("display_name") or f"{lat:.5f}, {lon:.5f}"}
    except Exception as exc:
        print(f"Geocode error: {exc}")
        return JSONResponse({"address": "", "error": "Could not resolve address"}, status_code=200)


@app.get("/report")
def show_report_page(request: Request):
    blocked = require_citizen(request)
    if blocked:
        return blocked
    return render(request, "report.html")


@app.post("/report")
def submit_report(
    request: Request,
    category_id: int = Form(...),
    address: str = Form(...),
    description: str = Form(""),
    latitude: float = Form(0.0),
    longitude: float = Form(0.0),
    file: UploadFile = File(...),
    force_submit: bool = Form(False),
):
    blocked = require_citizen(request)
    if blocked:
        return blocked

    session_user = request.session["user"]
    user = store.get_user_by_id(session_user["id"])
    if not user:
        request.session.clear()
        return redirect("/login", "Session expired. Please log in again.")

    try:
        image_bytes = compress_upload(file)
        os.makedirs("static/uploads", exist_ok=True)
        temp_path = os.path.join("static", "uploads", f"ai_{uuid4().hex}.jpg")
        with open(temp_path, "wb") as handle:
            handle.write(image_bytes)
        ai_id, ai_name = detect_category_from_image(temp_path)
        try:
            os.remove(temp_path)
        except OSError:
            pass

        submission_status = "Pending Sync"
        final_msg = "Report submitted successfully."

        if ai_id and category_id in STRICT_CATEGORIES and ai_id != category_id:
            if force_submit:
                description = f"[AI Flag: Detected {ai_name}] {description}".strip()
                submission_status = "Flagged"
                final_msg = "Report submitted (AI mismatch overridden)."
            else:
                return redirect("/report", f"Error: AI sees {ai_name}. Tick the box to force submit.")

        image_url = store.save_image(image_bytes, suffix=".jpg")

        swachhata_complaint_id = None
        if api_client:
            try:
                swachhata_complaint_id = api_client.post_complaint(
                    user.mobile_number, category_id, latitude, longitude, address, image_url
                )
                if submission_status == "Pending Sync":
                    submission_status = "Synced"
            except Exception as exc:
                print(f"API Sync Failed: {exc}")

        store.create_complaint(
            user_id=user.id,
            category_id=category_id,
            latitude=latitude,
            longitude=longitude,
            address=address,
            image_url=image_url,
            description=description,
            status=submission_status,
            swachhata_complaint_id=swachhata_complaint_id,
        )
        return redirect("/my-reports", final_msg)
    except Exception:
        print("CRITICAL ERROR IN SUBMIT_REPORT:")
        traceback.print_exc()
        return redirect("/report", "Could not save the report. Try again.")


@app.get("/my-reports")
def my_reports(request: Request):
    blocked = require_citizen(request)
    if blocked:
        return blocked
    user = request.session["user"]
    complaints = store.list_complaints_for_user(user["id"])
    return render(request, "my_reports.html", complaints=complaints)


@app.get("/admin/login")
def admin_login_page(request: Request):
    if request.session.get("is_admin"):
        return RedirectResponse("/admin", status_code=303)
    return render(request, "admin_login.html")


@app.post("/admin/login")
def admin_login(request: Request, password: str = Form(...)):
    if not config.ADMIN_PASSWORD:
        return render(request, "admin_login.html", error="Set ADMIN_PASSWORD in your .env file first.")
    if not hmac.compare_digest(password, config.ADMIN_PASSWORD):
        return render(request, "admin_login.html", error="Wrong admin password.")
    request.session["is_admin"] = True
    return redirect("/admin", "Admin access granted.")


@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return redirect("/", "Admin logged out.")


@app.get("/admin")
def admin_dashboard(request: Request):
    if not request.session.get("is_admin"):
        return redirect("/admin/login", "Admin login required.")
    users = store.list_all_users()
    complaints = store.list_all_complaints()
    return render(request, "admin.html", users=users, complaints=complaints)
