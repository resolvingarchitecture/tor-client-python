from __future__ import annotations

import socket
import threading

from ra_common.envelope import Envelope

from tor_client import Status, TorClient


def test_start_fails_cleanly_without_a_daemon():
    client = TorClient.from_config(
        {"ra.tor.socksPort": "9098", "ra.tor.controlPort": "9099"}
    )
    assert client.start() is False
    assert client.status() == Status.DISCONNECTED


def test_send_without_start_reports_not_started():
    client = TorClient.from_config(
        {"ra.tor.socksPort": "9098", "ra.tor.controlPort": "9099"}
    )
    env = Envelope()
    env.headers["url"] = "http://example.onion/"
    assert client.send(env) is False
    assert env.headers["error"] == "Tor client not started"


def test_send_without_url_header_errors():
    client = TorClient()
    env = Envelope()
    assert client.send(env) is False
    assert env.headers["error"] == "no url header"


def test_socks_connect_and_http_fetch_through_a_fake_proxy():
    """A fake SOCKS5 proxy that also serves the "destination" HTTP response,
    mirroring tor-client-rust's integration test of the same name."""
    socks_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socks_srv.bind(("127.0.0.1", 0))
    socks_srv.listen(5)
    socks_port = socks_srv.getsockname()[1]

    # separate listener just so the control-port probe passes
    control_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    control_srv.bind(("127.0.0.1", 0))
    control_srv.listen(5)
    control_port = control_srv.getsockname()[1]

    def serve_control() -> None:
        while True:
            try:
                conn, _ = control_srv.accept()
            except OSError:
                return
            conn.close()

    def serve_socks() -> None:
        # The detector probes the SOCKS port before the real request, so
        # accept in a loop and handle whichever connection completes a full
        # handshake; probe connections close after the greeting and are
        # skipped.
        while True:
            conn, _ = socks_srv.accept()
            try:
                greeting = conn.recv(3)
                if len(greeting) < 3:
                    conn.close()
                    continue
                conn.sendall(bytes([0x05, 0x00]))
                head = conn.recv(5)
                name_len = head[4]
                conn.recv(name_len + 2)
                conn.sendall(bytes([0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0]))
                conn.recv(1024)
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n"
                    b"Connection: close\r\n\r\nhello"
                )
            finally:
                conn.close()
            return

    control_thread = threading.Thread(target=serve_control, daemon=True)
    socks_thread = threading.Thread(target=serve_socks, daemon=True)
    control_thread.start()
    socks_thread.start()

    try:
        client = TorClient.from_config(
            {"ra.tor.socksPort": str(socks_port), "ra.tor.controlPort": str(control_port)}
        )
        assert client.start() is True

        env = Envelope()
        env.headers["url"] = "http://example.onion/path"
        assert client.send(env) is True
        assert env.headers["body"] == b"hello"
    finally:
        socks_srv.close()
        control_srv.close()
