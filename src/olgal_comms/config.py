from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models import Capability


@dataclass(frozen=True)
class Settings:
    database: Path
    bind_host: str
    bind_port: int
    public_base: str
    tokens: dict[str, Capability]
    quiet_start: int
    quiet_end: int
    emergency_enabled: bool
    simplex_command: str | None
    terminalphone_path: Path | None
    baresip_command: str | None
    venice_base_url: str | None

    @classmethod
    def from_env(cls) -> Settings:
        token_data = json.loads(os.getenv("OLGAL_TOKENS_JSON", "{}"))
        token_file = os.getenv("OLGAL_TOKENS_FILE")
        if token_file:
            token_data.update(json.loads(Path(token_file).read_text(encoding="utf-8")))
        tokens: dict[str, Capability] = {}
        for token, raw in token_data.items():
            tokens[token] = Capability(
                subject=raw["subject"],
                actions=frozenset(raw.get("actions", [])),
                expires_at=raw.get("expires_at"),
                emergency=bool(raw.get("emergency", False)),
                calls_per_hour=int(raw.get("calls_per_hour", 4)),
                messages_per_hour=int(raw.get("messages_per_hour", 30)),
            )
        default_db = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local/state"))
        return cls(
            database=Path(os.getenv("OLGAL_DATABASE", default_db / "olgal-comms/comms.db")),
            bind_host=os.getenv("OLGAL_BIND_HOST", "127.0.0.1"),
            bind_port=int(os.getenv("OLGAL_BIND_PORT", "8791")),
            public_base=os.getenv("OLGAL_PUBLIC_BASE", "/comms"),
            tokens=tokens,
            quiet_start=int(os.getenv("OLGAL_QUIET_START", "22")),
            quiet_end=int(os.getenv("OLGAL_QUIET_END", "7")),
            emergency_enabled=os.getenv("OLGAL_EMERGENCY_ENABLED", "false").lower() == "true",
            simplex_command=os.getenv("OLGAL_SIMPLEX_COMMAND"),
            terminalphone_path=(
                Path(os.environ["OLGAL_TERMINALPHONE_PATH"])
                if os.getenv("OLGAL_TERMINALPHONE_PATH")
                else None
            ),
            baresip_command=os.getenv("OLGAL_BARESIP_COMMAND"),
            venice_base_url=os.getenv("OLGAL_VENICE_BASE_URL"),
        )
