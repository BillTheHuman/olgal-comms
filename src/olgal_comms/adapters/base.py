from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AdapterStatus:
    name: str
    ready: bool
    detail: str
    privacy_boundary: str

    def public(self) -> dict[str, object]:
        return asdict(self)


class Adapter:
    name = "adapter"

    def status(self) -> AdapterStatus:
        raise NotImplementedError

    def notify_self(self, text: str, priority: str, link: str | None = None) -> str:
        raise RuntimeError(f"{self.name} adapter is not ready")
