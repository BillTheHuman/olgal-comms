from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .base import Adapter, AdapterStatus


class CommandAdapter(Adapter):
    def __init__(self, name: str, command: str | None, boundary: str, setup: str):
        self.name = name
        self.command = command
        self.boundary = boundary
        self.setup = setup

    def status(self) -> AdapterStatus:
        ready = bool(self.command and shutil.which(self.command.split()[0]))
        return AdapterStatus(
            self.name,
            ready,
            "command detected" if ready else self.setup,
            self.boundary,
        )

    def notify_self(self, text: str, priority: str, link: str | None = None) -> str:
        if not self.status().ready or not self.command:
            return super().notify_self(text, priority, link)
        argv = self.command.split() + [priority, link or ""]
        # The command is operator-owned configuration and shell expansion is disabled.
        result = subprocess.run(  # noqa: S603
            argv,
            input=text,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
            shell=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{self.name} delivery command failed with exit {result.returncode}")
        return result.stdout.strip()[:200] or "submitted"


class FileAdapter(Adapter):
    def __init__(
        self,
        name: str,
        path: Path | None,
        boundary: str,
        setup: str,
        required_commands: tuple[str, ...] = (),
    ):
        self.name = name
        self.path = path
        self.boundary = boundary
        self.setup = setup
        self.required_commands = required_commands

    def status(self) -> AdapterStatus:
        path_ready = bool(self.path and self.path.is_file())
        missing = [name for name in self.required_commands if not shutil.which(name)]
        ready = path_ready and not missing
        if ready:
            detail = "entrypoint and required commands detected"
        elif missing:
            detail = f"missing commands: {', '.join(missing)}; {self.setup}"
        else:
            detail = self.setup
        return AdapterStatus(self.name, ready, detail, self.boundary)


class DisabledAdapter(Adapter):
    def __init__(self, name: str, reason: str, boundary: str):
        self.name = name
        self.reason = reason
        self.boundary = boundary

    def status(self) -> AdapterStatus:
        return AdapterStatus(self.name, False, self.reason, self.boundary)


class HttpHealthAdapter(Adapter):
    def __init__(self, name: str, base_url: str, boundary: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.boundary = boundary

    def status(self) -> AdapterStatus:
        if not self.base_url.startswith("http://127.0.0.1:"):
            return AdapterStatus(self.name, False, "health URL must use loopback", self.boundary)
        try:
            request = urllib.request.Request(f"{self.base_url}/health")  # noqa: S310
            with urllib.request.urlopen(request, timeout=2) as response:  # noqa: S310
                body = json.load(response)
            media = body.get("media", {})
            speech = media.get("operations", {}).get("speech_generation", {})
            ready = body.get("status") == "ok" and speech.get("enabled") is True
            detail = (
                "Aster speech broker is healthy; each generation still requires its policy gate"
                if ready
                else "Aster health did not confirm speech generation"
            )
            return AdapterStatus(self.name, ready, detail, self.boundary)
        except (OSError, ValueError, json.JSONDecodeError):
            return AdapterStatus(
                self.name, False, "Aster health endpoint unavailable", self.boundary
            )
