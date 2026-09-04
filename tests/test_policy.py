from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from olgal_comms.config import Settings
from olgal_comms.models import Capability, Priority, SessionState
from olgal_comms.policy import PolicyDenied
from olgal_comms.service import CommsService
from olgal_comms.store import SignalUnavailable


def settings(tmp_path: Path, *, emergency: bool = False) -> Settings:
    return Settings(
        database=tmp_path / "test.db",
        bind_host="127.0.0.1",
        bind_port=8765,
        public_base="/comms",
        tokens={},
        quiet_start=25,
        quiet_end=25,
        emergency_enabled=emergency,
        simplex_command=None,
        terminalphone_path=None,
        baresip_command=None,
        venice_base_url=None,
    )


def capability(*, emergency: bool = False, calls: int = 4) -> Capability:
    return Capability(
        subject="agent-one",
        actions=frozenset(
            {"notify_self", "voice_note_self", "request_attention", "request_call_self", "end_call"}
        ),
        emergency=emergency,
        calls_per_hour=calls,
    )


def test_status_is_honest_about_unavailable_transports(tmp_path):
    status = CommsService(settings(tmp_path)).status()
    assert status["recipient"] == "self"
    assert status["adapters"]["imessage"]["ready"] is False
    assert "Apple-branded hardware" in status["adapters"]["imessage"]["detail"]
    assert status["adapters"]["pstn"]["ready"] is False
    assert "intentionally unfinished" in status["adapters"]["pstn"]["detail"]


def test_emergency_is_disabled_even_when_model_claims_urgency(tmp_path):
    service = CommsService(settings(tmp_path, emergency=False))
    with pytest.raises(PolicyDenied, match="disabled or unprovisioned"):
        service.request_session(
            capability(emergency=True),
            "call",
            "model says emergency",
            Priority.EMERGENCY,
            300,
            "webrtc",
            "text-voice",
        )


def test_emergency_needs_separate_capability(tmp_path):
    service = CommsService(settings(tmp_path, emergency=True))
    with pytest.raises(PolicyDenied, match="disabled or unprovisioned"):
        service.request_session(
            capability(emergency=False),
            "call",
            "urgent",
            Priority.EMERGENCY,
            300,
            "webrtc",
            "text-voice",
        )


def test_session_owner_isolated(tmp_path):
    service = CommsService(settings(tmp_path))
    owner = capability()
    session = service.request_session(
        owner, "call", "talk", Priority.IMPORTANT, 300, "terminalphone", "native-audio"
    )
    stranger = Capability("agent-two", owner.actions)
    with pytest.raises(PolicyDenied, match="not found"):
        service.get_session(stranger, session.id)


def test_owner_browser_can_manage_but_not_send(tmp_path):
    service = CommsService(settings(tmp_path))
    ai = capability()
    session = service.request_session(
        ai, "call", "talk", Priority.IMPORTANT, 300, "webrtc", "native-audio"
    )
    browser = Capability("owner-browser", frozenset({"manage_self_sessions"}))
    assert service.get_session(browser, session.id).id == session.id
    with pytest.raises(PolicyDenied, match="does not allow notify_self"):
        service.notify(browser, "not allowed", Priority.IMPORTANT)


def test_reason_content_is_not_stored(tmp_path):
    service = CommsService(settings(tmp_path))
    secret_reason = "private words that must not enter metadata"
    session = service.request_session(
        capability(), "attention", secret_reason, Priority.IMPORTANT, 300, "simplex"
    )
    raw = (tmp_path / "test.db").read_bytes()
    assert secret_reason.encode() not in raw
    assert session.reason_digest is None


def test_call_rate_limit(tmp_path):
    service = CommsService(settings(tmp_path))
    cap = capability(calls=1)
    service.request_session(cap, "call", "one", Priority.IMPORTANT, 300, "sip")
    with pytest.raises(PolicyDenied, match="rate limit"):
        service.request_session(cap, "call", "two", Priority.IMPORTANT, 300, "sip")


def test_expired_session_transitions(tmp_path):
    service = CommsService(settings(tmp_path))
    cap = capability()
    session = service.request_session(cap, "call", "talk", Priority.IMPORTANT, 30, "webrtc")
    service.store._db.execute(
        "UPDATE sessions SET expires_at=? WHERE id=?", (time.time() - 1, session.id)
    )
    assert service.get_session(cap, session.id).state is SessionState.EXPIRED


def test_audit_contains_no_message_body(tmp_path):
    service = CommsService(settings(tmp_path))
    body = "this text must not be audited"
    service.notify(capability(), body, Priority.IMPORTANT)
    row = service.store._db.execute(
        "SELECT metadata FROM audit ORDER BY id DESC LIMIT 1"
    ).fetchone()
    metadata = json.loads(row["metadata"])
    assert body not in row["metadata"]
    assert metadata["content_bytes"] == len(body)


def test_signals_are_bounded_and_deleted_at_end(tmp_path):
    service = CommsService(settings(tmp_path))
    cap = capability()
    session = service.request_session(
        cap, "call", "talk", Priority.IMPORTANT, 300, "webrtc", "native-audio"
    )
    service.store.transition(session.id, SessionState.ACCEPTED, {SessionState.REQUESTED})
    service.store.add_signal(session.id, "ai", {"sdp": "small"})
    assert len(service.store.signals(session.id)) == 1
    with pytest.raises(ValueError, match="exceeds 32768 bytes"):
        service.store.add_signal(session.id, "ai", {"sdp": "x" * 32_769})
    service.store.transition(session.id, SessionState.ENDED)
    assert service.store.signals(session.id) == []


def test_signal_cannot_be_inserted_after_terminal_transition(tmp_path):
    service = CommsService(settings(tmp_path))
    cap = capability()
    session = service.request_session(
        cap, "call", "talk", Priority.IMPORTANT, 300, "webrtc", "native-audio"
    )
    service.store.transition(session.id, SessionState.ACCEPTED, {SessionState.REQUESTED})

    # Reproduce the old race: authorization observed ACCEPTED, then the call ended
    # before the signal write reached the Store.
    assert service.get_session(cap, session.id).state is SessionState.ACCEPTED
    service.end_session(cap, session.id)
    with pytest.raises(SignalUnavailable, match="no longer open"):
        service.store.add_signal(session.id, "ai", {"type": "ice"})
    assert service.store.signals(session.id) == []
