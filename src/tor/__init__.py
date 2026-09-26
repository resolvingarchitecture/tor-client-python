"""tor-client - a local-only Tor client for 1M5, in Python.

Attaches to a Tor daemon already running on the host via its SOCKS proxy
(``127.0.0.1:9050``); the control port (``9051``) is probed for readiness
only. A Python port of ``tor-client-java`` / ``tor-client-rust``'s local
backend - see ``DESIGN.md`` for why there is no embedded backend here.
"""

from ra_common.envelope import Envelope

from .client import DEFAULT_REQUEST_TIMEOUT, Status, TorClient
from .detector import (
    DEFAULT_CONTROL_PORT,
    DEFAULT_HOST,
    DEFAULT_SOCKS_PORT,
    LocalTorDetector,
)

__all__ = [
    "TorClient",
    "Status",
    "LocalTorDetector",
    "Envelope",
    "DEFAULT_HOST",
    "DEFAULT_SOCKS_PORT",
    "DEFAULT_CONTROL_PORT",
    "DEFAULT_REQUEST_TIMEOUT",
]

__version__ = "0.1.0"
