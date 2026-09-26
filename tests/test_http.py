from __future__ import annotations

import pytest

from tor.http import format_get, parse_url, split_body


def test_parse_url_with_path_and_port():
    assert parse_url("http://example.onion:81/path") == ("example.onion", 81, "/path")


def test_parse_url_no_path_defaults_to_root():
    assert parse_url("http://example.onion") == ("example.onion", 80, "/")


def test_parse_url_rejects_https():
    with pytest.raises(ValueError):
        parse_url("https://example.onion/")


def test_format_get_has_close_connection():
    req = format_get("example.onion", "/path")
    assert req.startswith("GET /path HTTP/1.1\r\n")
    assert "Host: example.onion\r\n" in req
    assert req.endswith("Connection: close\r\n\r\n")


def test_split_body_after_headers():
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello"
    assert split_body(raw) == b"hello"


def test_split_body_with_no_separator_returns_whole_buffer():
    raw = b"not really http"
    assert split_body(raw) == raw
