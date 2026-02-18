"""FireProtectionDomain — sprinklers, suppression, fire dampers."""

from __future__ import annotations

from typing import Any

from aecos.domains.base import DomainPlugin
from aecos.validation.rules.base import ValidationIssue, ValidationRule

SOURCE = "RSMeans 2026 Q1 estimated"


class _FireProtectionCoverageRule(ValidationRule):
    """Fire suppression elements should specify coverage area."""

    @property
    def name(self) -> str:
        return "fire_protection_coverage"

    @property
    def description(self) -> str:
        return "Sprinkler heads must specify maximum coverage area per NFPA 13."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class != "IfcFireSuppressionTerminal":
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "coverage_m2" in pset_props or "CoverageArea" in pset_props:
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message="Sprinkler head does not specify coverage area.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add coverage_m2 property (max 18.6 m2 per NFPA 13 for light hazard).",
            )
        ]


class _FireProtectionRatingRule(ValidationRule):
    """Fire dampers should specify fire rating."""

    @property
    def name(self) -> str:
        return "fire_protection_damper_rating"

    @property
    def description(self) -> str:
        return "Fire dampers must specify fire resistance rating."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class != "IfcProtectiveDevice":
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "fire_rating" in pset_props or "FireRating" in pset_props:
                return []
        # Check performance dict
        perf = element_data.get("performance", {})
        if perf.get("fire_rating"):
            return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message="Fire damper does not specify fire resistance rating.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add fire_rating property (e.g. 1.5H or 3H per barrier rating).",
            )
        ]


class FireProtectionDomain(DomainPlugin):
    """Fire protection and suppression systems domain."""

    @property
    def name(self) -> str:
        return "fire_protection"

    @property
    def description(self) -> str:
        return "Fire protection: sprinklers, suppression systems, fire dampers, and standpipes."

    @property
    def ifc_classes(self) -> list[str]:
        return ["IfcFireSuppressionTerminal", "IfcProtectiveDevice", "IfcValve"]

    def register_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template_id": "fp_pendant_sprinkler",
                "ifc_class": "IfcFireSuppressionTerminal",
                "name": "Pendant Sprinkler Head",
                "description": "Standard pendant sprinkler head, 155°F, 1/2 in. orifice.",
                "properties": {"coverage_m2": 18.6, "temperature_f": 155, "orifice_mm": 12.7, "type": "pendant"},
                "materials": ["brass"],
                "tags": {"ifc_class": "IfcFireSuppressionTerminal", "material": ["brass"], "compliance_codes": ["NFPA13"]},
            },
            {
                "template_id": "fp_fire_damper",
                "ifc_class": "IfcProtectiveDevice",
                "name": "Fire Damper 1.5H",
                "description": "1.5-hour rated fire damper for duct penetration.",
                "properties": {"fire_rating": "1.5H", "width_mm": 600, "height_mm": 400},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcProtectiveDevice", "material": ["steel"], "compliance_codes": ["NFPA80"]},
            },
            {
                "template_id": "fp_standpipe",
                "ifc_class": "IfcValve",
                "name": "Standpipe Valve Connection",
                "description": "Class III standpipe with 2.5 in. valve and FDC.",
                "properties": {"diameter_mm": 65, "type": "Class III"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcValve", "material": ["steel"], "compliance_codes": ["NFPA14"]},
            },
            {
                "template_id": "fp_extinguisher",
                "ifc_class": "IfcFireSuppressionTerminal",
                "name": "Fire Extinguisher Cabinet",
                "description": "Recessed fire extinguisher cabinet with 10 lb ABC extinguisher.",
                "properties": {"width_mm": 300, "height_mm": 600, "depth_mm": 150, "type": "cabinet"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcFireSuppressionTerminal", "material": ["steel"], "compliance_codes": ["NFPA10"]},
            },
        ]

    def register_compliance_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "code_name": "NFPA13",
                "section": "8.5.2",
                "title": "Maximum sprinkler coverage area (light hazard)",
                "ifc_classes": ["IfcFireSuppressionTerminal"],
                "check_type": "max_value",
                "property_path": "properties.coverage_m2",
                "check_value": 18.6,
                "region": "US",
                "citation": "NFPA 13 §8.5.2 — Maximum protection area per sprinkler: 200 ft² (18.6 m²) for light hazard.",
                "effective_date": "2022-01-01",
            },
            {
                "code_name": "NFPA80",
                "section": "19.4.1",
                "title": "Fire damper rating must match barrier",
                "ifc_classes": ["IfcProtectiveDevice"],
                "check_type": "exists",
                "property_path": "properties.fire_rating",
                "check_value": None,
                "region": "US",
                "citation": "NFPA 80 §19.4.1 — Fire dampers shall have a fire resistance rating not less than the barrier penetrated.",
                "effective_date": "2022-01-01",
            },
            {
                "code_name": "NFPA14",
                "section": "7.3.2",
                "title": "Standpipe minimum hose reach",
                "ifc_classes": ["IfcValve"],
                "check_type": "min_value",
                "property_path": "properties.diameter_mm",
                "check_value": 38,
                "region": "US",
                "citation": "NFPA 14 §7.3.2 — Standpipe hose connections shall be minimum 1.5 in. (38 mm) diameter.",
                "effective_date": "2019-01-01",
            },
            {
                "code_name": "NFPA10",
                "section": "6.1.3",
                "title": "Extinguisher travel distance",
                "ifc_classes": ["IfcFireSuppressionTerminal"],
                "check_type": "exists",
                "property_path": "properties.type",
                "check_value": None,
                "region": "US",
                "citation": "NFPA 10 §6.1.3 — Fire extinguishers shall be distributed so travel distance does not exceed 75 ft.",
                "effective_date": "2022-01-01",
            },
        ]

    def register_parser_patterns(self) -> dict[str, str]:
        return {
            "sprinkler": "IfcFireSuppressionTerminal",
            "fire damper": "IfcProtectiveDevice",
            "standpipe": "IfcValve",
            "extinguisher": "IfcFireSuppressionTerminal",
        }

    def register_cost_data(self) -> list[dict[str, Any]]:
        return [
            {"material": "brass", "ifc_class": "IfcFireSuppressionTerminal", "material_cost_per_unit": 35.0, "labor_cost_per_unit": 65.0, "unit_type": "each", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcProtectiveDevice", "material_cost_per_unit": 280.0, "labor_cost_per_unit": 150.0, "unit_type": "each", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcValve", "material_cost_per_unit": 450.0, "labor_cost_per_unit": 200.0, "unit_type": "each", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcFireSuppressionTerminal", "material_cost_per_unit": 120.0, "labor_cost_per_unit": 45.0, "unit_type": "each", "source": SOURCE},
        ]

    def register_validation_rules(self) -> list[ValidationRule]:
        return [
            _FireProtectionCoverageRule(),
            _FireProtectionRatingRule(),
        ]

    def get_builder_config(self, ifc_class: str) -> dict[str, Any]:
        configs: dict[str, dict[str, Any]] = {
            "IfcFireSuppressionTerminal": {"coverage_m2": 18.6, "temperature_f": 155, "type": "pendant"},
            "IfcProtectiveDevice": {"fire_rating": "1.5H", "width_mm": 600, "height_mm": 400},
            "IfcValve": {"diameter_mm": 65, "type": "Class III"},
        }
        return configs.get(ifc_class, {})
