from __future__ import annotations

import time
from datetime import datetime

from .config import Settings
from .models import Capability, Priority
from .store import Store


class PolicyDenied(PermissionError):
    pass


class Policy:
    def __init__(self, settings: Settings, store: Store):
        self.settings = settings
        self.store = store

    def authenticate(self, token: str | None) -> Capability:
        if not token or token not in self.settings.tokens:
            raise PolicyDenied("missing or invalid capability token")
        capability = self.settings.tokens[token]
        if capability.expires_at is not None and capability.expires_at <= time.time():
            raise PolicyDenied("capability token expired")
        return capability

    def authorize(self, capability: Capability, action: str, priority: Priority) -> None:
        if action not in capability.actions:
            raise PolicyDenied(f"capability does not allow {action}")
        if priority is Priority.EMERGENCY:
            if not self.settings.emergency_enabled or not capability.emergency:
                raise PolicyDenied("emergency direct-ring is disabled or unprovisioned")
        limit = capability.calls_per_hour if "call" in action else capability.messages_per_hour
        if self.store.count_actions(capability.subject, action, time.time() - 3600) >= limit:
            raise PolicyDenied("hourly rate limit reached")

    def quiet_hours(self, now: datetime | None = None) -> bool:
        hour = (now or datetime.now()).hour
        start, end = self.settings.quiet_start, self.settings.quiet_end
        return hour >= start or hour < end if start > end else start <= hour < end
