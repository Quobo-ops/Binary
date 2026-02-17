"""Element-level compliance checking against matched rules."""

from __future__ import annotations

from typing import Any

from aecos.compliance.rules import Rule, RuleResult, evaluate_rule


def check_element(
    rules: list[Rule],
    element_data: dict[str, Any],
) -> tuple[list[RuleResult], list[str]]:
    """Evaluate all applicable rules against an element.

    Parameters
    ----------
    rules:
        List of rules to evaluate.
    element_data:
        Dict representation of the element with keys like
        ``properties``, ``performance``, ``constraints``, ``materials``.

    Returns
    -------
    tuple[list[RuleResult], list[str]]
        A tuple of (results, suggested_fixes).
    """
    results: list[RuleResult] = []
    fixes: list[str] = []

    for rule in rules:
        result = evaluate_rule(rule, element_data)
        results.append(result)

        if result.status == "fail":
            fix = _suggest_fix(rule, result)
            if fix:
                fixes.append(fix)

    return results, fixes


def _suggest_fix(rule: Rule, result: RuleResult) -> str:
    """Generate an actionable suggestion for a failed rule."""
    if rule.check_type == "min_value":
        return (
            f"Increase {rule.property_path} to at least {rule.check_value} "
            f"per {rule.code_name} §{rule.section}."
        )
    if rule.check_type == "max_value":
        return (
            f"Reduce {rule.property_path} to at most {rule.check_value} "
            f"per {rule.code_name} §{rule.section}."
        )
    if rule.check_type == "exists":
        return (
            f"Provide a value for {rule.property_path} "
            f"per {rule.code_name} §{rule.section}."
        )
    if rule.check_type == "boolean":
        return (
            f"Ensure {rule.property_path} = {rule.check_value} "
            f"per {rule.code_name} §{rule.section}."
        )
    if rule.check_type == "enum":
        return (
            f"Set {rule.property_path} to one of {rule.check_value} "
            f"per {rule.code_name} §{rule.section}."
        )
    return f"Review {rule.code_name} §{rule.section}: {rule.title}."
