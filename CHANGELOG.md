# Changelog

## 0.1.0

- Initial local-only Tor client: `LocalTorDetector`, hand-rolled SOCKS5 +
  HTTP/1.1 GET, `TorClient` (`from_config`, `start`/`stop`/`send`).
- Depends on `ra-common` for `Envelope`.
- No embedded backend (see `DESIGN.md`).
