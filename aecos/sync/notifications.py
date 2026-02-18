"""Notification providers — console, Slack, Teams, Discord."""

from __future__ import annotations

import abc
import logging
from typing import Any

logger = logging.getLogger(__name__)


class NotificationProvider(abc.ABC):
    """Abstract notification provider."""

    @abc.abstractmethod
    def notify(self, event: dict[str, Any]) -> bool:
        """Send a notification about an event.

        Parameters
        ----------
        event:
            Event dict with keys: type, user, element_id, branch,
            timestamp, details.

        Returns True if notification was sent successfully.
        """

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if provider is ready to send."""


class ConsoleNotifier(NotificationProvider):
    """Always-available console/log notification provider."""

    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []

    def notify(self, event: dict[str, Any]) -> bool:
        self._log.append(event)
        event_type = event.get("type", "unknown")
        user = event.get("user", "unknown")
        element_id = event.get("element_id", "")
        details = event.get("details", "")
        msg = f"[AEC OS] {event_type}: user={user} element={element_id} {details}"
        logger.info(msg)
        return True

    def is_available(self) -> bool:
        return True

    @property
    def log(self) -> list[dict[str, Any]]:
        """Access the in-memory log for testing."""
        return list(self._log)


class SlackNotifier(NotificationProvider):
    """Slack webhook notification provider. Optional."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self._webhook_url = webhook_url

    def is_available(self) -> bool:
        if not self._webhook_url:
            return False
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def notify(self, event: dict[str, Any]) -> bool:
        if not self.is_available():
            logger.warning("Slack notifier unavailable, skipping.")
            return False

        try:
            import requests

            payload = {"text": _format_event(event)}
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Slack notification failed: %s", exc)
            return False


class TeamsNotifier(NotificationProvider):
    """Microsoft Teams webhook notification provider. Optional."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self._webhook_url = webhook_url

    def is_available(self) -> bool:
        if not self._webhook_url:
            return False
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def notify(self, event: dict[str, Any]) -> bool:
        if not self.is_available():
            logger.warning("Teams notifier unavailable, skipping.")
            return False

        try:
            import requests

            payload = {"text": _format_event(event)}
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("Teams notification failed: %s", exc)
            return False


class DiscordNotifier(NotificationProvider):
    """Discord webhook notification provider. Optional."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self._webhook_url = webhook_url

    def is_available(self) -> bool:
        if not self._webhook_url:
            return False
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def notify(self, event: dict[str, Any]) -> bool:
        if not self.is_available():
            logger.warning("Discord notifier unavailable, skipping.")
            return False

        try:
            import requests

            payload = {"content": _format_event(event)}
            resp = requests.post(self._webhook_url, json=payload, timeout=10)
            return resp.status_code in (200, 204)
        except Exception as exc:
            logger.warning("Discord notification failed: %s", exc)
            return False


def _format_event(event: dict[str, Any]) -> str:
    """Format an event dict into a readable notification message."""
    event_type = event.get("type", "unknown")
    user = event.get("user", "unknown")
    element_id = event.get("element_id", "")
    branch = event.get("branch", "")
    details = event.get("details", "")

    parts = [f"AEC OS {event_type}"]
    if user:
        parts.append(f"by {user}")
    if element_id:
        parts.append(f"on {element_id}")
    if branch:
        parts.append(f"(branch: {branch})")
    if details:
        parts.append(f"— {details}")

    return " ".join(parts)
