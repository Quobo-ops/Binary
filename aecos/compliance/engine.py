"""ComplianceEngine — main entry point for code compliance checking.

Usage::

    from aecos.compliance import ComplianceEngine

    engine = ComplianceEngine()
    report = engine.check(element_or_spec)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aecos.compliance.checker import check_element
from aecos.compliance.database import RuleDatabase
from aecos.compliance.report import ComplianceReport
from aecos.compliance.rules import Rule

logger = logging.getLogger(__name__)


def _spec_to_data(spec: Any) -> dict[str, Any]:
    """Convert a ParametricSpec to the dict format expected by the checker."""
    # Avoid circular import — accept duck-typed objects
    data: dict[str, Any] = {}

    if hasattr(spec, "properties"):
        data["properties"] = dict(spec.properties)
    if hasattr(spec, "performance"):
        data["performance"] = dict(spec.performance)
    if hasattr(spec, "constraints"):
        data["constraints"] = dict(spec.constraints)
    if hasattr(spec, "materials"):
        mats = spec.materials
        data["materials"] = list(mats) if mats else []

    return data


def _element_to_data(element: Any) -> dict[str, Any]:
    """Convert an Element model to the dict format expected by the checker."""
    data: dict[str, Any] = {}

    # Element stores dimensions in psets, not a flat 'properties' dict
    # Flatten psets into properties
    if hasattr(element, "psets") and element.psets:
        flat: dict[str, Any] = {}
        for _pset_name, props in element.psets.items():
            flat.update(props)
        data["properties"] = flat
    else:
        data["properties"] = {}

    # Performance data may be in psets under specific keys
    perf: dict[str, Any] = {}
    for key in ("fire_rating", "acoustic_stc", "thermal_r_value", "thermal_u_value"):
        if key in data["properties"]:
            perf[key] = data["properties"][key]
    data["performance"] = perf

    data["constraints"] = {}

    if hasattr(element, "materials"):
        data["materials"] = [m.name for m in element.materials if hasattr(m, "name")]
    else:
        data["materials"] = []

    return data


class ComplianceEngine:
    """Check elements or specs against the compliance rule database.

    Parameters
    ----------
    db_path:
        Path to the SQLite database.  Defaults to ``':memory:'`` for an
        ephemeral database (auto-seeded with initial rules).
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db = RuleDatabase(db_path, auto_seed=True)

    def check(
        self,
        element_or_spec: Any,
        *,
        region: str | None = None,
    ) -> ComplianceReport:
        """Run compliance checks against the element or spec.

        Parameters
        ----------
        element_or_spec:
            An ``Element`` (from extraction) or ``ParametricSpec``
            (from the NL parser).
        region:
            Override region for rule filtering.  If *None*, uses '*'
            (all rules).

        Returns
        -------
        ComplianceReport
        """
        # Determine IFC class and element id
        ifc_class = getattr(element_or_spec, "ifc_class", "")
        element_id = getattr(element_or_spec, "global_id", "") or getattr(
            element_or_spec, "name", ""
        ) or ""

        # Convert to checker data format
        is_element = hasattr(element_or_spec, "psets")
        if is_element:
            data = _element_to_data(element_or_spec)
        else:
            data = _spec_to_data(element_or_spec)

        # Query applicable rules
        rules = self.db.get_rules(ifc_class=ifc_class, region=region)

        if not rules:
            return ComplianceReport(
                element_id=element_id,
                ifc_class=ifc_class,
                status="unknown",
                results=[],
                suggested_fixes=[],
            )

        # Evaluate
        results, fixes = check_element(rules, data)

        # Determine overall status
        statuses = {r.status for r in results}
        if "fail" in statuses:
            status = "non_compliant"
        elif statuses == {"pass"}:
            status = "compliant"
        elif "pass" in statuses:
            status = "partial"
        else:
            status = "unknown"

        return ComplianceReport(
            element_id=element_id,
            ifc_class=ifc_class,
            status=status,
            results=results,
            suggested_fixes=fixes,
        )

    def add_rule(self, rule: Rule) -> int:
        """Add a rule to the database. Returns the new rule id."""
        return self.db.add_rule(rule)

    def get_rules(self, **kwargs: Any) -> list[Rule]:
        """Query rules from the database."""
        return self.db.get_rules(**kwargs)

    def search_rules(self, query: str) -> list[Rule]:
        """Full-text search on rules."""
        return self.db.search_rules(query)
