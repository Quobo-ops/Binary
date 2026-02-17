"""Constructability validation rules — practical build checks."""

from __future__ import annotations

from typing import Any

from aecos.validation.rules.base import ValidationIssue, ValidationRule

# Material layer ordering (exterior to interior)
_LAYER_ORDER = {
    "brick": 0,
    "stone": 0,
    "stucco": 0,
    "cmu": 1,
    "concrete": 1,
    "insulation": 2,
    "fiberglass": 2,
    "gypsum": 3,
    "drywall": 3,
    "plywood": 2,
    "wood": 1,
    "steel": 1,
}

# Standard dimension proximity thresholds (common sizes in mm)
_STANDARD_WALL_THICKNESSES = {100, 150, 200, 250, 300, 400}
_STANDARD_DOOR_WIDTHS = {762, 813, 914, 1016, 1219}
_STANDARD_DOOR_HEIGHTS = {2032, 2134}

# Beam span/depth ratio limits
_MAX_BEAM_SPAN_DEPTH_RATIO = 25.0


class MaterialLayerOrdering(ValidationRule):
    """Material layers should follow exterior-to-interior ordering."""

    @property
    def name(self) -> str:
        return "constructability.layer_ordering"

    @property
    def description(self) -> str:
        return "Verify material layers follow standard exterior-to-interior ordering."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        materials = element_data.get("materials", [])
        element_id = element_data.get("metadata", {}).get("GlobalId", "")

        if len(materials) < 2:
            return issues

        orders = []
        for mat in materials:
            name = mat.get("name", "").lower()
            order = _LAYER_ORDER.get(name)
            if order is not None:
                orders.append((name, order))

        if len(orders) < 2:
            return issues

        # Check if ordering is monotonically non-decreasing
        for i in range(1, len(orders)):
            if orders[i][1] < orders[i - 1][1]:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity="warning",
                    message=f"Layer '{orders[i][0]}' (position {i+1}) appears after '{orders[i-1][0]}' — expected exterior-to-interior order",
                    element_id=element_id,
                    suggestion="Reorder material layers: exterior finish, structure, insulation, interior finish.",
                ))
                break

        return issues


class BeamSpanDepth(ValidationRule):
    """Beam span/depth ratio should be within feasibility limits."""

    @property
    def name(self) -> str:
        return "constructability.beam_span_depth"

    @property
    def description(self) -> str:
        return "Verify beam span-to-depth ratio is within practical limits."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class != "IfcBeam":
            return issues

        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        psets = element_data.get("psets", {})
        dims = psets.get("Dimensions", {})

        span = dims.get("length_mm")
        depth = dims.get("depth_mm")
        if span is None or depth is None:
            return issues

        try:
            span = float(span)
            depth = float(depth)
        except (TypeError, ValueError):
            return issues

        if depth <= 0:
            return issues

        ratio = span / depth
        if ratio > _MAX_BEAM_SPAN_DEPTH_RATIO:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message=f"Beam span/depth ratio ({ratio:.1f}) exceeds practical limit ({_MAX_BEAM_SPAN_DEPTH_RATIO})",
                element_id=element_id,
                suggestion=f"Increase beam depth or reduce span. Typical ratio is 15-20 for steel, 10-15 for concrete.",
            ))
        return issues


class StandardSizeProximity(ValidationRule):
    """Flag non-standard dimensions."""

    @property
    def name(self) -> str:
        return "constructability.standard_size"

    @property
    def description(self) -> str:
        return "Flag dimensions that are not close to standard sizes."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        psets = element_data.get("psets", {})
        dims = psets.get("Dimensions", {})

        if ifc_class in ("IfcWall", "IfcWallStandardCase"):
            thickness = dims.get("thickness_mm")
            if thickness is not None:
                try:
                    t = float(thickness)
                    if not _near_standard(t, _STANDARD_WALL_THICKNESSES):
                        issues.append(ValidationIssue(
                            rule_name=self.name,
                            severity="info",
                            message=f"Wall thickness {t}mm is not a standard size ({sorted(_STANDARD_WALL_THICKNESSES)})",
                            element_id=element_id,
                            suggestion="Consider using a standard wall thickness for cost efficiency.",
                        ))
                except (TypeError, ValueError):
                    pass

        elif ifc_class == "IfcDoor":
            width = dims.get("width_mm")
            if width is not None:
                try:
                    w = float(width)
                    if not _near_standard(w, _STANDARD_DOOR_WIDTHS, tolerance=25):
                        issues.append(ValidationIssue(
                            rule_name=self.name,
                            severity="info",
                            message=f"Door width {w}mm is not a standard size",
                            element_id=element_id,
                            suggestion="Consider using a standard door width (762, 813, 914, 1016, 1219mm).",
                        ))
                except (TypeError, ValueError):
                    pass

        return issues


def _near_standard(value: float, standards: set[float], tolerance: float = 10.0) -> bool:
    """Return True if value is within tolerance of any standard size."""
    return any(abs(value - s) <= tolerance for s in standards)


class ConstructabilityRules:
    """Collection of all constructability validation rules."""

    @staticmethod
    def all_rules() -> list[ValidationRule]:
        return [
            MaterialLayerOrdering(),
            BeamSpanDepth(),
            StandardSizeProximity(),
        ]
