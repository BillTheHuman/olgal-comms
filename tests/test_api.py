from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from olgal_comms.api import create_app
from olgal_comms.config import Settings
from olgal_comms.models import Capability, SessionState

TOKEN = "test-token"
OWNER_TOKEN = "owner-token"


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
        tokens={
            TOKEN: cap,
            OWNER_TOKEN: Capability(
                subject="owner-browser", actions=frozenset({"manage_self_sessions"})
            ),
        },
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


def test_hearth_response_cannot_be_framed(tmp_path):
    response = client(tmp_path).get("/")
    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in policy
    assert "connect-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy


def test_no_recipient_can_be_selected(tmp_path):
    response = client(tmp_path).post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"text": "hello", "priority": "important", "recipient": "someone-else"},
    )
    assert response.status_code == 422


def test_call_lifecycle_and_owner_signal(tmp_path):
    c = client(tmp_path)
    ai_headers = {"Authorization": f"Bearer {TOKEN}"}
    owner_headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    response = c.post(
        "/api/v1/calls",
        headers=ai_headers,
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
    forbidden = c.post(
        f"/api/v1/sessions/{session_id}/transition",
        headers=ai_headers,
        json={"state": "accepted"},
    )
    assert forbidden.status_code == 403

    pre_accept_signal = c.post(
        f"/api/v1/sessions/{session_id}/signals",
        headers=ai_headers,
        json={"payload": {"type": "offer", "sdp": "placeholder"}},
    )
    assert pre_accept_signal.status_code == 403

    accepted = c.post(
        f"/api/v1/sessions/{session_id}/transition",
        headers=owner_headers,
        json={"state": "accepted"},
    )
    assert accepted.json()["state"] == "accepted"
    signal = c.post(
        f"/api/v1/sessions/{session_id}/signals",
        headers=owner_headers,
        json={"payload": {"type": "offer", "sdp": "placeholder"}},
    )
    assert signal.status_code == 200
    received = c.get(f"/api/v1/sessions/{session_id}/signals", headers=ai_headers)
    assert received.json()["signals"][0]["sender"] == "self"
    spoofed = c.post(
        f"/api/v1/sessions/{session_id}/signals",
        headers=ai_headers,
        json={"sender": "self", "payload": {"type": "answer"}},
    )
    assert spoofed.status_code == 422
    ended = c.post(f"/api/v1/sessions/{session_id}/end", headers=ai_headers, json={})
    assert ended.json()["state"] == "ended"


def test_signal_write_conflicts_if_call_ends_after_eligibility_check(tmp_path, monkeypatch):
    c = client(tmp_path)
    ai_headers = {"Authorization": f"Bearer {TOKEN}"}
    owner_headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    created = c.post(
        "/api/v1/calls",
        headers=ai_headers,
        json={"reason": "race", "priority": "important", "ttl": 300},
    ).json()
    session_id = created["id"]
    c.post(
        f"/api/v1/sessions/{session_id}/transition",
        headers=owner_headers,
        json={"state": "accepted"},
    )

    store = c.app.state.service.store
    original_add_signal = store.add_signal

    def end_before_insert(signal_session_id, sender, payload):
        store.transition(
            signal_session_id,
            SessionState.ENDED,
            {SessionState.ACCEPTED, SessionState.ACTIVE},
        )
        return original_add_signal(signal_session_id, sender, payload)

    monkeypatch.setattr(store, "add_signal", end_before_insert)
    response = c.post(
        f"/api/v1/sessions/{session_id}/signals",
        headers=owner_headers,
        json={"payload": {"type": "offer", "sdp": "placeholder"}},
    )

    assert response.status_code == 409
    assert store.get_session(session_id).state is SessionState.ENDED
    assert store.signals(session_id) == []


def test_owner_can_list_pending_sessions_without_private_reason(tmp_path):
    c = client(tmp_path)
    ai_headers = {"Authorization": f"Bearer {TOKEN}"}
    owner_headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    created = c.post(
        "/api/v1/calls",
        headers=ai_headers,
        json={
            "reason": "private words",
            "priority": "important",
            "transport": "webrtc",
            "media_mode": "native-audio",
            "ttl": 300,
        },
    )
    assert created.status_code == 200

    forbidden = c.get("/api/v1/inbox", headers=ai_headers)
    assert forbidden.status_code == 403

    response = c.get("/api/v1/inbox", headers=owner_headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    sessions = response.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["source"] == "test-ai"
    assert "reason_digest" not in sessions[0]
    assert "transport" not in sessions[0]
    assert "private words" not in response.text


def test_owner_can_defer_but_stale_decisions_conflict(tmp_path):
    c = client(tmp_path)
    ai_headers = {"Authorization": f"Bearer {TOKEN}"}
    owner_headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    created = c.post(
        "/api/v1/calls",
        headers=ai_headers,
        json={"reason": "later", "priority": "routine", "ttl": 300},
    )
    session_id = created.json()["id"]
    deferred = c.post(
        f"/api/v1/sessions/{session_id}/transition",
        headers=owner_headers,
        json={"state": "deferred"},
    )
    assert deferred.status_code == 200
    assert deferred.json()["state"] == "deferred"

    accepted = c.post(
        f"/api/v1/sessions/{session_id}/transition",
        headers=owner_headers,
        json={"state": "accepted"},
    )
    assert accepted.status_code == 200
    stale = c.post(
        f"/api/v1/sessions/{session_id}/transition",
        headers=owner_headers,
        json={"state": "declined"},
    )
    assert stale.status_code == 409


def test_inbox_excludes_ended_and_expired_sessions(tmp_path):
    c = client(tmp_path)
    ai_headers = {"Authorization": f"Bearer {TOKEN}"}
    owner_headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    ended = c.post(
        "/api/v1/calls",
        headers=ai_headers,
        json={"reason": "end me", "priority": "routine", "ttl": 300},
    ).json()
    c.post(f"/api/v1/sessions/{ended['id']}/end", headers=ai_headers, json={})
    expiring = c.post(
        "/api/v1/calls",
        headers=ai_headers,
        json={"reason": "expire me", "priority": "routine", "ttl": 30},
    ).json()
    c.app.state.service.store._db.execute(
        "UPDATE sessions SET expires_at=0 WHERE id=?", (expiring["id"],)
    )
    response = c.get("/api/v1/inbox", headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == {"sessions": []}
