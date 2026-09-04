from fastapi import APIRouter, Request

from ..security.session import require_admin
from ..services.store import get_store
from ..web import redirect, render

router = APIRouter()
store = get_store()


@router.get("/admin")
def admin_dashboard(request: Request):
    blocked = require_admin(request)
    if blocked:
        return blocked
    users = store.list_all_users()
    complaints = store.list_all_complaints()
    return render(request, "admin.html", users=users, complaints=complaints)
