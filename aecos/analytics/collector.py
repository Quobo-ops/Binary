"""MetricsCollector — event recording hooks for all modules."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT    NOT NULL,
    module         TEXT    NOT NULL,
    event_type     TEXT    NOT NULL,
    value          REAL,
    metadata_json  TEXT    NOT NULL DEFAULT '{}',
    user           TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_module ON events(module);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
"""


class MetricsCollector:
    """Record events from all AEC OS modules into an SQLite database.

    Parameters
    ----------
    db_path:
        Path to analytics.db.  Defaults to ``':memory:'``.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def record(
        self,
        module: str,
        event_type: str,
        value: float | None = None,
        metadata: dict[str, Any] | None = None,
        user: str = "",
    ) -> int:
        """Record an analytics event.

        Returns the event id.
        """
        ts = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {})

        cur = self._conn.execute(
            "INSERT INTO events (timestamp, module, event_type, value, metadata_json, user) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts, module, event_type, value, meta_json, user),
        )
        self._conn.commit()
        return cur.lastrowid or 0

    def get_events(
        self,
        module: str | None = None,
        event_type: str | None = None,
        since: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query events with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if module:
            clauses.append("module = ?")
            params.append(module)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT id,timestamp,module,event_type,value,metadata_json,user FROM events{where} ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "module": r[2],
                "event_type": r[3],
                "value": r[4],
                "metadata_json": r[5],
                "user": r[6],
            }
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
