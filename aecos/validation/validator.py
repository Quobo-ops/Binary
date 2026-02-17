"""Validator — main entry point for the validation suite.

Usage::

    from aecos.validation import Validator

    v = Validator()
    report = v.validate(element_folder)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aecos.validation.clash import ClashDetector
from aecos.validation.context import load_context_elements, load_element_data
from aecos.validation.report import ValidationReport
from aecos.validation.rules.base import ValidationIssue, ValidationRule
from aecos.validation.rules.constructability import ConstructabilityRules
from aecos.validation.rules.geometric import GeometricRules
from aecos.validation.rules.semantic import SemanticRules
from aecos.validation.rules.topological import TopologicalRules

logger = logging.getLogger(__name__)


class Validator:
    """Central validation engine with pluggable rule registry.

    Loads default rules on init.  Additional rules can be registered
    via :meth:`add_rule`.
    """

    def __init__(self) -> None:
        self.rules: list[ValidationRule] = []
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Register all built-in rules."""
        self.rules.extend(GeometricRules.all_rules())
        self.rules.extend(SemanticRules.all_rules())
        self.rules.extend(TopologicalRules.all_rules())
        self.rules.extend(ConstructabilityRules.all_rules())

    def add_rule(self, rule: ValidationRule) -> None:
        """Register an additional validation rule."""
        self.rules.append(rule)

    def validate(
        self,
        element_folder: str | Path,
        context_elements: list[str | Path] | None = None,
    ) -> ValidationReport:
        """Validate an element folder against all registered rules.

        Parameters
        ----------
        element_folder:
            Path to the element folder.
        context_elements:
            Optional list of paths to existing element folders for
            clash detection.

        Returns
        -------
        ValidationReport
        """
        folder = Path(element_folder)
        element_data = load_element_data(folder)
        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")

        # Run all rules
        all_issues: list[ValidationIssue] = []
        for rule in self.rules:
            try:
                issues = rule.check(element_data)
                all_issues.extend(issues)
            except Exception:
                logger.debug("Rule %s failed", rule.name, exc_info=True)

        # Clash detection
        clash_results = []
        if context_elements:
            try:
                context_data = load_context_elements(
                    [Path(c) for c in context_elements]
                )
                all_elements = [element_data] + context_data
                detector = ClashDetector()
                clash_results = detector.detect(all_elements)
            except Exception:
                logger.debug("Clash detection failed", exc_info=True)

        # Determine status
        has_errors = any(i.severity == "error" for i in all_issues)
        has_warnings = any(i.severity == "warning" for i in all_issues)
        has_clashes = len(clash_results) > 0

        if has_errors or has_clashes:
            status = "failed"
        elif has_warnings:
            status = "warnings"
        else:
            status = "passed"

        return ValidationReport(
            element_id=element_id,
            ifc_class=ifc_class,
            status=status,
            issues=all_issues,
            clash_results=clash_results,
        )
