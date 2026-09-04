from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..security.csrf import csrf_guard
from ..security.rate_limit import limiter
from ..security.http import client_ip
from ..security.session import require_citizen
from ..security.validation import (
    clamp_coords,
    normalize_address,
    normalize_description,
    parse_category_id,
)
from ..services.ai import detect_category_from_bytes
from ..services.images import ImageRejected, compress_upload
from ..services.store import get_store
from ..services.swachhata import SwachhataClient
from ..views import STRICT_CATEGORIES
from ..web import redirect, render

router = APIRouter(dependencies=[Depends(csrf_guard)])
store = get_store()
try:
    api_client = SwachhataClient()
except Exception:
    api_client = None


@router.get("/report")
def show_report_page(request: Request):
    blocked = require_citizen(request)
    if blocked:
        return blocked
    return render(request, "report.html")


@router.post("/report")
async def submit_report(
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
    if not limiter.allow(f"report:{client_ip(request)}", 15, 10 * 60):
        return redirect("/report", "Too many reports in a short time. Try again shortly.")

    session_user = request.session["user"]
    user = store.get_user_by_id(session_user["id"])
    if not user:
        from ..security.session import cycle_session

        cycle_session(request)
        return redirect("/login", "Session expired. Please log in again.")

    parsed_category = parse_category_id(category_id)
    place = normalize_address(address)
    if not parsed_category:
        return redirect("/report", "Choose a valid category.")
    if not place:
        return redirect("/report", "Enter a valid location.")
    lat, lon = clamp_coords(latitude, longitude)
    notes = normalize_description(description)

    try:
        image_bytes = compress_upload(file)
    except ImageRejected as exc:
        return redirect("/report", str(exc))

    try:
        ai_id, ai_name = detect_category_from_bytes(image_bytes)
        submission_status = "Pending Sync"
        final_msg = "Report submitted successfully."

        if ai_id and parsed_category in STRICT_CATEGORIES and ai_id != parsed_category:
            if force_submit:
                notes = f"[AI Flag: Detected {ai_name}] {notes}".strip()
                submission_status = "Flagged"
                final_msg = "Report submitted (AI mismatch overridden)."
            else:
                return redirect("/report", f"Error: AI sees {ai_name}. Tick the box to force submit.")

        image_url = store.save_image(image_bytes, suffix=".jpg")

        swachhata_complaint_id = None
        if api_client:
            try:
                swachhata_complaint_id = api_client.post_complaint(
                    user.mobile_number, parsed_category, lat, lon, place, image_url
                )
                if submission_status == "Pending Sync":
                    submission_status = "Synced"
            except Exception as exc:
                print(f"API Sync Failed: {exc}")

        store.create_complaint(
            user_id=user.id,
            category_id=parsed_category,
            latitude=lat,
            longitude=lon,
            address=place,
            image_url=image_url,
            description=notes,
            status=submission_status,
            swachhata_complaint_id=swachhata_complaint_id,
        )
        return redirect("/my-reports", final_msg)
    except Exception as exc:
        print(f"Submit report failed: {exc}")
        return redirect("/report", "Could not save the report. Try again.")


@router.get("/my-reports")
def my_reports(request: Request):
    blocked = require_citizen(request)
    if blocked:
        return blocked
    user = request.session["user"]
    complaints = store.list_complaints_for_user(user["id"])
    return render(request, "my_reports.html", complaints=complaints)
