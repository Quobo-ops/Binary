"""Semantic validation rules — property consistency, required fields, value ranges."""

from __future__ import annotations

from typing import Any

from aecos.validation.rules.base import ValidationIssue, ValidationRule

# Required properties by IFC class
_REQUIRED_PROPERTIES: dict[str, list[str]] = {
    "IfcWall": ["thickness_mm"],
    "IfcWallStandardCase": ["thickness_mm"],
    "IfcDoor": ["width_mm", "height_mm"],
    "IfcWindow": ["width_mm", "height_mm"],
    "IfcSlab": ["thickness_mm"],
    "IfcColumn": ["height_mm"],
    "IfcBeam": ["depth_mm", "length_mm"],
}

# Standard dimension ranges (mm)
_DIM_RANGES: dict[str, tuple[float, float]] = {
    "thickness_mm": (10.0, 2000.0),
    "height_mm": (100.0, 50000.0),
    "width_mm": (100.0, 20000.0),
    "length_mm": (100.0, 100000.0),
    "depth_mm": (50.0, 5000.0),
}

# Fire rating: material capabilities (max hours)
_MATERIAL_FIRE_MAX: dict[str, int] = {
    "concrete": 4,
    "cmu": 4,
    "brick": 4,
    "steel": 3,
    "gypsum": 2,
    "wood": 1,
    "glass": 0,
    "aluminum": 0,
}


class RequiredProperties(ValidationRule):
    """IFC class-specific required properties must be present."""

    @property
    def name(self) -> str:
        return "semantic.required_properties"

    @property
    def description(self) -> str:
        return "Verify required properties are present for the IFC class."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        psets = element_data.get("psets", {})

        required = _REQUIRED_PROPERTIES.get(ifc_class, [])
        if not required:
            return issues

        # Gather all dimension values
        dims = psets.get("Dimensions", {})

        for prop in required:
            val = dims.get(prop)
            if val is None:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity="error",
                    message=f"Required property '{prop}' is missing for {ifc_class}",
                    element_id=element_id,
                    suggestion=f"Add '{prop}' to the Dimensions property set.",
                ))
        return issues


class ValueRanges(ValidationRule):
    """Dimension values must be within realistic ranges."""

    @property
    def name(self) -> str:
        return "semantic.value_ranges"

    @property
    def description(self) -> str:
        return "Verify dimension values are within standard ranges."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        psets = element_data.get("psets", {})
        dims = psets.get("Dimensions", {})
        element_id = element_data.get("metadata", {}).get("GlobalId", "")

        for key, (lo, hi) in _DIM_RANGES.items():
            val = dims.get(key)
            if val is None:
                continue
            try:
                val = float(val)
            except (TypeError, ValueError):
                continue
            if val < lo:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity="warning",
                    message=f"{key} ({val}mm) is below standard minimum ({lo}mm)",
                    element_id=element_id,
                    suggestion=f"Verify {key} — standard range is {lo}–{hi}mm.",
                ))
            elif val > hi:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity="warning",
                    message=f"{key} ({val}mm) exceeds standard maximum ({hi}mm)",
                    element_id=element_id,
                    suggestion=f"Verify {key} — standard range is {lo}–{hi}mm.",
                ))
        return issues


class MaterialFireRating(ValidationRule):
    """Fire rating must be achievable with the specified materials."""

    @property
    def name(self) -> str:
        return "semantic.material_fire_rating"

    @property
    def description(self) -> str:
        return "Verify fire rating is consistent with material capabilities."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        psets = element_data.get("psets", {})
        element_id = element_data.get("metadata", {}).get("GlobalId", "")
        materials = element_data.get("materials", [])

        # Find fire rating in psets
        fire_rating = None
        for pset_name, props in psets.items():
            fr = props.get("FireRating")
            if fr is not None:
                fire_rating = fr
                break

        if fire_rating is None or not materials:
            return issues

        # Parse fire rating hours
        required_hours = _parse_fire_hours(fire_rating)
        if required_hours <= 0:
            return issues

        # Check each material
        for mat in materials:
            mat_name = mat.get("name", "").lower()
            max_hours = _MATERIAL_FIRE_MAX.get(mat_name, 99)
            if required_hours > max_hours:
                issues.append(ValidationIssue(
                    rule_name=self.name,
                    severity="warning",
                    message=f"Fire rating {fire_rating} exceeds {mat_name} capability ({max_hours}H max)",
                    element_id=element_id,
                    suggestion=f"Consider a different material or assembly to achieve {fire_rating} fire rating.",
                ))
        return issues


def _parse_fire_hours(rating: Any) -> int:
    """Parse a fire rating string like '2H' or '2' into hours."""
    if rating is None:
        return 0
    s = str(rating).upper().strip()
    s = s.rstrip("HR").rstrip("H")
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return 0


class SemanticRules:
    """Collection of all semantic validation rules."""

    @staticmethod
    def all_rules() -> list[ValidationRule]:
        return [
            RequiredProperties(),
            ValueRanges(),
            MaterialFireRating(),
        ]
