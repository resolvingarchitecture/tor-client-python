"""Minimal SOCKS5 CONNECT client (no auth) - enough to tunnel an HTTP request
through Tor's SOCKS proxy. Ports ``tor-client-rust``'s ``socks`` module.
"""

from __future__ import annotations

import socket


def connect_through(
    proxy_host: str,
    proxy_port: int,
    dest_host: str,
    dest_port: int,
    timeout: float,
) -> socket.socket:
    """Open a TCP connection to ``dest_host:dest_port`` *through* the SOCKS5
    proxy at ``proxy_host:proxy_port``."""
    s = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    s.settimeout(max(timeout, 30.0))

    # greeting: VER=5, NMETHODS=1, METHOD=0 (no auth)
    s.sendall(bytes([0x05, 0x01, 0x00]))
    method = _recv_exact(s, 2)
    if method != b"\x05\x00":
        s.close()
        raise OSError(f"SOCKS5 proxy refused no-auth (got {method!r})")

    # request: VER=5, CMD=1 (connect), RSV=0, ATYP=3 (domain), len, name, port
    dest_host_bytes = dest_host.encode("ascii")
    if len(dest_host_bytes) > 255:
        s.close()
        raise ValueError("host too long")
    req = bytes([0x05, 0x01, 0x00, 0x03, len(dest_host_bytes)])
    req += dest_host_bytes
    req += dest_port.to_bytes(2, "big")
    s.sendall(req)

    # reply: VER, REP, RSV, ATYP, BND.ADDR, BND.PORT
    head = _recv_exact(s, 4)
    if head[1] != 0x00:
        s.close()
        raise ConnectionError(f"SOCKS5 connect failed, REP={head[1]}")
    atyp = head[3]
    if atyp == 0x01:
        bnd_len = 4
    elif atyp == 0x04:
        bnd_len = 16
    elif atyp == 0x03:
        bnd_len = _recv_exact(s, 1)[0]
    else:
        s.close()
        raise OSError(f"SOCKS5 bad ATYP {atyp}")
    _recv_exact(s, bnd_len + 2)  # BND.ADDR + BND.PORT
    return s


def _recv_exact(s: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise OSError("connection closed early")
        buf.extend(chunk)
    return bytes(buf)
