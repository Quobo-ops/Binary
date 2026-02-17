"""Ollama/local LLM provider — optional, graceful fallback."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from aecos.nlp.providers.base import LLMProvider

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "mistral"


class OllamaProvider(LLMProvider):
    """Provider that calls a local Ollama instance.

    Gracefully returns *None* if Ollama is not running, allowing the
    caller to fall back to the rule-based engine.
    """

    def __init__(
        self,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if Ollama is running by hitting the version endpoint."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def parse_with_llm(self, prompt: str) -> str | None:
        """Send a prompt to Ollama and return the response text.

        Returns *None* if Ollama is unreachable or the call fails.
        """
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response")
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            logger.debug("Ollama call failed: %s", exc)
            return None
