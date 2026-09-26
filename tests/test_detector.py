from __future__ import annotations

import socket
import threading

from tor.detector import LocalTorDetector


def _listening_port() -> tuple[socket.socket, int]:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    return srv, srv.getsockname()[1]


def test_unreachable_port_is_not_reachable():
    d = LocalTorDetector(host="127.0.0.1", socks_port=1, control_port=1, timeout=0.2)
    assert d.is_socks_reachable() is False
    assert d.is_local_tor_running() is False


def test_reachable_port_is_reachable():
    srv, port = _listening_port()
    try:
        d = LocalTorDetector(host="127.0.0.1", socks_port=port, timeout=0.5)
        assert d.is_socks_reachable() is True
    finally:
        srv.close()


def test_is_local_tor_running_requires_both_ports():
    socks_srv, socks_port = _listening_port()
    try:
        d = LocalTorDetector(
            host="127.0.0.1", socks_port=socks_port, control_port=1, timeout=0.2
        )
        assert d.is_socks_reachable() is True
        assert d.is_control_reachable() is False
        assert d.is_local_tor_running() is False
    finally:
        socks_srv.close()
