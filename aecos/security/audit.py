"""AuditLogger — immutable, hash-chained event log backed by SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aecos.security.hasher import Hasher

logger = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    user        TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    resource    TEXT    NOT NULL DEFAULT '',
    before_hash TEXT    NOT NULL DEFAULT '',
    after_hash  TEXT    NOT NULL DEFAULT '',
    entry_hash  TEXT    NOT NULL,
    prev_entry_hash TEXT NOT NULL DEFAULT ''
);
"""


class AuditEntry(BaseModel):
    """Single immutable audit record."""

    id: int = 0
    timestamp: str = ""
    user: str = ""
    action: str = ""
    resource: str = ""
    before_hash: str = ""
    after_hash: str = ""
    entry_hash: str = ""
    prev_entry_hash: str = ""


class AuditLogger:
    """Append-only, hash-chained audit log stored in SQLite.

    Parameters
    ----------
    db_path:
        Path to the SQLite file.  Defaults to ``':memory:'``.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log(
        self,
        user: str,
        action: str,
        resource: str = "",
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> AuditEntry:
        """Append an event and return the created AuditEntry."""
        ts = datetime.now(timezone.utc).isoformat()
        bh = before_hash or ""
        ah = after_hash or ""

        prev = self._last_hash()

        entry_hash = Hasher.hash_string(
            f"{ts}{user}{action}{resource}{bh}{ah}{prev}"
        )

        cur = self._conn.execute(
            "INSERT INTO audit_log "
            "(timestamp, user, action, resource, before_hash, after_hash, "
            "entry_hash, prev_entry_hash) VALUES (?,?,?,?,?,?,?,?)",
            (ts, user, action, resource, bh, ah, entry_hash, prev),
        )
        self._conn.commit()

        return AuditEntry(
            id=cur.lastrowid or 0,
            timestamp=ts,
            user=user,
            action=action,
            resource=resource,
            before_hash=bh,
            after_hash=ah,
            entry_hash=entry_hash,
            prev_entry_hash=prev,
        )

    def verify_chain(self) -> bool:
        """Validate the entire hash chain.  Returns False if tampered."""
        rows = self._conn.execute(
            "SELECT id, timestamp, user, action, resource, before_hash, "
            "after_hash, entry_hash, prev_entry_hash "
            "FROM audit_log ORDER BY id"
        ).fetchall()

        prev_hash = ""
        for row in rows:
            (
                _id, ts, user, action, resource,
                bh, ah, stored_hash, stored_prev,
            ) = row

            if stored_prev != prev_hash:
                return False

            expected = Hasher.hash_string(
                f"{ts}{user}{action}{resource}{bh}{ah}{prev_hash}"
            )
            if expected != stored_hash:
                return False

            prev_hash = stored_hash

        return True

    def get_log(
        self,
        resource: str | None = None,
        user: str | None = None,
        action: str | None = None,
        since: str | None = None,
    ) -> list[AuditEntry]:
        """Query the audit log with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if resource is not None:
            clauses.append("resource = ?")
            params.append(resource)
        if user is not None:
            clauses.append("user = ?")
            params.append(user)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT id,timestamp,user,action,resource,before_hash,after_hash,entry_hash,prev_entry_hash FROM audit_log{where} ORDER BY id"

        rows = self._conn.execute(sql, params).fetchall()
        return [
            AuditEntry(
                id=r[0], timestamp=r[1], user=r[2], action=r[3],
                resource=r[4], before_hash=r[5], after_hash=r[6],
                entry_hash=r[7], prev_entry_hash=r[8],
            )
            for r in rows
        ]

    def export_log(self, format: str = "json") -> str:
        """Export the full audit trail as JSON."""
        entries = self.get_log()
        data = [e.model_dump() for e in entries]
        return json.dumps(data, indent=2)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else ""

    def close(self) -> None:
        self._conn.close()
