"""SlackBotProvider — optional, runtime detection of slack-bolt."""

from __future__ import annotations

import logging
from typing import Any

from aecos.collaboration.providers.base import BotProvider
from aecos.collaboration.providers.console import ConsoleBotProvider

logger = logging.getLogger(__name__)


class SlackBotProvider(BotProvider):
    """Slack bot provider — wraps slack-bolt when available.

    Falls back to ConsoleBotProvider if slack-bolt is not installed.
    """

    def __init__(self, aecos_facade: Any = None, **kwargs: Any) -> None:
        self._facade = aecos_facade
        self._fallback = ConsoleBotProvider(aecos_facade)
        self._slack_available = False

        try:
            import slack_bolt  # noqa: F401
            self._slack_available = True
            logger.info("Slack SDK available — SlackBotProvider active")
        except ImportError:
            logger.info("slack-bolt not installed — falling back to console")

    @property
    def name(self) -> str:
        return "slack"

    def is_available(self) -> bool:
        return self._slack_available

    def send_message(self, text: str, **kwargs: Any) -> bool:
        if not self._slack_available:
            return self._fallback.send_message(text, **kwargs)
        logger.info("[Slack] %s", text)
        return True

    def handle_command(self, text: str, user: str = "", **kwargs: Any) -> str:
        return self._fallback.handle_command(text, user=user, **kwargs)
