# tor (Python) — TODO

## P0 — local client (done)

- [x] `LocalTorDetector` (probe SOCKS 9050 + control 9051); `start()` fails
      fast with an actionable message when no daemon is reachable.
- [x] Hand-rolled SOCKS5 CONNECT (no auth) on stdlib `socket`.
- [x] HTTP/1.1 GET through the SOCKS tunnel; response body on
      `envelope.headers["body"]`.
- [x] Config keys aligned with `tor-rust`: `ra.tor.host`,
      `ra.tor.socksPort`, `ra.tor.controlPort`, `ra.tor.requestTimeoutSecs`.

## P0.5 — Embedded Tor (planned, matching tor-java's new model)

`tor-java` no longer attaches to a pre-existing Tor daemon at all - it
downloads the official Tor Project binary, verifies it, and spawns/owns it
directly (see its README.md "Trust model" / DESIGN.md "Why embedded"). Not
started here yet - genuinely simpler than most other ports since the stdlib
already covers every primitive needed (no new dependency required at all):

- [ ] `TorBinary`-equivalent: resolve OS/arch (`platform.system()`/
      `platform.machine()`), download the official Tor Project Expert Bundle
      into a local cache (first run only, `urllib.request` - stdlib HTTPS),
      verify its SHA-256 (`hashlib.sha256`) against a value pinned in this
      port's own source (never trusted from the network alongside the
      download), extract with the stdlib `tarfile` module.
- [ ] `EmbeddedTor`-equivalent: spawn via `subprocess.Popen` with a generated
      `torrc` (`SocksPort auto`, `ControlPort auto`, real
      `CookieAuthentication 1`, `__OwningControllerProcess <our pid>`).
- [ ] A *minimal* control client - `AUTHENTICATE` with the real cookie,
      `GETINFO status/bootstrap-phase` (poll until `PROGRESS=100`), `GETINFO
      net/listeners/socks` - a subset of the full `TORControlConnection` port
      in P2 below; P0.5 doesn't need the rest of P2 to land first.
- [ ] Never fall back to attaching to some other Tor instance if provisioning
      or bootstrap fails - fail closed (`start()` returns `False`, never
      raises), matching every other port's existing "fails cleanly" contract.

## P1 — request path

- [ ] HTTPS (`ssl.SSLContext` wrapped around the SOCKS socket).
- [ ] Follow redirects; surface status code + headers.
- [ ] Reuse the SOCKS connection / a small pool instead of one per request.
- [ ] Configurable `User-Agent`; strip identifying headers by default.
- [ ] Async variant (`asyncio` socket API) once a real caller needs it —
      the sync stdlib client is deliberately the v1 scope.

## P2 — Tor control protocol

- [ ] Port `TORControlConnection` / `TORControlCommands` from
      `tor-java` (authenticate with `CookieAuthentication 0` or a
      control password).
- [ ] Async event stream (`SETEVENTS`) → map `CIRC` / `STATUS_CLIENT` onto
      `Status`; live readiness instead of a one-shot probe.
- [ ] `NEWNYM` (new circuit) on demand.

## P3 — inbound / hidden service

- [ ] Create or load an onion service key, `ADD_ONION` via the control port.
- [ ] Accept connections on the HS target port, turn requests into
      `Envelope`s (mirrors `tor-java`'s HS handler).

## P4 — privacy hardening

- [ ] Stream isolation: distinct SOCKS credentials per identity / destination.
- [ ] Optional bridge / pluggable-transport config passthrough (needs the
      system Tor's own bridge config — no embedded backend here to configure).

## Testing / ops

- [ ] Integration test behind a marker that uses a real local Tor daemon.
- [x] Fake-SOCKS-proxy integration test (`test_client.py`), no live network.
- [ ] CI: `pytest`, `ruff`/`mypy` if/when the project adopts them elsewhere.
- [ ] Publish to PyPI once the API settles (currently local editable install
      only).

## Cross-repo

- [ ] Keep `Status` and config keys aligned with `tor-java` 1.2.x and
      `tor-rust`'s local backend.
- [ ] Wire into a future `1m5-core-python`'s protocol-service adapter, same
      pattern as `NetworkServiceProtocol`/`TorProtocolService` in
      `1m5-core-java` and `1m5-core-rust`.
