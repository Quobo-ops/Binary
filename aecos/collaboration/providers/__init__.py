"""Bot providers — console (always), Slack and Teams (optional)."""

from aecos.collaboration.providers.base import BotProvider
from aecos.collaboration.providers.console import ConsoleBotProvider

__all__ = ["BotProvider", "ConsoleBotProvider"]
