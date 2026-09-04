from __future__ import annotations

import secrets
import time

from .adapters import CommandAdapter, DisabledAdapter, FileAdapter, HttpHealthAdapter
from .config import Settings
from .models import TERMINAL_STATES, Priority, Session, SessionState
from .policy import Policy, PolicyDenied
from .store import Store


class CommsService:
    def __init__(self, settings: Settings, store: Store | None = None):
        self.settings = settings
        self.store = store or Store(settings.database)
        self.policy = Policy(settings, self.store)
        self.adapters = {
            "simplex": CommandAdapter(
                "simplex",
                settings.simplex_command,
                "SimpleX relay and recipient device",
                "set OLGAL_SIMPLEX_COMMAND after pairing the self contact",
            ),
            "terminalphone": FileAdapter(
                "terminalphone",
                settings.terminalphone_path,
                "Tor relays and peer endpoint",
                "set OLGAL_TERMINALPHONE_PATH to the reviewed fork entrypoint",
                ("tor", "opusenc", "sox", "socat", "arecord"),
            ),
            "sip": CommandAdapter(
                "sip",
                settings.baresip_command,
                "local SIP endpoint; no carrier configured",
                "install baresip and set OLGAL_BARESIP_COMMAND",
            ),
            "venice": DisabledAdapter(
                "venice",
                "set OLGAL_VENICE_BASE_URL to OlGal's local Aster bridge",
                "Venice API provider receives selected audio/text",
            )
            if not settings.venice_base_url
            else HttpHealthAdapter(
                "venice",
                settings.venice_base_url,
                "Aster enforces policy locally; selected audio/text then reaches Venice",
            ),
            "imessage": DisabledAdapter(
                "imessage",
                "requires Apple-branded hardware, supported macOS, and a user-created "
                "dedicated Apple Account",
                "Apple Messages and relay Mac",
            ),
            "pstn": DisabledAdapter(
                "pstn",
                "intentionally unfinished: requires carrier choice, credentials, number "
                "authorization, and spending policy",
                "future telecom carrier",
            ),
        }

    def status(self) -> dict[str, object]:
        return {
            "service": "olgal-comms",
            "recipient": "self",
            "emergency_enabled": self.settings.emergency_enabled,
            "adapters": {
                name: adapter.status().public() for name, adapter in self.adapters.items()
            },
        }

    def notify(self, capability, text: str, priority: Priority) -> dict[str, object]:
        self.policy.authorize(capability, "notify_self", priority)
        if self.policy.quiet_hours() and priority is Priority.ROUTINE:
            outcome = "quiet-hours"
            state = "queued"
        else:
            status = self.adapters["simplex"].status()
            if status.ready:
                try:
                    self.adapters["simplex"].notify_self(text, priority.value)
                    outcome, state = "allowed", "submitted"
                except RuntimeError:
                    outcome, state = "transport-error", "failed"
            else:
                outcome, state = "transport-unavailable", "transport-unavailable"
        event_id = secrets.token_urlsafe(12)
        self.store.audit(
            capability.subject,
            "notify_self",
            outcome,
            {
                "event_id": event_id,
                "priority": priority.value,
                "content_bytes": len(text.encode()),
                "state": state,
            },
        )
        return {"id": event_id, "recipient": "self", "state": state, "transport": "simplex"}

    def voice_note(self, capability, text: str, priority: Priority) -> dict[str, object]:
        self.policy.authorize(capability, "voice_note_self", priority)
        event_id = secrets.token_urlsafe(12)
        venice_ready = self.adapters["venice"].status().ready
        simplex_ready = self.adapters["simplex"].status().ready
        if venice_ready and simplex_ready:
            state = "confirmation-required"
        else:
            state = "transport-unavailable"
        self.store.audit(
            capability.subject,
            "voice_note_self",
            "allowed",
            {
                "event_id": event_id,
                "priority": priority.value,
                "content_bytes": len(text.encode()),
                "state": state,
            },
        )
        return {"id": event_id, "recipient": "self", "state": state, "transport": "venice+simplex"}

    def request_session(
        self,
        capability,
        kind: str,
        reason: str,
        priority: Priority,
        ttl: int,
        transport: str,
        media_mode: str | None = None,
    ) -> Session:
        action = "request_call_self" if kind == "call" else "request_attention"
        self.policy.authorize(capability, action, priority)
        if transport not in {"terminalphone", "sip", "webrtc", "simplex"}:
            raise PolicyDenied("transport is not allowed")
        now = time.time()
        state = SessionState.ACTIVE if priority is Priority.EMERGENCY else SessionState.REQUESTED
        session = Session(
            id=secrets.token_urlsafe(16),
            kind=kind,
            owner=capability.subject,
            state=state,
            priority=priority,
            created_at=now,
            expires_at=now + max(30, min(ttl, 3600)),
            transport=transport,
            media_mode=media_mode,
            reason_digest=None,
        )
        self.store.save_session(session)
        self.store.audit(
            capability.subject,
            action,
            "allowed",
            {
                "session_id": session.id,
                "priority": priority.value,
                "transport": transport,
                "reason_bytes": len(reason.encode("utf-8")),
            },
        )
        return session

    def get_session(self, capability, session_id: str) -> Session:
        session = self.store.get_session(session_id)
        may_manage_self = "manage_self_sessions" in capability.actions
        if not session or (session.owner != capability.subject and not may_manage_self):
            raise PolicyDenied("session not found for this capability")
        if session.state not in TERMINAL_STATES and session.expires_at <= time.time():
            session = (
                self.store.transition(
                    session.id,
                    SessionState.EXPIRED,
                    set(SessionState) - TERMINAL_STATES,
                )
                or self.store.get_session(session.id)
                or session
            )
        return session

    def list_owner_sessions(self, capability, limit: int = 20) -> list[Session]:
        if "manage_self_sessions" not in capability.actions:
            raise PolicyDenied("capability does not allow viewing the owner's Hearth")
        self.store.expire_sessions(time.time())
        return self.store.list_open_sessions(limit)

    def owner_decide(self, capability, session_id: str, state: SessionState) -> Session:
        if "manage_self_sessions" not in capability.actions:
            raise PolicyDenied("only the owner may answer or defer a request")
        if state not in {SessionState.ACCEPTED, SessionState.DEFERRED, SessionState.DECLINED}:
            raise ValueError("invalid owner decision")
        session = self.get_session(capability, session_id)
        allowed_from = {
            SessionState.REQUESTED,
            SessionState.NOTIFIED,
            SessionState.DEFERRED,
        }
        if session.state not in allowed_from:
            raise ValueError("request is no longer awaiting a decision")
        changed = self.store.transition(session_id, state, allowed_from)
        if changed is None:
            raise ValueError("request changed before the decision was saved")
        self.store.audit(
            capability.subject,
            "owner_decision",
            "allowed",
            {"session_id": session_id, "from": session.state.value, "to": state.value},
        )
        return changed

    def signaling_session(self, capability, session_id: str) -> tuple[Session, str]:
        session = self.get_session(capability, session_id)
        if session.kind != "call" or session.state not in {
            SessionState.ACCEPTED,
            SessionState.ACTIVE,
        }:
            raise PolicyDenied("signaling is unavailable until the owner accepts the call")
        sender = "self" if "manage_self_sessions" in capability.actions else "ai"
        return session, sender

    def add_signal(self, capability, session_id: str, payload: dict[str, object]) -> int:
        _session, sender = self.signaling_session(capability, session_id)
        return self.store.add_signal(session_id, sender, payload)

    def end_session(self, capability, session_id: str) -> Session:
        if (
            "end_call" not in capability.actions
            and "manage_self_sessions" not in capability.actions
        ):
            raise PolicyDenied("capability does not allow ending sessions")
        session = self.get_session(capability, session_id)
        if session.state in TERMINAL_STATES:
            return session
        ended = self.store.transition(
            session_id, SessionState.ENDED, set(SessionState) - TERMINAL_STATES
        )
        if ended is None:
            latest = self.store.get_session(session_id)
            if latest and latest.state in TERMINAL_STATES:
                return latest
            raise ValueError("session changed before it could be ended")
        self.store.audit(capability.subject, "end_call", "allowed", {"session_id": session_id})
        return ended
