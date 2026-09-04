# Transport boundaries and gates

## SimpleX

SimpleX is the initial asynchronous notification path. Pair exactly one owner contact, bind any bot
WebSocket to loopback, and set `OLGAL_SIMPLEX_COMMAND`. The adapter stays unavailable until its
executable and self-contact configuration exist.

## TerminalPhone

Set `OLGAL_TERMINALPHONE_PATH` only to a reviewed release of the OlGal fork. The original v1.1.9
full-duplex engine labels a SHA-256-derived XOR stream as AES-CTR; it is not accepted for production
use. The fork's v2 protocol must pass its tamper, replay, nonce, and downgrade tests first.

## SIP

Install `baresip` and set `OLGAL_BARESIP_COMMAND` to enable local SIP tests. V1 does not configure a
carrier or ordinary telephone number.

## Venice speech

`OLGAL_VENICE_BASE_URL` points to OlGal's existing Aster bridge at `http://127.0.0.1:8021`. Secrets
remain outside this repository. Aster currently requires a fresh confirmation and verified quote
for speech generation, so readiness does not authorize autonomous paid calls. A future recurring
communications budget must be an explicit user-approved Aster policy change. Selected audio or
text crosses the Venice trust boundary; native-audio models may bypass STT/TTS.

## iMessage

This adapter is intentionally disabled. It requires Apple-branded hardware, a security-supported
macOS release, a dedicated user-created Apple Account, and user-completed verification and terms.
The relay keeps Apple credentials on the Mac and exposes only a narrow authenticated Tailscale API.
Private APIs that require weakened macOS security remain off by default.

## Cellular/PSTN

This adapter is intentionally unfinished so it is not mistaken for a broken feature. Enabling it
requires a carrier choice, explicit number authorization, credential custody, a cost ceiling, and
user approval of any recurring or per-minute spend.
