from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from olgal_comms.api import create_app
from olgal_comms.config import Settings
from olgal_comms.models import Capability

TOKEN = "test-token"


def client(tmp_path: Path) -> TestClient:
    cap = Capability(
        subject="test-ai",
        actions=frozenset({"notify_self", "request_attention", "request_call_self", "end_call"}),
    )
    settings = Settings(
        database=tmp_path / "api.db",
        bind_host="127.0.0.1",
        bind_port=8765,
        public_base="/comms",
        tokens={TOKEN: cap},
        quiet_start=25,
        quiet_end=25,
        emergency_enabled=False,
        simplex_command=None,
        terminalphone_path=None,
        baresip_command=None,
        venice_base_url=None,
    )
    return TestClient(create_app(settings))


def test_requires_bearer_token(tmp_path):
    response = client(tmp_path).get("/api/v1/status")
    assert response.status_code == 401


def test_no_recipient_can_be_selected(tmp_path):
    response = client(tmp_path).post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": "hello", "priority": "important", "recipient": "someone-else"},
    )
    assert response.status_code == 422


def test_call_lifecycle_and_owner_signal(tmp_path):
    c = client(tmp_path)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = c.post(
        "/api/v1/calls",
        headers=headers,
        json={
            "reason": "check in",
            "priority": "important",
            "transport": "webrtc",
            "media_mode": "native-audio",
            "ttl": 300,
        },
    )
    assert response.status_code == 200
    session_id = response.json()["id"]
    accepted = c.post(
        f"/api/v1/sessions/{session_id}/transition", headers=headers, json={"state": "accepted"}
    )
    assert accepted.json()["state"] == "accepted"
    signal = c.post(
        f"/api/v1/sessions/{session_id}/signals",
        headers=headers,
        json={"sender": "self", "payload": {"type": "offer", "sdp": "placeholder"}},
    )
    assert signal.status_code == 200
    ended = c.post(f"/api/v1/sessions/{session_id}/end", headers=headers, json={})
    assert ended.json()["state"] == "ended"
