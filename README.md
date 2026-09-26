# tor-client (Python)

A local-only Tor client for **1M5**: attaches to a Tor daemon already
running on this host — SOCKS5 proxy `127.0.0.1:9050`, control port
`127.0.0.1:9051` (probed for readiness only).

A Python port of [`tor-client-java`](https://github.com/resolvingarchitecture/tor-client-java);
mirrors the *local* backend of [`tor-client-rust`](https://github.com/resolvingarchitecture/tor-client-rust)
(no embedded backend — Arti is Rust-only, see `DESIGN.md`).

**This local-daemon-only model is being retired.** `tor-client-java` no longer
attaches to a pre-existing Tor instance at all - it downloads the official Tor
Project binary, verifies it, and spawns/owns it directly, so there is no
fallback to some other already-running Tor anywhere in that library. This port
should adopt the same model; see "Embedded Tor (planned)" below and `TODO.md`.

## Embedded Tor (planned)

Not implemented yet. The plan, matching `tor-client-java`'s current design -
and genuinely simpler here than in most other ports, since the stdlib already
covers every primitive needed:

1. Download the official Tor Project "Expert Bundle" for the current
   OS/arch into a local cache (`urllib.request` - stdlib, HTTPS built in, no
   new dependency), verify its SHA-256 against a value pinned in this port's
   own source (`hashlib.sha256` - stdlib; never trusted from the network
   alongside the download itself), and extract it with the stdlib `tarfile`
   module - no need to shell out to the system `tar` the way `tor-client-java`
   does, since Python's stdlib has a real tar reader.
2. Spawn it (`subprocess.Popen`) with a generated `torrc` (`SocksPort auto`,
   `ControlPort auto`, real `CookieAuthentication 1`,
   `__OwningControllerProcess <our pid>`).
3. Authenticate over the control port with the real cookie and block until
   Tor reports 100% bootstrap - needs at least a minimal control client
   (`AUTHENTICATE`, `GETINFO status/bootstrap-phase`, `GETINFO
   net/listeners/socks`), a subset of the full control-protocol port already
   tracked in `TODO.md` P2.

## Local Tor daemon setup (current model, being retired)

Install Tor (`apt install tor`, `brew install tor`, …) and make sure
`/etc/tor/torrc` (or `~/.torrc`) has:

```
SocksPort 9050
ControlPort 9051
CookieAuthentication 0
```

Then `systemctl start tor` (or `tor -f ~/.torrc`). Check:
`curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip`.

## Use

```python
from ra_common.envelope import Envelope
from tor_client import TorClient

client = TorClient.from_config({})
if client.start():                       # False (cleanly) if Tor is unavailable
    env = Envelope()
    env.headers["url"] = "http://example.onion/"
    client.send(env)                     # body -> env.headers["body"], errors -> env.headers["error"]
```

### Config keys

| key | default | meaning |
|-----|---------|---------|
| `ra.tor.host` | `127.0.0.1` | local daemon host |
| `ra.tor.socksPort` | `9050` | local daemon SOCKS5 proxy port |
| `ra.tor.controlPort` | `9051` | local daemon control port (probed only) |
| `ra.tor.requestTimeoutSecs` | `60` | per-request timeout |

## Build

```
python3.13 -m venv .venv
.venv/bin/pip install -e ../../common/ra-common-python
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

## Status

Early. HTTP (`http://`) works; HTTPS needs a TLS layer wrapped around the
SOCKS socket (see `TODO.md`). The local daemon's control port is only
probed, not spoken — no event stream or hidden-service management yet.
Inbound / onion hosting is not implemented. See `DESIGN.md` and `TODO.md`.
