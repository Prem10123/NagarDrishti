from fastapi import APIRouter, Request

from ..web import render

router = APIRouter()


@router.get("/")
def home(request: Request):
    msg = request.query_params.get("msg", "")
    return render(request, "index.html", message=msg)
