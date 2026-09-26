"""``TorClient`` - the local-only Tor client. Ports ``tor-client-rust``'s
``TorClient`` minus the ``Mode``/embedded-backend split: Arti (the pure-Rust
Tor implementation ``tor-client-rust`` embeds) has no Python equivalent, so
this port - like ``tor-client-java`` - only ever attaches to a Tor daemon
already running on the host. See ``DESIGN.md``.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum

from ra_common.envelope import Envelope

from .detector import LocalTorDetector
from .http import fetch_via_socks

_LOG = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT = 60.0


class Status(str, Enum):
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    ERROR = "Error"


class TorClient:
    """A Tor client attached to a local Tor daemon's SOCKS proxy (default
    ``127.0.0.1:9050``); the control port (default ``9051``) is probed for
    readiness only - see ``TODO.md`` for the control protocol.
    """

    def __init__(self) -> None:
        self.detector = LocalTorDetector()
        self.request_timeout = DEFAULT_REQUEST_TIMEOUT
        self._status = Status.DISCONNECTED
        self._lock = threading.Lock()

    @classmethod
    def from_config(cls, cfg: dict[str, str]) -> "TorClient":
        """Config keys: ``ra.tor.host``, ``ra.tor.socksPort``,
        ``ra.tor.controlPort``, ``ra.tor.requestTimeoutSecs``."""
        c = cls()
        if "ra.tor.host" in cfg:
            c.detector.host = cfg["ra.tor.host"]
        if "ra.tor.socksPort" in cfg:
            c.detector.socks_port = int(cfg["ra.tor.socksPort"])
        if "ra.tor.controlPort" in cfg:
            c.detector.control_port = int(cfg["ra.tor.controlPort"])
        if "ra.tor.requestTimeoutSecs" in cfg:
            c.request_timeout = float(cfg["ra.tor.requestTimeoutSecs"])
        return c

    def status(self) -> Status:
        with self._lock:
            return self._status

    def _set_status(self, s: Status) -> None:
        with self._lock:
            self._status = s

    def start(self) -> bool:
        """Probe the local daemon. Returns ``False`` cleanly (never raises) if
        Tor is unavailable."""
        self._set_status(Status.CONNECTING)
        if not self.detector.is_local_tor_running():
            _LOG.warning(
                "No local Tor daemon on %s (SOCKS %s reachable=%s, control %s "
                "reachable=%s). Install and run Tor with 'ControlPort 9051' - "
                "see README.md.",
                self.detector.host,
                self.detector.socks_port,
                self.detector.is_socks_reachable(),
                self.detector.control_port,
                self.detector.is_control_reachable(),
            )
            self._set_status(Status.DISCONNECTED)
            return False
        _LOG.info(
            "Local Tor daemon reachable (SOCKS %s, control %s).",
            self.detector.socks_port,
            self.detector.control_port,
        )
        self._set_status(Status.CONNECTED)
        return True

    def stop(self) -> bool:
        self._set_status(Status.DISCONNECTED)
        return True

    def send(self, envelope: Envelope) -> bool:
        """Fetch ``envelope.headers["url"]`` through Tor into
        ``envelope.headers["body"]``. HTTP only for now. On error, records
        ``envelope.headers["error"]``.

        Uses ``headers`` rather than a generic payload field - unlike
        ``seda_bus::Envelope`` in Rust, ``ra_common.Envelope`` carries typed
        ``Message`` content, not a raw byte payload, and this client has no
        opinion on which ``Message`` subtype a caller wants.
        """
        url = envelope.headers.get("url")
        if not url:
            envelope.headers["error"] = "no url header"
            return False

        if self.status() != Status.CONNECTED:
            envelope.headers["error"] = "Tor client not started"
            return False

        try:
            body = fetch_via_socks(
                self.detector.host,
                self.detector.socks_port,
                url,
                self.request_timeout,
            )
        except (OSError, ValueError) as e:
            _LOG.warning("Tor request to %s failed: %s", url, e)
            envelope.headers["error"] = str(e)
            return False

        envelope.headers["body"] = body
        return True
