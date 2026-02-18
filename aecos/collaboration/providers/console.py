"""ConsoleBotProvider — CLI-based interaction, always available."""

from __future__ import annotations

import logging
from typing import Any

from aecos.collaboration.providers.base import BotProvider

logger = logging.getLogger(__name__)


class ConsoleBotProvider(BotProvider):
    """Console-based bot provider.

    Always available. Routes text commands through the NL parser
    and returns formatted text responses.
    """

    def __init__(self, aecos_facade: Any = None) -> None:
        self._facade = aecos_facade

    @property
    def name(self) -> str:
        return "console"

    def is_available(self) -> bool:
        return True

    def send_message(self, text: str, **kwargs: Any) -> bool:
        """Send a message (log to console)."""
        logger.info("[Console Bot] %s", text)
        return True

    def handle_command(self, text: str, user: str = "", **kwargs: Any) -> str:
        """Handle a text command by routing through the AecOS facade.

        Parameters
        ----------
        text:
            Natural language command text.
        user:
            User who sent the command.

        Returns
        -------
        str
            Formatted response text.
        """
        if self._facade is None:
            return f"Received command from {user}: {text} (no AecOS instance configured)"

        try:
            # Parse the command through NL parser
            spec = self._facade.parse(text)
            response_parts = [
                f"Parsed command from {user}:",
                f"  Intent: {spec.intent}",
                f"  IFC Class: {spec.ifc_class}",
                f"  Confidence: {spec.confidence:.0%}",
            ]

            if spec.properties:
                response_parts.append(f"  Properties: {spec.properties}")
            if spec.materials:
                response_parts.append(f"  Materials: {spec.materials}")
            if spec.performance:
                response_parts.append(f"  Performance: {spec.performance}")

            # If it's a create intent, try to generate
            if spec.intent == "create" and spec.ifc_class:
                try:
                    folder = self._facade.generate(spec)
                    response_parts.append(f"  Generated: {folder.name}")
                except Exception as e:
                    response_parts.append(f"  Generation: skipped ({e})")

            return "\n".join(response_parts)

        except Exception as e:
            logger.debug("Command handling failed: %s", e, exc_info=True)
            return f"Error processing command: {e}"
