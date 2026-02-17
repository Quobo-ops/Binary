"""Geometric validation rules — bounding box, clearance, tolerance checks.

All checks operate on spatial.json / geometry data — no mesh tessellation.
"""

from __future__ import annotations

from typing import Any

from aecos.validation.rules.base import ValidationIssue, ValidationRule

# Standard clearance requirements (mm)
_DOOR_SWING_CLEARANCE_MM = 1000.0
_CORRIDOR_MIN_WIDTH_MM = 1118.0  # IBC 1005.1


class DimensionPositivity(ValidationRule):
    """All physical dimensions must be positive."""

    @property
    def name(self) -> str:
        return "geometric.dimension_positivity"

    @property
    def description(self) -> str:
        return "Verify all dimensions (height, width, thickness, length) are positive."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        psets = element_data.get("psets", {})
        dims = psets.get("Dimensions", {})
        element_id = element_data.get("metadata", {}).get("GlobalId", "")

        for key in ("height_mm", "width_mm", "thickness_mm", "length_mm", "depth_mm"):
            val = dims.get(key)
            if val is not None:
                try:
                    if float(val) <= 0:
                        issues.append(ValidationIssue(
                            rule_name=self.name,
                            severity="error",
                            message=f"{key} must be positive, got {val}",
                            element_id=element_id,
                            suggestion=f"Set {key} to a positive value.",
                        ))
                except (TypeError, ValueError):
                    issues.append(ValidationIssue(
                        rule_name=self.name,
                        severity="error",
                        message=f"{key} is not a valid number: {val}",
                        element_id=element_id,
                        suggestion=f"Provide a numeric value for {key}.",
                    ))
        return issues


class BoundingBoxValid(ValidationRule):
    """Bounding box min values must be <= max values."""

    @property
    def name(self) -> str:
        return "geometric.bounding_box_valid"

    @property
    def description(self) -> str:
        return "Verify bounding box is well-formed (min <= max for all axes)."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        geo = element_data.get("geometry", {})
        bb = geo.get("bounding_box", {})
        element_id = element_data.get("metadata", {}).get("GlobalId", "")

        for axis in ("x", "y", "z"):
            lo = bb.get(f"min_{axis}", 0.0)
            hi = bb.get(f"max_{axis}", 0.0)
            if lo > hi:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity="error",
                    message=f"Bounding box min_{axis} ({lo}) > max_{axis} ({hi})",
                    element_id=element_id,
                    suggestion=f"Swap min_{axis} and max_{axis}.",
                ))
        return issues


class DoorClearance(ValidationRule):
    """Doors must have minimum swing clearance space."""

    @property
    def name(self) -> str:
        return "geometric.door_clearance"

    @property
    def description(self) -> str:
        return "Verify door has sufficient swing clearance space."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class != "IfcDoor":
            return issues

        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        psets = element_data.get("psets", {})
        dims = psets.get("Dimensions", {})
        width_mm = dims.get("width_mm", 0)

        try:
            width_mm = float(width_mm)
        except (TypeError, ValueError):
            return issues

        # Check if there's enough room for the door to swing
        # Context elements would refine this; here we check basic width
        if width_mm > 0 and width_mm < _DOOR_SWING_CLEARANCE_MM:
            issues.append(ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message=f"Door width ({width_mm}mm) is less than recommended swing clearance ({_DOOR_SWING_CLEARANCE_MM}mm)",
                element_id=element_id,
                suggestion="Ensure sufficient clear floor space for door swing per ADA/IBC requirements.",
            ))
        return issues


class GeometricRules:
    """Collection of all geometric validation rules."""

    @staticmethod
    def all_rules() -> list[ValidationRule]:
        return [
            DimensionPositivity(),
            BoundingBoxValid(),
            DoorClearance(),
        ]
