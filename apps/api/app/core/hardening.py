"""Security headers, body-size limits and per-address rate limits for every request.

- Headers: no sniffing, no framing, no referrer leakage, a locked-down CSP for API responses, and HSTS in production.
- Size: a request that declares a body larger than the limit is refused before it is read (JSON 1 MB, uploads 20 MB).
- Rate: all requests per address per minute, with a tighter limit for the endpoints that cost the most (uploads,
  search, questions, investigations, reports). The address is the proxy's X-Forwarded-For only if TRUST_PROXY is on.
"""

import re
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.errors import error_body
from app.core.ratelimit import Limiter, RateLimitedError, make_limiter

HEAVY = re.compile(
    r"/(documents(/search)?|bills|assistant/(ask|stream)|agents/runs|reports|reviews/import|udhaar/import|"
    r"campaigns/contacts/import|datasets|inventory/import|sources)$"
)
EXEMPT = ("/api/v1/health", "/docs", "/openapi.json", "/redoc")
_limiters: dict[str, Limiter] = {}


def reset() -> None:
    _limiters.clear()


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


def _lim(name: str, limit: int, settings: Settings) -> Limiter:
    if name not in _limiters:
        _limiters[name] = make_limiter(name, limit, 60, settings.redis_url)
    return _limiters[name]


def apply_headers(response: Response, settings: Settings) -> None:
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "no-referrer"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    h["Cross-Origin-Resource-Policy"] = "same-site"
    if "content-security-policy" not in h and "/docs" not in h.get("location", ""):
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.is_production:
        h["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"


def make_middleware(
    settings: Settings,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def hardening(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if path.startswith(EXEMPT) or request.method == "OPTIONS":
            resp = await call_next(request)
            if not path.startswith(("/docs", "/redoc")):  # the docs UI needs its own scripts
                apply_headers(resp, settings)
            return resp
        declared = request.headers.get("content-length")
        if declared and declared.isdigit():
            limit = (
                settings.max_upload_body_mb * 1024 * 1024
                if "multipart" in request.headers.get("content-type", "")
                else settings.max_json_body_kb * 1024
            )
            if int(declared) > limit:
                resp = JSONResponse(
                    status_code=413,
                    content=error_body("payload_too_large", "That request is too large."),
                )
                apply_headers(resp, settings)
                return resp
        ip = client_ip(request, settings)
        try:
            _lim("all", settings.rate_limit_per_minute, settings).check(ip)
            _lim("all", settings.rate_limit_per_minute, settings).hit(ip)
            if request.method != "GET" and HEAVY.search(path):
                _lim("heavy", settings.heavy_rate_limit_per_minute, settings).check(ip)
                _lim("heavy", settings.heavy_rate_limit_per_minute, settings).hit(ip)
        except RateLimitedError as exc:
            resp = JSONResponse(
                status_code=429,
                content=error_body("rate_limited", "Too many requests. Please slow down."),
                headers={"Retry-After": str(exc.retry_after)},
            )
            apply_headers(resp, settings)
            return resp
        resp = await call_next(request)
        apply_headers(resp, settings)
        return resp

    return hardening
