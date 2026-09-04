from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an OlGal Comms capability token")
    parser.add_argument("subject", nargs="?", default="trusted-ai")
    parser.add_argument(
        "--owner-browser", action="store_true", help="create a PWA management token"
    )
    parser.add_argument(
        "--store", type=Path, help="merge the capability into this mode-0600 JSON file"
    )
    parser.add_argument(
        "--token-output", type=Path, help="write the raw token to this mode-0600 file"
    )
    args = parser.parse_args()
    subject = args.subject
    token = secrets.token_urlsafe(32)
    actions = (
        ["manage_self_sessions"]
        if args.owner_browser
        else [
            "notify_self",
            "voice_note_self",
            "request_attention",
            "request_call_self",
            "end_call",
        ]
    )
    record = {
        token: {
            "subject": subject,
            "actions": actions,
            "emergency": False,
            "calls_per_hour": 4,
            "messages_per_hour": 30,
        }
    }
    if args.store:
        args.store.parent.mkdir(parents=True, exist_ok=True)
        current = json.loads(args.store.read_text()) if args.store.exists() else {}
        current.update(record)
        temporary = args.store.with_suffix(".tmp")
        temporary.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(args.store)
    if args.token_output:
        args.token_output.parent.mkdir(parents=True, exist_ok=True)
        args.token_output.write_text(token + "\n", encoding="utf-8")
        os.chmod(args.token_output, 0o600)
    if not args.store and not args.token_output:
        print(token)
        print(json.dumps(record, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
