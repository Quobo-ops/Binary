"""UpdateScheduler — periodic check scheduling using threading.Timer."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class UpdateScheduler:
    """Schedule periodic regulatory update checks.

    Uses threading.Timer for background checks — no external scheduler
    dependencies required.
    """

    def __init__(
        self,
        check_callback: Callable[[], Any] | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._callback = check_callback
        self._project_root = project_root
        self._timer: threading.Timer | None = None
        self._running = False
        self._interval_hours: float = 168  # weekly default
        self._state_path: Path | None = None
        if project_root:
            state_dir = project_root / ".aecos"
            state_dir.mkdir(parents=True, exist_ok=True)
            self._state_path = state_dir / "regulatory_schedule.json"

    @property
    def is_running(self) -> bool:
        return self._running

    def schedule_check(self, interval_hours: float = 168) -> None:
        """Start the periodic check schedule.

        Parameters
        ----------
        interval_hours:
            Check interval in hours (default 168 = weekly).
        """
        self._interval_hours = interval_hours
        self._running = True
        self._save_state()
        self._schedule_next()
        logger.info("Scheduled regulatory checks every %.1f hours", interval_hours)

    def stop(self) -> None:
        """Stop the periodic schedule."""
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._save_state()
        logger.info("Stopped regulatory check schedule")

    def check_now(self) -> Any:
        """Execute an immediate check."""
        logger.info("Executing immediate regulatory check")
        self._update_last_checked()
        if self._callback:
            return self._callback()
        return None

    def _schedule_next(self) -> None:
        """Schedule the next check using threading.Timer."""
        if not self._running:
            return

        interval_seconds = self._interval_hours * 3600
        self._timer = threading.Timer(interval_seconds, self._run_check)
        self._timer.daemon = True
        self._timer.start()

    def _run_check(self) -> None:
        """Execute check and reschedule."""
        if not self._running:
            return
        try:
            self._update_last_checked()
            if self._callback:
                self._callback()
        except Exception:
            logger.debug("Scheduled check failed", exc_info=True)
        finally:
            self._schedule_next()

    def _update_last_checked(self) -> None:
        """Update the last checked timestamp in state."""
        self._save_state()

    def _save_state(self) -> None:
        """Persist schedule state to .aecos/regulatory_schedule.json."""
        if self._state_path is None:
            return
        state = {
            "interval_hours": self._interval_hours,
            "running": self._running,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError:
            logger.debug("Failed to save schedule state", exc_info=True)

    def _load_state(self) -> dict[str, Any]:
        """Load schedule state from disk."""
        if self._state_path is None or not self._state_path.is_file():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
