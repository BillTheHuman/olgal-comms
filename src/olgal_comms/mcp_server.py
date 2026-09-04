from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("olgal-comms")


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    base = os.getenv("OLGAL_COMMS_URL", "http://127.0.0.1:8791/api/v1").rstrip("/")
    token = os.getenv("OLGAL_COMMS_TOKEN")
    token_file = os.getenv(
        "OLGAL_COMMS_TOKEN_FILE", str(Path.home() / ".config/olgal-comms/ai.token")
    )
    if not token and Path(token_file).is_file():
        token = Path(token_file).read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("OLGAL_COMMS_TOKEN is not configured")
    data = json.dumps(body).encode() if body is not None else None
    if not (base.startswith("http://127.0.0.1:") or base.startswith("http://[::1]:")):
        raise RuntimeError("OLGAL_COMMS_URL must use an explicit loopback HTTP address")
    request = urllib.request.Request(  # noqa: S310
        f"{base}/{path.lstrip('/')}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OlGal Comms rejected the request ({exc.code}): {detail}") from exc


@mcp.tool()
def comms_status() -> dict[str, Any]:
    """Report actual readiness and privacy boundaries for OlGal communication transports."""
    return _request("GET", "status")


@mcp.tool()
def comms_notify_self(text: str, priority: str = "routine") -> dict[str, Any]:
    """Send a rate-limited notification only to the configured owner; no recipient is accepted."""
    return _request("POST", "notifications", {"text": text, "priority": priority})


@mcp.tool()
def comms_send_voice_note_self(text: str, priority: str = "routine") -> dict[str, Any]:
    """Queue text for policy-controlled voice synthesis and delivery only to the owner."""
    return _request("POST", "voice-notes", {"text": text, "priority": priority})


@mcp.tool()
def comms_request_attention(
    reason: str, priority: str = "important", ttl: int = 300
) -> dict[str, Any]:
    """Ask the owner for a temporary attention session without assuming they saw the request."""
    return _request("POST", "attention", {"reason": reason, "priority": priority, "ttl": ttl})


@mcp.tool()
def comms_poll_attention(session_id: str) -> dict[str, Any]:
    """Read transport-confirmed state for an attention session owned by this AI capability."""
    return _request("GET", f"sessions/{session_id}")


@mcp.tool()
def comms_request_call_self(
    reason: str,
    urgency: str = "important",
    media_mode: str = "text-voice",
    transport: str = "webrtc",
    ttl: int = 300,
) -> dict[str, Any]:
    """Request a private call to the owner; ordinary calls require the owner's acceptance."""
    return _request(
        "POST",
        "calls",
        {
            "reason": reason,
            "priority": urgency,
            "media_mode": media_mode,
            "transport": transport,
            "ttl": ttl,
        },
    )


@mcp.tool()
def comms_call_status(session_id: str) -> dict[str, Any]:
    """Read the confirmed state of a call session owned by this AI capability."""
    return _request("GET", f"sessions/{session_id}")


@mcp.tool()
def comms_end_call(session_id: str) -> dict[str, Any]:
    """End a call session owned by this AI capability."""
    return _request("POST", f"sessions/{session_id}/end", {})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
