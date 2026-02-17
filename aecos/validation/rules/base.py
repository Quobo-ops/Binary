"""Abstract ValidationRule interface."""

from __future__ import annotations

import abc
from typing import Any


class ValidationIssue:
    """A single validation issue found by a rule."""

    def __init__(
        self,
        rule_name: str,
        severity: str,
        message: str,
        element_id: str = "",
        suggestion: str = "",
    ) -> None:
        self.rule_name = rule_name
        self.severity = severity  # "error", "warning", "info"
        self.message = message
        self.element_id = element_id
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "element_id": self.element_id,
            "suggestion": self.suggestion,
        }


class ValidationRule(abc.ABC):
    """Base class for all validation rules."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short rule identifier."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Human-readable description."""

    @abc.abstractmethod
    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        """Run this rule against element data.

        Parameters
        ----------
        element_data:
            Dict with keys: metadata, psets, materials, geometry, spatial.

        Returns list of issues (empty if passing).
        """
