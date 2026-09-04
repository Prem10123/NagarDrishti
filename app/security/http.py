from urllib.parse import urlparse

from fastapi import Request

from .. import config


def client_ip(request: Request) -> str:
    if config.TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64] or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def safe_next_url(url: str, fallback: str = "/") -> str:
    if not url:
        return fallback
    url = url.strip()
    if any(ch in url for ch in ("\n", "\r", "\0", "\\")):
        return fallback
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not url.startswith("/") or url.startswith("//"):
        return fallback
    return url
