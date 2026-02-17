"""Rule model and evaluation logic."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class Rule(BaseModel):
    """A single building-code rule stored in the compliance database."""

    id: int | None = None
    code_name: str
    """Code identifier: 'IBC2024', 'CBC2025', 'Title-24', 'ADA2010'."""

    section: str
    """Section reference: '703.3', '1106.2'."""

    title: str
    """Human-readable rule name."""

    ifc_classes: list[str] = Field(default_factory=list)
    """IFC types this rule applies to."""

    check_type: str
    """Evaluation type: 'min_value', 'max_value', 'enum', 'boolean', 'exists'."""

    property_path: str
    """Dot-notation path to the checked property, e.g. 'performance.fire_rating'."""

    check_value: Any = None
    """Threshold or required value for evaluation."""

    region: str = "*"
    """Region scope: 'US', 'CA', 'LA' (Louisiana), '*' for universal."""

    citation: str = ""
    """Full citation text for reports."""

    effective_date: str = ""
    """ISO date string when rule takes effect."""


class RuleResult(BaseModel):
    """Result of evaluating a single rule against an element."""

    rule_id: int | None = None
    code_name: str = ""
    section: str = ""
    title: str = ""
    status: str = "unknown"
    """'pass', 'fail', 'skip', 'unknown'."""

    actual_value: Any = None
    expected_value: Any = None
    citation: str = ""
    message: str = ""


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-notation path against a nested dict.

    Example: _resolve_path({"performance": {"fire_rating": "2H"}}, "performance.fire_rating")
    returns "2H".
    """
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _parse_fire_rating_hours(value: Any) -> float | None:
    """Parse a fire rating string to hours (e.g., '2H' -> 2.0)."""
    if value is None:
        return None
    s = str(value).upper().strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*H?$", s)
    if m:
        return float(m.group(1))
    return None


def _coerce_numeric(value: Any) -> float | None:
    """Try to coerce a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def evaluate_rule(rule: Rule, element_data: dict[str, Any]) -> RuleResult:
    """Evaluate a single rule against element data.

    Parameters
    ----------
    rule:
        The rule to evaluate.
    element_data:
        A flat dict representation of the element/spec with keys like
        ``properties``, ``performance``, ``constraints``, ``materials``, etc.

    Returns
    -------
    RuleResult
        The evaluation result for this rule.
    """
    result = RuleResult(
        rule_id=rule.id,
        code_name=rule.code_name,
        section=rule.section,
        title=rule.title,
        expected_value=rule.check_value,
        citation=rule.citation,
    )

    actual = _resolve_path(element_data, rule.property_path)
    result.actual_value = actual

    if rule.check_type == "exists":
        if actual is not None and actual != "" and actual != []:
            result.status = "pass"
            result.message = f"{rule.property_path} is present."
        else:
            result.status = "fail"
            result.message = f"{rule.property_path} is required but missing."
        return result

    if rule.check_type == "boolean":
        expected = bool(rule.check_value) if rule.check_value is not None else True
        if actual is not None and bool(actual) == expected:
            result.status = "pass"
            result.message = f"{rule.property_path} = {actual} (expected {expected})."
        elif actual is None:
            result.status = "fail"
            result.message = f"{rule.property_path} is not set (expected {expected})."
        else:
            result.status = "fail"
            result.message = f"{rule.property_path} = {actual} (expected {expected})."
        return result

    if rule.check_type == "enum":
        allowed = rule.check_value if isinstance(rule.check_value, list) else [rule.check_value]
        allowed_upper = [str(a).upper() for a in allowed]
        if actual is not None and str(actual).upper() in allowed_upper:
            result.status = "pass"
            result.message = f"{rule.property_path} = {actual} is in allowed set."
        else:
            result.status = "fail"
            result.message = (
                f"{rule.property_path} = {actual} not in allowed values {allowed}."
            )
        return result

    if rule.check_type == "min_value":
        # Special handling for fire ratings (compare hours)
        if "fire_rating" in rule.property_path:
            actual_num = _parse_fire_rating_hours(actual)
            expected_num = _parse_fire_rating_hours(rule.check_value)
            if expected_num is None:
                expected_num = _coerce_numeric(rule.check_value)
        else:
            actual_num = _coerce_numeric(actual)
            expected_num = _coerce_numeric(rule.check_value)

        if actual_num is None:
            result.status = "fail"
            result.message = (
                f"{rule.property_path} is not set; minimum {rule.check_value} required."
            )
        elif expected_num is not None and actual_num >= expected_num:
            result.status = "pass"
            result.message = (
                f"{rule.property_path} = {actual} meets minimum {rule.check_value}."
            )
        else:
            result.status = "fail"
            result.message = (
                f"{rule.property_path} = {actual} below minimum {rule.check_value}."
            )
        return result

    if rule.check_type == "max_value":
        actual_num = _coerce_numeric(actual)
        expected_num = _coerce_numeric(rule.check_value)

        if actual_num is None:
            result.status = "skip"
            result.message = f"{rule.property_path} not set; cannot verify maximum."
        elif expected_num is not None and actual_num <= expected_num:
            result.status = "pass"
            result.message = (
                f"{rule.property_path} = {actual} within maximum {rule.check_value}."
            )
        else:
            result.status = "fail"
            result.message = (
                f"{rule.property_path} = {actual} exceeds maximum {rule.check_value}."
            )
        return result

    # Unknown check type
    result.status = "unknown"
    result.message = f"Unknown check_type: {rule.check_type}"
    return result
