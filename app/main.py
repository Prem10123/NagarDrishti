import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import config, database, models  # noqa: F401
from .routers import admin, api, auth, pages, reports
from .security.csrf import CSRFError
from .security.headers import SecurityHeadersMiddleware
from .web import configure_sessions, redirect

database.Base.metadata.create_all(bind=database.engine)
database.ensure_schema()

_docs = None if config.ENV == "production" else "/docs"
app = FastAPI(
    title="Nagardrishti",
    docs_url=_docs,
    redoc_url=None if config.ENV == "production" else "/redoc",
    openapi_url=None if config.ENV == "production" else "/openapi.json",
)

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(api.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

configure_sessions(app)
app.add_middleware(SecurityHeadersMiddleware)
if config.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)


@app.exception_handler(CSRFError)
async def csrf_failed(request: Request, _exc: CSRFError):
    path = request.url.path
    if path.startswith("/api") or path.startswith("/detect-category") or request.headers.get("x-csrf-token"):
        return JSONResponse({"error": "csrf"}, status_code=403)
    return redirect("/", "Your session expired. Refresh the page and try again.")
