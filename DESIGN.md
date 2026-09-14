# tor-client (Python) — Design

A local-only Tor client: attaches to a Tor daemon already running on the
host via its SOCKS proxy, for use as the Tor **protocol service** by a
future `1m5-core-python`. A Python port of the design in
[`tor-client-java`](https://github.com/resolvingarchitecture/tor-client-java),
trimmed to the same scope `tor-client-rust`'s *local* backend covers.

## Where it sits

    (future) 1m5-core-python  ──wraps──►  tor_client.TorClient
                                                  │
                                     SOCKS5 127.0.0.1:9050
                                     control 127.0.0.1:9051 (probe only)
                                                  │
                                          system tor daemon

A router service would discover this client by name/type and push a
routing-slip hop carrying the destination URL, same as the Rust and Java
adapters do; this repo only provides the client itself.

## No embedded backend

Unlike `tor-client-rust`, there is no `Mode { Local, Embedded, Auto }` here.
Rust's `embedded` backend runs [Arti](https://gitlab.torproject.org/tpo/core/arti),
the Tor Project's pure-**Rust** Tor implementation, in-process — there is no
pure-Python equivalent to embed. So, like `tor-client-java` (Tor is a C
daemon it can't keep updated in-process either), this client only ever
attaches to a Tor instance **installed and running on the host**. See
`tor-client-rust/DESIGN.md` for the embedded design, kept there as the
reference for what a future FFI-based embedded backend (binding Arti's C API,
or `tor-client-rust` built as a shared library) would need to provide across
every non-Rust port — a separate project, not part of this one.

## Components

    LocalTorDetector   probes SOCKS 9050 + control 9051 (socket.create_connection)
                        so start() fails fast, mirrors tor-client-rust's detector
    socks              minimal SOCKS5 CONNECT client, no auth (stdlib socket only)
    http               fetch_via_socks / parse_url / format_get / split_body;
                        http:// only, no TLS
    TorClient          config, status, start()/stop()/send()

## Message flow

**Outbound** — a caller sets `envelope.headers["url"]` to a `.onion` or
clearnet `http://` URL and calls `send()`. `http.fetch_via_socks` opens a
SOCKS5 tunnel through `127.0.0.1:9050`, issues a `GET`, and writes the
response body to `envelope.headers["body"]`.

`ra_common.Envelope` has no generic byte-payload field the way
`seda_bus::Envelope` does in Rust — it carries a typed `Message`
(`DocumentMessage`/`TextMessage`/…) instead. Rather than force a
`DocumentMessage` on every caller, this client puts the raw response bytes
on `envelope.headers["body"]`, keeping the same headers-in/headers-out
contract `tor-client-rust` uses (`headers["url"]` in, `headers["error"]` on
failure) rather than inventing a payload convention `ra_common.Envelope`
doesn't have.

**Inbound** — not implemented (see `TODO.md`), same as both other ports.

## Status model

`Status` is its own 4-state enum (`Connecting`, `Connected`, `Disconnected`,
`Error`) — not `ra_common`'s 13-state `NetworkStatus` — matching
`tor-client-rust`'s deliberate choice to keep a small, protocol-service-facing
status distinct from the full network status vocabulary. `start()` sets
`Connecting`, then `Connected` if the daemon answers or `Disconnected`
(cleanly, no exception) if not. `stop()` → `Disconnected`.

## Config keys

Same names as `tor-client-rust` (`ra.tor.mode`/`ra.tor.dataDir` dropped —
no embedded mode to select): `ra.tor.host`, `ra.tor.socksPort`,
`ra.tor.controlPort`, `ra.tor.requestTimeoutSecs`.

## Python adaptations vs. the Rust/Java clients

- No `Mode`/backend switching — see "No embedded backend" above.
- Response body goes on `envelope.headers["body"]`, not a payload field —
  see "Message flow" above.
- SOCKS5 + HTTP hand-rolled on the stdlib `socket` module (no `requests`/
  `PySocks`), matching Rust's dependency-light default build and Java's own
  hand-rolled control/SOCKS code.
- `Status` guarded by a `threading.Lock` rather than an atomic — CPython
  (and free-threaded 3.13+) have no lock-free `AtomicU8` equivalent in the
  stdlib; a plain lock is the idiomatic choice here, mirroring how
  `service-bus-python` guards shared state.
- The Tor control protocol client (`TORControlConnection` & friends) is not
  ported, same gap `tor-client-rust` has.

## Not here

- HTTPS (needs `ssl.SSLContext` wrapped around the SOCKS socket).
- Tor control protocol: authentication, event stream, `NEWNYM`, circuit info.
- Hidden service (onion) hosting for inbound envelopes.
- Stream isolation per identity / per destination.
- An embedded/bridged backend (see "No embedded backend").
