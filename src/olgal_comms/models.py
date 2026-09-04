from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Priority(StrEnum):
    ROUTINE = "routine"
    IMPORTANT = "important"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class SessionState(StrEnum):
    REQUESTED = "requested"
    NOTIFIED = "notified"
    DEFERRED = "deferred"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    DECLINED = "declined"
    EXPIRED = "expired"
    ENDED = "ended"
    FAILED = "failed"


TERMINAL_STATES = {
    SessionState.DECLINED,
    SessionState.EXPIRED,
    SessionState.ENDED,
    SessionState.FAILED,
}


@dataclass(frozen=True)
class Capability:
    subject: str
    actions: frozenset[str]
    expires_at: float | None = None
    emergency: bool = False
    calls_per_hour: int = 4
    messages_per_hour: int = 30


@dataclass
class Session:
    id: str
    kind: str
    owner: str
    state: SessionState
    priority: Priority
    created_at: float
    expires_at: float
    transport: str
    media_mode: str | None = None
    reason_digest: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "transport": self.transport,
            "media_mode": self.media_mode,
        }

    def owner_summary(self) -> dict[str, Any]:
        """Return only the session fields the owner's Hearth needs."""
        return {
            "id": self.id,
            "kind": self.kind,
            "source": self.owner,
            "state": self.state.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "media_mode": self.media_mode,
        }
