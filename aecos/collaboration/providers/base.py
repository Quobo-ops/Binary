"""Abstract BotProvider interface."""

from __future__ import annotations

import abc
from typing import Any


class BotProvider(abc.ABC):
    """Base class for all bot providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is ready."""

    @abc.abstractmethod
    def send_message(self, text: str, **kwargs: Any) -> bool:
        """Send a message through this provider."""

    @abc.abstractmethod
    def handle_command(self, text: str, user: str = "", **kwargs: Any) -> str:
        """Handle an incoming command and return a response."""
