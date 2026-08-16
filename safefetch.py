"""
SSRF-resistant HTTP GET helper used by all fetchers.

Protections:
  - scheme allowlist (http/https only)
  - DNS resolution check: refuses hosts that resolve to private, loopback,
    link-local, reserved, multicast, or unspecified addresses (blocks access to
    internal services and the cloud metadata endpoint 169.254.169.254)
  - redirects are followed only to targets that pass the same host checks
  - response size cap (defends against memory-exhaustion via huge responses)
  - mandatory timeout

Residual risk: DNS rebinding between the resolution check and the socket connect
is not fully prevented (would require IP pinning that breaks TLS SNI). Acceptable
for this app's threat model (self-hosted, user-controlled config, known hosts).
"""

import ipaddress
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125 Safari/537.36")
MAX_BYTES = 8 * 1024 * 1024   # 8 MiB


class FetchError(Exception):
    """Raised when a request is refused for safety or exceeds limits."""


def _assert_public_host(host: str) -> None:
    if not host:
        raise FetchError("missing host")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise FetchError(f"cannot resolve host: {host!r}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise FetchError(f"refusing non-public address {ip} for host {host!r}")


def _assert_allowed_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise FetchError(f"scheme not allowed: {parts.scheme!r}")
    _assert_public_host(parts.hostname)
    return url


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_allowed_url(newurl)   # re-validate every redirect hop
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SafeRedirect)


def get(url: str, *, headers: dict | None = None, timeout: int = 30,
        max_bytes: int = MAX_BYTES) -> bytes:
    _assert_allowed_url(url)
    h = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with _OPENER.open(req, timeout=timeout) as resp:
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise FetchError(f"response exceeds {max_bytes} bytes")
    return data


def get_text(url: str, *, headers: dict | None = None, timeout: int = 30,
             max_bytes: int = MAX_BYTES, encoding: str = "utf-8") -> str:
    return get(url, headers=headers, timeout=timeout, max_bytes=max_bytes).decode(encoding, "ignore")
