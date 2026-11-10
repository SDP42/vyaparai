"""Fetch a file from a user-supplied link without letting it reach our own network (SSRF).

Rules, following the OWASP SSRF cheat sheet:
- https only, default port, no user:password in the link;
- the host must be on the allow-list (Google Sheets and Drive, Dropbox, GitHub raw) unless an
  administrator opened it to any public host;
- the name is resolved once and every address must be public (not loopback, private, link-local,
  metadata, multicast or reserved); the connection goes to exactly that address, with the original
  name for TLS and the Host header, so a changing DNS answer cannot redirect us;
- redirects are followed by hand, at most 3, and every hop passes the same checks;
- timeout and size are capped, and an HTML page (a sign-in screen) is refused.
"""

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.errors import AppError

MAX_REDIRECTS = 3
ACCEPT_TYPES = (
    "text/csv", "text/plain", "application/csv", "application/octet-stream",
    "application/vnd.ms-excel", "application/zip", "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)  # fmt: skip


class UnsafeUrlError(AppError):
    status_code = 422
    code = "unsafe_url"


class FetchError(AppError):
    status_code = 422
    code = "fetch_failed"


Resolver = Callable[[str, int], list[str]]


def _resolve(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError("That link's address could not be found.") from exc
    return sorted({str(i[4][0]) for i in infos})


def _host_allowed(host: str, allowed: list[str]) -> bool:
    host = host.lower().rstrip(".")
    for pattern in allowed:
        p = pattern.lower()
        if p.startswith("*."):
            if host.endswith(p[1:]) and host != p[2:]:
                return True
        elif host == p:
            return True
    return False


def normalise_url(url: str) -> str:
    """Turn a Google Sheets edit/share link into its CSV export link; leave other links alone."""
    u = url.strip()
    m = re.match(
        r"^https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)(?:/[^?#]*)?(\?[^#]*)?(?:#(.*))?$",
        u,
    )
    if not m or "/pub" in u or "/export" in u:
        return u
    sheet, query, frag = m.group(1), m.group(2) or "", m.group(3) or ""
    gid = next(
        (
            p.split("=", 1)[1]
            for p in (query.lstrip("?") + "&" + frag).split("&")
            if p.startswith("gid=")
        ),
        None,
    )
    return f"https://docs.google.com/spreadsheets/d/{sheet}/export?format=csv" + (
        f"&gid={gid}" if gid else ""
    )


def _is_public(ip: str) -> bool:
    """True only for ordinary public unicast addresses (IPv4-in-IPv6 is judged by the IPv4 inside)."""
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return bool(
        addr.is_global
        and not (
            addr.is_multicast or addr.is_reserved or addr.is_unspecified or addr.is_loopback
            or addr.is_link_local or addr.is_private
        )
    )  # fmt: skip


def check_url(
    url: str, resolver: Resolver | None = None
) -> tuple[urllib.parse.ParseResult, str, int]:
    """Validate a link and return (parsed, address to connect to, port). Raises UnsafeUrlError."""
    s = get_settings()
    p = urllib.parse.urlparse(url.strip())
    if p.scheme != "https":
        raise UnsafeUrlError("The link must start with https://")
    if p.username or p.password or "@" in (p.netloc or ""):
        raise UnsafeUrlError("The link must not contain a user name or password.")
    host = (p.hostname or "").lower()
    if not host:
        raise UnsafeUrlError("The link has no address.")
    port = p.port or 443
    if port != 443:
        raise UnsafeUrlError("Only the standard secure port is allowed.")
    try:
        ipaddress.ip_address(host)
        raise UnsafeUrlError("Use the site's name, not a numeric address.")
    except ValueError:
        pass
    if not s.source_allow_any_public_host and not _host_allowed(host, s.source_allowed_hosts):
        raise UnsafeUrlError(
            "That site is not on the allowed list. Use a Google Sheets, Drive or Dropbox link."
        )
    ips = (resolver or _resolve)(host, port)
    if not ips:
        raise FetchError("That link's address could not be found.")
    for ip in ips:
        if not _is_public(ip):
            raise UnsafeUrlError("That link points to a private or internal address.")
    return p, ips[0], port


@dataclass(slots=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


Requester = Callable[[urllib.parse.ParseResult, str, int, float, int], Response]


def _request(
    p: urllib.parse.ParseResult, ip: str, port: int, timeout: float, max_bytes: int
) -> Response:
    """One GET straight to the validated address, with the original name for TLS and Host."""
    ctx = ssl.create_default_context()
    sock = socket.create_connection((ip, port), timeout=timeout)
    try:
        tls = ctx.wrap_socket(sock, server_hostname=p.hostname)
    except Exception:
        sock.close()
        raise
    conn = http.client.HTTPSConnection(p.hostname or "", port, timeout=timeout, context=ctx)
    conn.sock = tls
    path = (p.path or "/") + (f"?{p.query}" if p.query else "")
    try:
        conn.request(
            "GET",
            path,
            headers={
                "Host": p.hostname or "",
                "User-Agent": "vyapar-ai-import/1.0",
                "Accept": "text/csv,*/*;q=0.5",
            },
        )
        r = conn.getresponse()
        body = r.read(max_bytes + 1)
        return Response(r.status, {k.lower(): v for k, v in r.getheaders()}, body)
    finally:
        conn.close()


def fetch(
    url: str,
    *,
    max_bytes: int,
    resolver: Resolver | None = None,
    requester: Requester | None = None,
) -> tuple[bytes, str]:
    """Download a file safely. Returns (bytes, sha256). Raises UnsafeUrlError or FetchError."""
    s = get_settings()
    do = requester or _request
    current = normalise_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        p, ip, port = check_url(current, resolver)
        try:
            resp = do(p, ip, port, s.source_fetch_timeout_seconds, max_bytes)
        except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
            raise FetchError("The link could not be reached. Check it and try again.") from exc
        if resp.status in (301, 302, 303, 307, 308):
            loc = resp.headers.get("location")
            if not loc:
                raise FetchError("The link redirected without saying where.")
            current = urllib.parse.urljoin(current, loc)  # re-validated at the top of the loop
            continue
        if resp.status in (401, 403):
            raise FetchError(
                "The link is private. Share it with 'Anyone with the link' or publish it."
            )
        if resp.status == 404:
            raise FetchError("The link was not found.")
        if resp.status != 200:
            raise FetchError(f"The link answered with an error ({resp.status}).")
        if len(resp.body) > max_bytes:
            raise FetchError(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        head = resp.body[:512].lstrip().lower()
        if ctype == "text/html" or head.startswith((b"<!doctype html", b"<html")):
            raise FetchError(
                "The link opened a web page, not a file. Publish the sheet as CSV, or share it "
                "so anyone with the link can view it."
            )
        if ctype and ctype not in ACCEPT_TYPES:
            raise FetchError("The link did not return a CSV or Excel file.")
        if not resp.body:
            raise FetchError("The file is empty.")
        return resp.body, hashlib.sha256(resp.body).hexdigest()
    raise FetchError("The link redirected too many times.")


def describe(error: Exception) -> str:
    return str(error) if isinstance(error, AppError) else "The import failed. Try again later."
