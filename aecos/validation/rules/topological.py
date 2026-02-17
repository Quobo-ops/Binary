"""Topological validation rules — connectivity, containment, adjacency."""

from __future__ import annotations

from typing import Any

from aecos.validation.rules.base import ValidationIssue, ValidationRule


class StoreyContainment(ValidationRule):
    """Elements should reference a containing storey."""

    @property
    def name(self) -> str:
        return "topological.storey_containment"

    @property
    def description(self) -> str:
        return "Wall/slab/column must reference a containing storey."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        spatial = element_data.get("spatial", {})

        # Only check classes that should be spatially contained
        contained_classes = {"IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcColumn", "IfcBeam"}
        if ifc_class not in contained_classes:
            return issues

        storey = spatial.get("storey_name") or spatial.get("storey_id")
        if not storey:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity="info",
                message=f"{ifc_class} has no storey reference",
                element_id=element_id,
                suggestion="Assign element to a building storey for proper spatial coordination.",
            ))
        return issues


class OpeningHostRelation(ValidationRule):
    """Doors and windows should reference a host wall."""

    @property
    def name(self) -> str:
        return "topological.opening_host"

    @property
    def description(self) -> str:
        return "Door/window should reference a host wall element."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        element_id = element_data.get("metadata", {}).get("GlobalId", "")

        if ifc_class not in ("IfcDoor", "IfcWindow"):
            return issues

        spatial = element_data.get("spatial", {})
        # For newly generated elements without host, this is informational
        host = spatial.get("host_wall_id") or spatial.get("host_id")
        if not host:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity="info",
                message=f"{ifc_class} has no host wall reference",
                element_id=element_id,
                suggestion="Associate this opening with a host wall for proper IFC relationships.",
            ))
        return issues


class TopologicalRules:
    """Collection of all topological validation rules."""

    @staticmethod
    def all_rules() -> list[ValidationRule]:
        return [
            StoreyContainment(),
            OpeningHostRelation(),
        ]
