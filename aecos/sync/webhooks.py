"""Webhook dispatcher — routes events to configured notification providers."""

from __future__ import annotations

import logging
import time
from typing import Any

from aecos.sync.notifications import ConsoleNotifier, NotificationProvider

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Dispatch AEC OS events to all configured notification providers.

    Always includes a ConsoleNotifier as the default provider.
    """

    def __init__(self, providers: list[NotificationProvider] | None = None) -> None:
        self._console = ConsoleNotifier()
        self._providers: list[NotificationProvider] = [self._console]
        if providers:
            self._providers.extend(providers)

    def add_provider(self, provider: NotificationProvider) -> None:
        """Register an additional notification provider."""
        self._providers.append(provider)

    @property
    def console(self) -> ConsoleNotifier:
        """Access the built-in console notifier (useful for testing)."""
        return self._console

    def on_commit(
        self,
        user: str,
        element_id: str = "",
        branch: str = "",
        details: str = "",
    ) -> None:
        """Dispatch a commit event."""
        event = _make_event("commit", user, element_id, branch, details)
        self._dispatch(event)

    def on_conflict(
        self,
        user: str,
        element_id: str = "",
        branch: str = "",
        details: str = "",
    ) -> None:
        """Dispatch a conflict event."""
        event = _make_event("conflict", user, element_id, branch, details)
        self._dispatch(event)

    def on_lock(
        self,
        user: str,
        element_id: str = "",
        branch: str = "",
        details: str = "",
    ) -> None:
        """Dispatch a lock/unlock event."""
        event = _make_event("lock", user, element_id, branch, details)
        self._dispatch(event)

    def _dispatch(self, event: dict[str, Any]) -> None:
        """Send event to all available providers."""
        for provider in self._providers:
            if provider.is_available():
                try:
                    provider.notify(event)
                except Exception as exc:
                    logger.warning(
                        "Notification provider %s failed: %s",
                        type(provider).__name__,
                        exc,
                    )


def _make_event(
    event_type: str,
    user: str,
    element_id: str,
    branch: str,
    details: str,
) -> dict[str, Any]:
    """Build a standard event dict."""
    return {
        "type": event_type,
        "user": user,
        "element_id": element_id,
        "branch": branch,
        "timestamp": time.time(),
        "details": details,
    }
