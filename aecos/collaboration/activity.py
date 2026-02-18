"""ActivityFeed — aggregated event log across all collaboration modules."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aecos.collaboration.models import ActivityEvent

logger = logging.getLogger(__name__)


class ActivityFeed:
    """Aggregated activity feed stored in .aecos/activity.jsonl.

    Uses append-only JSONL format for efficient logging.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._feed_path = project_root / ".aecos" / "activity.jsonl"
        self._feed_path.parent.mkdir(parents=True, exist_ok=True)

    def record_event(self, event: ActivityEvent) -> None:
        """Record an event to the activity feed."""
        try:
            line = event.model_dump_json() + "\n"
            with open(self._feed_path, "a", encoding="utf-8") as f:
                f.write(line)
            logger.debug("Recorded event: %s (%s)", event.type, event.summary)
        except OSError:
            logger.debug("Failed to record event", exc_info=True)

    def get_feed(
        self,
        since: datetime | None = None,
        user: str | None = None,
        element_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get activity feed with optional filtering.

        Parameters
        ----------
        since:
            Only events after this timestamp.
        user:
            Filter by user.
        element_id:
            Filter by element.
        event_type:
            Filter by event type.
        limit:
            Maximum events to return.
        """
        if not self._feed_path.is_file():
            return []

        events: list[ActivityEvent] = []

        try:
            with open(self._feed_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = ActivityEvent.model_validate_json(line)
                        # Apply filters
                        if since and event.timestamp < since:
                            continue
                        if user and event.user != user:
                            continue
                        if element_id and event.element_id != element_id:
                            continue
                        if event_type and event.type != event_type:
                            continue
                        events.append(event)
                    except Exception:
                        continue
        except OSError:
            logger.debug("Failed to read activity feed", exc_info=True)

        # Return most recent events, capped at limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
