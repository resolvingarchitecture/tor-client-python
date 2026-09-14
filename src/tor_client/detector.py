"""Detects a local Tor daemon.

Ports ``tor-client-rust``'s ``detector`` module (itself a port of
``tor-client-java``'s ``LocalTorDetector``). Tor is a C daemon - unlike I2P,
which has a pure-language router this project can embed - so every language
port only ever attaches to a Tor instance already installed and running on
the host.
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

DEFAULT_HOST = "127.0.0.1"
DEFAULT_SOCKS_PORT = 9050
DEFAULT_CONTROL_PORT = 9051
DEFAULT_TIMEOUT = 0.75

_LOG = logging.getLogger(__name__)


@dataclass
class LocalTorDetector:
    """Probes SOCKS + control ports so :meth:`TorClient.start` can fail fast
    with a clear message instead of a confusing connection error later."""

    host: str = DEFAULT_HOST
    socks_port: int = DEFAULT_SOCKS_PORT
    control_port: int = DEFAULT_CONTROL_PORT
    timeout: float = DEFAULT_TIMEOUT

    def is_socks_reachable(self) -> bool:
        return self._reachable(self.socks_port)

    def is_control_reachable(self) -> bool:
        return self._reachable(self.control_port)

    def is_local_tor_running(self) -> bool:
        """True only if both the SOCKS proxy and the control port answer."""
        return self.is_socks_reachable() and self.is_control_reachable()

    def _reachable(self, port: int) -> bool:
        try:
            with socket.create_connection((self.host, port), timeout=self.timeout):
                return True
        except OSError as e:
            _LOG.debug("nothing on %s:%s (%s)", self.host, port, e)
            return False
