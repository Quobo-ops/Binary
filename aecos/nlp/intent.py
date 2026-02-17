"""Intent classification — determine the user's desired action."""

from __future__ import annotations

import re

# Intent patterns ordered by specificity
_INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("validate", re.compile(
        r"\b(check|validate|verify|inspect|audit|comply|compliance|compliant)\b", re.I,
    )),
    ("find", re.compile(
        r"\b(find|search|list|show|get|query|locate|filter|select|retrieve|look\s*up)\b", re.I,
    )),
    ("modify", re.compile(
        r"\b(update|modify|change|alter|edit|replace|upgrade|increase|decrease|"
        r"resize|adjust|revise|rename|set)\b", re.I,
    )),
    ("create", re.compile(
        r"\b(create|add|build|construct|make|insert|place|install|design|generate|new)\b", re.I,
    )),
]


def classify_intent(text: str) -> str:
    """Return the most likely intent for *text*.

    Returns one of: ``'create'``, ``'modify'``, ``'find'``, ``'validate'``.
    Defaults to ``'create'`` when no strong signal is found.
    """
    text_lower = text.lower().strip()
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(text_lower):
            return intent
    return "create"
