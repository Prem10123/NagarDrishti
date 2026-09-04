import re

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

import httpx

from .. import config
from ..security.csrf import csrf_guard
from ..security.http import client_ip
from ..security.rate_limit import limiter
from ..security.session import require_citizen
from ..security.validation import clamp_coords
from ..services.ai import detect_category_from_bytes
from ..services.images import ImageRejected, compress_upload
from ..services.store import get_store
from ..web import redirect

router = APIRouter(dependencies=[Depends(csrf_guard)])
store = get_store()
_MEDIA = re.compile(r"^[a-fA-F0-9]{32}\.jpg$")


@router.post("/detect-category")
async def api_detect_category(request: Request, file: UploadFile = File(...)):
    blocked = require_citizen(request)
    if blocked:
        return JSONResponse({"error": "auth_required"}, status_code=401)
    if not limiter.allow(f"detect:{client_ip(request)}", 20, 10 * 60):
        return JSONResponse({"suggested_id": None, "category_name": "Unknown", "error": "rate_limited"}, status_code=429)
    try:
        data = compress_upload(file)
        cat_id, cat_name = detect_category_from_bytes(data)
    except ImageRejected:
        return {"suggested_id": None, "category_name": "Unknown"}
    except Exception as exc:
        print(f"Detect error: {exc}")
        return {"suggested_id": None, "category_name": "Unknown"}
    if cat_id is None:
        return {"suggested_id": None, "category_name": "Unknown"}
    return {"suggested_id": cat_id, "category_name": cat_name}


@router.get("/api/reverse-geocode")
async def reverse_geocode(request: Request, lat: float, lon: float):
    blocked = require_citizen(request)
    if blocked:
        return JSONResponse({"address": "", "error": "auth_required"}, status_code=401)
    if not limiter.allow(f"geocode:{client_ip(request)}", 30, 10 * 60):
        return JSONResponse({"address": "", "error": "rate_limited"}, status_code=429)
    lat, lon = clamp_coords(lat, lon)
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": "Nagardrishti/1.0 (civic-reporting)"},
            )
        response.raise_for_status()
        payload = response.json()
        address = payload.get("display_name") or ""
        return {"address": address[:400]}
    except Exception as exc:
        print(f"Geocode error: {exc}")
        return JSONResponse({"address": "", "error": "Could not resolve address"}, status_code=200)


@router.get("/media/{filename}")
def media(request: Request, filename: str):
    if not _MEDIA.fullmatch(filename):
        return JSONResponse({"error": "not_found"}, status_code=404)
    user = request.session.get("user")
    is_admin = bool(request.session.get("is_admin"))
    if not user and not is_admin:
        return redirect("/login", "Please log in first.")
    if is_admin:
        allowed = store.image_exists(filename)
    else:
        allowed = store.user_can_view_image(user["id"], filename)
    if not allowed:
        return JSONResponse({"error": "not_found"}, status_code=404)
    path = config.UPLOAD_DIR / filename
    legacy = config.ROOT / "static" / "uploads" / filename
    file_path = path if path.is_file() else legacy
    if not file_path.is_file():
        return JSONResponse({"error": "not_found"}, status_code=404)
    return FileResponse(file_path, media_type="image/jpeg", headers={"X-Content-Type-Options": "nosniff"})
