"""TeamsBotProvider — optional, runtime detection of Teams SDK."""

from __future__ import annotations

import logging
from typing import Any

from aecos.collaboration.providers.base import BotProvider
from aecos.collaboration.providers.console import ConsoleBotProvider

logger = logging.getLogger(__name__)


class TeamsBotProvider(BotProvider):
    """Microsoft Teams bot provider.

    Falls back to ConsoleBotProvider if Teams SDK is not installed.
    """

    def __init__(self, aecos_facade: Any = None, **kwargs: Any) -> None:
        self._facade = aecos_facade
        self._fallback = ConsoleBotProvider(aecos_facade)
        self._teams_available = False

        try:
            import botbuilder.core  # noqa: F401
            self._teams_available = True
            logger.info("Teams SDK available — TeamsBotProvider active")
        except ImportError:
            logger.info("botbuilder-core not installed — falling back to console")

    @property
    def name(self) -> str:
        return "teams"

    def is_available(self) -> bool:
        return self._teams_available

    def send_message(self, text: str, **kwargs: Any) -> bool:
        if not self._teams_available:
            return self._fallback.send_message(text, **kwargs)
        logger.info("[Teams] %s", text)
        return True

    def handle_command(self, text: str, user: str = "", **kwargs: Any) -> str:
        return self._fallback.handle_command(text, user=user, **kwargs)
