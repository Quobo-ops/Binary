"""DataWarehouse — SQLite metrics storage and aggregation."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class DataWarehouse:
    """Aggregation and query layer on top of the metrics database.

    Parameters
    ----------
    conn:
        An existing sqlite3 connection (shared with MetricsCollector).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def aggregate(
        self,
        module: str,
        event_type: str,
        period: str = "day",
    ) -> list[tuple[str, float]]:
        """Aggregate event values by time period.

        Parameters
        ----------
        period:
            ``'day'``, ``'week'``, or ``'month'``.

        Returns list of (period_label, aggregate_value) tuples.
        """
        if period == "day":
            fmt = "%Y-%m-%d"
            trunc = "substr(timestamp, 1, 10)"
        elif period == "week":
            fmt = "%Y-W%W"
            trunc = "strftime('%Y-W%W', timestamp)"
        else:
            fmt = "%Y-%m"
            trunc = "substr(timestamp, 1, 7)"

        sql = (
            f"SELECT {trunc} AS p, COALESCE(SUM(value), COUNT(*)) "
            f"FROM events WHERE module = ? AND event_type = ? "
            f"GROUP BY p ORDER BY p"
        )
        rows = self._conn.execute(sql, (module, event_type)).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    def count(
        self,
        module: str,
        event_type: str,
        since: str | None = None,
    ) -> int:
        """Count events matching the criteria."""
        sql = "SELECT COUNT(*) FROM events WHERE module = ? AND event_type = ?"
        params: list[Any] = [module, event_type]
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    def average(
        self,
        module: str,
        event_type: str,
        since: str | None = None,
    ) -> float:
        """Average of event values."""
        sql = "SELECT AVG(value) FROM events WHERE module = ? AND event_type = ? AND value IS NOT NULL"
        params: list[Any] = [module, event_type]
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        row = self._conn.execute(sql, params).fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0

    def trend(
        self,
        module: str,
        event_type: str,
        periods: int = 12,
    ) -> list[tuple[str, float]]:
        """Recent trend data — last N months.

        Returns list of (period_label, value) tuples.
        """
        # Get all monthly aggregates and return last N
        all_data = self.aggregate(module, event_type, period="month")
        return all_data[-periods:]

    def top_templates(self, limit: int = 10) -> list[tuple[str, int]]:
        """Most-reused templates by event count."""
        sql = (
            "SELECT json_extract(metadata_json, '$.template_id') AS tid, COUNT(*) AS cnt "
            "FROM events WHERE module = 'template' AND event_type = 'reuse_count' "
            "AND tid IS NOT NULL GROUP BY tid ORDER BY cnt DESC LIMIT ?"
        )
        rows = self._conn.execute(sql, (limit,)).fetchall()
        return [(r[0], r[1]) for r in rows]

    def distinct_users(self, since: str | None = None) -> int:
        """Count distinct active users."""
        sql = "SELECT COUNT(DISTINCT user) FROM events WHERE user != ''"
        params: list[Any] = []
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else 0
