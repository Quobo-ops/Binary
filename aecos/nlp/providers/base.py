"""Abstract LLM provider interface."""

from __future__ import annotations

import abc


class LLMProvider(abc.ABC):
    """Base class for LLM-backed parsing providers.

    Implementations must override :meth:`parse_with_llm` which accepts a
    prompt string and returns raw JSON text, or *None* on failure.
    """

    @abc.abstractmethod
    def parse_with_llm(self, prompt: str) -> str | None:
        """Send *prompt* to the LLM and return raw response text.

        Returns *None* if the provider is unavailable or the call fails,
        signalling the caller to fall back to the rule-based engine.
        """

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return *True* if the provider is ready to serve requests."""
