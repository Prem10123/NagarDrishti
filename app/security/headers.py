from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from .. import config

_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        length = headers.get("content-length")
        if length:
            try:
                if int(length) > config.MAX_REQUEST_BYTES:
                    await self._plain(send, 413, b"Request too large")
                    return
            except ValueError:
                await self._plain(send, 400, b"Invalid request")
                return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(raw=message.setdefault("headers", []))
                response_headers["X-Content-Type-Options"] = "nosniff"
                response_headers["X-Frame-Options"] = "DENY"
                response_headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response_headers["Permissions-Policy"] = (
                    "camera=(self), geolocation=(self), microphone=(), payment=()"
                )
                response_headers["Content-Security-Policy"] = _CSP
                response_headers["Cross-Origin-Opener-Policy"] = "same-origin"
                response_headers["X-Permitted-Cross-Domain-Policies"] = "none"
                if config.SESSION_HTTPS_ONLY:
                    response_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_wrapper)

    async def _plain(self, send: Send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": body})
