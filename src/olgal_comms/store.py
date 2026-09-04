from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .models import Priority, Session, SessionState


class SignalUnavailable(RuntimeError):
    """Raised when a call cannot accept signaling in its current state."""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._db.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, owner TEXT NOT NULL,
              state TEXT NOT NULL, priority TEXT NOT NULL, created_at REAL NOT NULL,
              expires_at REAL NOT NULL, transport TEXT NOT NULL,
              media_mode TEXT, reason_digest TEXT
            );
            CREATE TABLE IF NOT EXISTS signals (
              id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
              sender TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at REAL NOT NULL,
              subject TEXT NOT NULL, action TEXT NOT NULL, outcome TEXT NOT NULL,
              metadata TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS audit_subject_time ON audit(subject, occurred_at);
            CREATE INDEX IF NOT EXISTS signals_session_id ON signals(session_id, id);
            """
        )

    def save_session(self, session: Session) -> None:
        with self._lock, self._db:
            self._db.execute(
                """INSERT OR REPLACE INTO sessions
                (id,kind,owner,state,priority,created_at,expires_at,transport,media_mode,reason_digest)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    session.id,
                    session.kind,
                    session.owner,
                    session.state.value,
                    session.priority.value,
                    session.created_at,
                    session.expires_at,
                    session.transport,
                    session.media_mode,
                    session.reason_digest,
                ),
            )

    def get_session(self, session_id: str) -> Session | None:
        row = self._db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        return self._session_from_row(row)

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            kind=row["kind"],
            owner=row["owner"],
            state=SessionState(row["state"]),
            priority=Priority(row["priority"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            transport=row["transport"],
            media_mode=row["media_mode"],
            reason_digest=row["reason_digest"],
        )

    def list_sessions(self, limit: int = 20) -> list[Session]:
        rows = self._db.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def list_open_sessions(self, limit: int = 20) -> list[Session]:
        rows = self._db.execute(
            "SELECT * FROM sessions WHERE state IN (?,?,?,?,?) ORDER BY created_at DESC LIMIT ?",
            (
                SessionState.REQUESTED.value,
                SessionState.NOTIFIED.value,
                SessionState.DEFERRED.value,
                SessionState.ACCEPTED.value,
                SessionState.ACTIVE.value,
                limit,
            ),
        ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def transition(
        self,
        session_id: str,
        state: SessionState,
        allowed_from: set[SessionState] | None = None,
    ) -> Session | None:
        with self._lock, self._db:
            row = self._db.execute(
                "SELECT state FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            if not row:
                return None
            current = SessionState(row["state"])
            if allowed_from and current not in allowed_from:
                return None
            cursor = self._db.execute(
                "UPDATE sessions SET state=? WHERE id=? AND state=?",
                (state.value, session_id, current.value),
            )
            if cursor.rowcount != 1:
                return None
            if state in {
                SessionState.DECLINED,
                SessionState.ENDED,
                SessionState.EXPIRED,
                SessionState.FAILED,
            }:
                self._db.execute("DELETE FROM signals WHERE session_id = ?", (session_id,))
        return self.get_session(session_id)

    def expire_sessions(self, now: float) -> None:
        with self._lock, self._db:
            rows = self._db.execute(
                "SELECT id,state FROM sessions WHERE expires_at<=?", (now,)
            ).fetchall()
            for row in rows:
                current = SessionState(row["state"])
                if current in {
                    SessionState.DECLINED,
                    SessionState.EXPIRED,
                    SessionState.ENDED,
                    SessionState.FAILED,
                }:
                    continue
                cursor = self._db.execute(
                    "UPDATE sessions SET state=? WHERE id=? AND state=?",
                    (SessionState.EXPIRED.value, row["id"], current.value),
                )
                if cursor.rowcount == 1:
                    self._db.execute("DELETE FROM signals WHERE session_id=?", (row["id"],))

    def count_actions(self, subject: str, action: str, since: float) -> int:
        row = self._db.execute(
            "SELECT COUNT(*) AS n FROM audit WHERE subject=? AND action=? "
            "AND occurred_at>=? AND outcome='allowed'",
            (subject, action, since),
        ).fetchone()
        return int(row["n"])

    def audit(self, subject: str, action: str, outcome: str, metadata: dict[str, Any]) -> None:
        safe = {
            k: v for k, v in metadata.items() if k not in {"text", "reason", "audio", "payload"}
        }
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO audit(occurred_at,subject,action,outcome,metadata) VALUES(?,?,?,?,?)",
                (time.time(), subject, action, outcome, json.dumps(safe, sort_keys=True)),
            )

    def add_signal(self, session_id: str, sender: str, payload: dict[str, Any]) -> int:
        encoded = json.dumps(payload, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > 32_768:
            raise ValueError("signal payload exceeds 32768 bytes")
        with self._lock, self._db:
            now = time.time()
            cursor = self._db.execute(
                """INSERT INTO signals(session_id,sender,payload,created_at)
                SELECT id,?,?,? FROM sessions
                WHERE id=? AND kind='call' AND state IN (?,?) AND expires_at>?""",
                (
                    sender,
                    encoded,
                    now,
                    session_id,
                    SessionState.ACCEPTED.value,
                    SessionState.ACTIVE.value,
                    now,
                ),
            )
            if cursor.rowcount != 1:
                expired = self._db.execute(
                    """UPDATE sessions SET state=?
                    WHERE id=? AND state NOT IN (?,?,?,?) AND expires_at<=?""",
                    (
                        SessionState.EXPIRED.value,
                        session_id,
                        SessionState.DECLINED.value,
                        SessionState.EXPIRED.value,
                        SessionState.ENDED.value,
                        SessionState.FAILED.value,
                        now,
                    ),
                )
                if expired.rowcount == 1:
                    self._db.execute("DELETE FROM signals WHERE session_id=?", (session_id,))
                raise SignalUnavailable("call is no longer open for signaling")
            return int(cursor.lastrowid)

    def signals(self, session_id: str, after: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT id,sender,payload,created_at FROM signals "
            "WHERE session_id=? AND id>? ORDER BY id LIMIT ?",
            (session_id, after, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "sender": r["sender"],
                "payload": json.loads(r["payload"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
