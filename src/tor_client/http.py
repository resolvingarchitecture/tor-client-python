"""A tiny HTTP/1.1 GET. HTTP only (no TLS) - HTTPS needs a TLS layer wrapped
around the SOCKS socket, see ``TODO.md``. Ports ``tor-client-rust``'s ``http``
module.
"""

from __future__ import annotations

from . import socks

_USER_AGENT = "ra-tor-client"


def fetch_via_socks(
    proxy_host: str,
    proxy_port: int,
    url: str,
    timeout: float,
) -> bytes:
    """Fetch ``url`` (``http://`` only) through the SOCKS5 proxy; returns the
    response body."""
    host, port, path = parse_url(url)

    s = socks.connect_through(proxy_host, proxy_port, host, port, timeout)
    try:
        s.sendall(format_get(host, path).encode("ascii"))
        raw = bytearray()
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            raw.extend(chunk)
    finally:
        s.close()
    return split_body(bytes(raw))


def parse_url(url: str) -> tuple[str, int, str]:
    """Split ``host``, ``port`` and ``path`` out of an ``http://`` URL. Raises
    on any other scheme."""
    if not url.startswith("http://"):
        raise ValueError(
            "only http:// URLs are supported (HTTPS needs a TLS layer - see TODO.md)"
        )
    rest = url[len("http://") :]
    slash = rest.find("/")
    if slash == -1:
        authority, path = rest, "/"
    else:
        authority, path = rest[:slash], rest[slash:]
    if ":" in authority:
        host, port_str = authority.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError as e:
            raise ValueError("bad port") from e
    else:
        host, port = authority, 80
    return host, port, path


def format_get(host: str, path: str) -> str:
    """The GET request line + headers for ``path`` on ``host``,
    ``Connection: close``."""
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: {_USER_AGENT}\r\n"
        f"Accept: */*\r\n"
        f"Connection: close\r\n\r\n"
    )


def split_body(raw: bytes) -> bytes:
    """Everything after the first CRLFCRLF (the body), or the whole buffer if
    no header/body separator is present."""
    sep = raw.find(b"\r\n\r\n")
    return raw[sep + 4 :] if sep != -1 else raw
