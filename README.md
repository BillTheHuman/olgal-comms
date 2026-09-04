# OlGal Comms

OlGal Comms is a private communications broker that lets authorized AI applications call and
message exactly one person: the owner of the OlGal machine. The public API intentionally has no
recipient parameter.

The first release provides a policy engine, scoped capability tokens, SQLite session state,
metadata-only audit records, REST and MCP interfaces, an installable iPhone PWA, WebRTC signaling,
and capability-detected adapters. SimpleX, TerminalPhone, SIP, Venice, iMessage, and PSTN report
their actual readiness rather than silently falling back.

## Present status

| Capability | State | Boundary |
| --- | --- | --- |
| REST/MCP policy service | Implemented | OlGal loopback |
| iPhone PWA and signaling | Implemented; device test required | Tailscale and the owner's browser |
| SimpleX | Adapter scaffold; CLI not installed | SimpleX network and the owner's device |
| TerminalPhone | Forked; hardened v2 work tracked separately | Tor relays and peer |
| SIP | Adapter scaffold; `baresip` not installed | Local SIP only in v1 |
| Venice speech | Live Aster health adapter; generation remains confirmation-gated | Selected audio/text reaches Venice |
| iMessage | Blocked by design | Requires a lawful Apple relay |
| Cellular/PSTN | Intentionally unfinished | Requires a carrier and spending approval |

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# Generate a token and copy the JSON printed to stderr into OLGAL_TOKENS_JSON.
.venv/bin/olgal-comms-token trusted-ai

# Generate a separate token for the iPhone PWA.
.venv/bin/olgal-comms-token owner-iphone --owner-browser

export OLGAL_TOKENS_JSON='{"replace-with-token":{"subject":"trusted-ai","actions":["notify_self","voice_note_self","request_attention","request_call_self","end_call"]}}'
.venv/bin/olgal-comms
```

The service listens only on `127.0.0.1:8791` by default. See [deployment](docs/DEPLOYMENT.md)
before exposing the PWA through the existing Tailscale and Caddy route.

## Repository map

- `src/olgal_comms`: policy, state, REST API, MCP server, and adapter capability checks.
- `web`: mobile-first PWA and WebRTC signaling client.
- `plugins/olgal-comms`: Codex plugin package.
- `skills/olgal-comms`: reusable standalone skill.
- `docs`: architecture, transport boundaries, deployment, and future adapter gates.
- `deploy`: reviewed service and reverse-proxy examples; nothing is installed automatically.

## Moral source and licenses

The behavioral covenant is derived from the FORGE in
[Eyla Architecture](https://github.com/BillTheHuman/eyla-architecture), while the original
`SOUL.md` remains authoritative. See [COVENANT.md](COVENANT.md).

Software in this repository is offered under AGPL-3.0-or-later. The covenant is offered under
CC BY-SA 4.0. The TerminalPhone downstream fork remains MIT-licensed in its own repository.
