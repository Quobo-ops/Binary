"""KPI models — Bible Section 8 success metrics."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from aecos.analytics.warehouse import DataWarehouse


class KPICalculator:
    """Calculate KPIs from the analytics data warehouse.

    Parameters
    ----------
    warehouse:
        DataWarehouse instance backed by the analytics database.
    """

    def __init__(self, warehouse: DataWarehouse) -> None:
        self.wh = warehouse

    def parse_accuracy(self) -> float:
        """Percentage of parses with confidence >= 0.85."""
        conn = self.wh._conn
        total = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='parser' AND event_type='parse_completed' AND value IS NOT NULL"
        ).fetchone()[0]
        if total == 0:
            return 0.0
        good = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='parser' AND event_type='parse_completed' AND value >= 0.85"
        ).fetchone()[0]
        return (good / total) * 100.0

    def template_reuse_rate(self) -> float:
        """Percentage of generations that used an existing template."""
        conn = self.wh._conn
        total_gen = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='generation' AND event_type='element_generated'"
        ).fetchone()[0]
        if total_gen == 0:
            return 0.0
        reuses = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='template' AND event_type='reuse_count'"
        ).fetchone()[0]
        return min((reuses / total_gen) * 100.0, 100.0)

    def avg_generation_time(self) -> float:
        """Mean generation duration in milliseconds."""
        return self.wh.average("generation", "element_generated")

    def compliance_pass_rate(self) -> float:
        """Percentage of compliance checks that passed."""
        conn = self.wh._conn
        total = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='compliance' AND event_type='check_completed' AND value IS NOT NULL"
        ).fetchone()[0]
        if total == 0:
            return 0.0
        passed = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='compliance' AND event_type='check_completed' AND value = 1.0"
        ).fetchone()[0]
        return (passed / total) * 100.0

    def cost_avoidance_estimate(
        self,
        avg_manual_hours: float = 4.0,
        hourly_rate: float = 85.0,
    ) -> float:
        """Estimated dollars saved: elements * avg_manual_hours * hourly_rate."""
        conn = self.wh._conn
        total_elements = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='generation' AND event_type='element_generated'"
        ).fetchone()[0]
        return total_elements * avg_manual_hours * hourly_rate

    def active_users(self, days: int = 30) -> int:
        """Distinct users in the last N days."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return self.wh.distinct_users(since=since)

    def elements_generated(self, since: str | None = None) -> int:
        """Count of elements generated."""
        return self.wh.count("generation", "element_generated", since=since)

    def collaboration_engagement(self) -> float:
        """Average comments + tasks + reviews per user per week."""
        conn = self.wh._conn
        # Total collab events
        total = conn.execute(
            "SELECT COUNT(*) FROM events WHERE module='collaboration'"
        ).fetchone()[0]
        users = self.wh.distinct_users()
        if users == 0:
            return 0.0
        # Assume we look at all time; weekly = total / users / (weeks)
        # Simplified: just total / users as engagement score
        return total / users

    def all_kpis(self) -> dict[str, Any]:
        """Return all KPIs as a dict."""
        return {
            "parse_accuracy": round(self.parse_accuracy(), 2),
            "template_reuse_rate": round(self.template_reuse_rate(), 2),
            "avg_generation_time_ms": round(self.avg_generation_time(), 2),
            "compliance_pass_rate": round(self.compliance_pass_rate(), 2),
            "cost_avoidance_usd": round(self.cost_avoidance_estimate(), 2),
            "active_users_30d": self.active_users(),
            "elements_generated": self.elements_generated(),
            "collaboration_engagement": round(self.collaboration_engagement(), 2),
        }
