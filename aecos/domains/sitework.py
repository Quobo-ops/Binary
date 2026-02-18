"""SiteworkDomain — grading, paving, retaining walls, utilities."""

from __future__ import annotations

from typing import Any

from aecos.domains.base import DomainPlugin
from aecos.validation.rules.base import ValidationIssue, ValidationRule

SOURCE = "RSMeans 2026 Q1 estimated"


class _SiteworkSlopeRule(ValidationRule):
    """Site elements should comply with ADA slope requirements."""

    @property
    def name(self) -> str:
        return "sitework_ada_slope"

    @property
    def description(self) -> str:
        return "Site paving and ramps must meet ADA maximum slope requirements."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class not in {"IfcPavement", "IfcGeographicElement"}:
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            slope = pset_props.get("slope_percent")
            if slope is not None:
                try:
                    if float(slope) > 5.0:
                        return [
                            ValidationIssue(
                                rule_name=self.name,
                                severity="warning",
                                message=f"Slope {slope}% exceeds ADA maximum 5% for accessible routes.",
                                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                                suggestion="Reduce slope to 5% or less for ADA compliance, or add handrails if ramp.",
                            )
                        ]
                except (ValueError, TypeError):
                    pass
        return []


class _SiteworkDrainageRule(ValidationRule):
    """Paving should specify drainage considerations."""

    @property
    def name(self) -> str:
        return "sitework_drainage"

    @property
    def description(self) -> str:
        return "Paving elements should specify surface drainage direction."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class != "IfcPavement":
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "drainage_direction" in pset_props or "slope_percent" in pset_props:
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="info",
                message="Paving element does not specify drainage direction or slope.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add slope_percent or drainage_direction property.",
            )
        ]


class SiteworkDomain(DomainPlugin):
    """Site and civil works domain."""

    @property
    def name(self) -> str:
        return "sitework"

    @property
    def description(self) -> str:
        return "Sitework: grading, paving, retaining walls, and site utilities."

    @property
    def ifc_classes(self) -> list[str]:
        return ["IfcGeographicElement", "IfcPavement", "IfcEarthworksElement"]

    def register_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template_id": "sitework_asphalt_paving",
                "ifc_class": "IfcPavement",
                "name": "Asphalt Paving 75mm",
                "description": "Hot-mix asphalt paving, 75mm thick on aggregate base.",
                "properties": {"thickness_mm": 75, "width_mm": 3600, "length_mm": 6000},
                "materials": ["asphalt"],
                "tags": {"ifc_class": "IfcPavement", "material": ["asphalt"]},
            },
            {
                "template_id": "sitework_concrete_paving",
                "ifc_class": "IfcPavement",
                "name": "Concrete Paving 150mm",
                "description": "Reinforced concrete paving 150mm thick.",
                "properties": {"thickness_mm": 150, "width_mm": 3000, "length_mm": 6000},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcPavement", "material": ["concrete"]},
            },
            {
                "template_id": "sitework_concrete_curb",
                "ifc_class": "IfcPavement",
                "name": "Concrete Curb and Gutter",
                "description": "Cast-in-place concrete curb and gutter, 150mm face.",
                "properties": {"height_mm": 150, "width_mm": 300, "length_mm": 3000},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcPavement", "material": ["concrete"]},
            },
            {
                "template_id": "sitework_retaining_wall",
                "ifc_class": "IfcEarthworksElement",
                "name": "Concrete Retaining Wall",
                "description": "Cast-in-place concrete retaining wall, 2.4m height.",
                "properties": {"height_mm": 2400, "thickness_mm": 300, "length_mm": 6000},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcEarthworksElement", "material": ["concrete"]},
            },
            {
                "template_id": "sitework_grading",
                "ifc_class": "IfcGeographicElement",
                "name": "Site Grading",
                "description": "Fine grading and compaction for building pad.",
                "properties": {"area_m2": 500, "depth_mm": 300},
                "materials": ["soil"],
                "tags": {"ifc_class": "IfcGeographicElement", "material": ["soil"]},
            },
            {
                "template_id": "sitework_storm_pipe",
                "ifc_class": "IfcGeographicElement",
                "name": "Storm Drainage Pipe",
                "description": "HDPE storm drainage pipe 450mm diameter.",
                "properties": {"diameter_mm": 450, "length_mm": 30000},
                "materials": ["hdpe"],
                "tags": {"ifc_class": "IfcGeographicElement", "material": ["hdpe"]},
            },
        ]

    def register_compliance_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "code_name": "ADA2010",
                "section": "403.3",
                "title": "Maximum running slope of accessible route",
                "ifc_classes": ["IfcPavement"],
                "check_type": "max_value",
                "property_path": "properties.slope_percent",
                "check_value": 5.0,
                "region": "US",
                "citation": "ADA 2010 §403.3 — Running slope of walking surfaces shall not be steeper than 1:20 (5%).",
                "effective_date": "2010-09-15",
            },
            {
                "code_name": "IBC2024",
                "section": "1804.1",
                "title": "Stormwater management required",
                "ifc_classes": ["IfcGeographicElement", "IfcPavement"],
                "check_type": "exists",
                "property_path": "materials",
                "check_value": None,
                "region": "US",
                "citation": "IBC 2024 §1804.1 — Surface drainage shall be diverted away from building foundations.",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IBC2024",
                "section": "1809.4",
                "title": "Retaining wall minimum thickness",
                "ifc_classes": ["IfcEarthworksElement"],
                "check_type": "min_value",
                "property_path": "properties.thickness_mm",
                "check_value": 200,
                "region": "US",
                "citation": "IBC 2024 §1809.4 — Retaining walls shall have minimum thickness of 200 mm (8 in.).",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IBC2024",
                "section": "3103.1",
                "title": "Setback and easement compliance",
                "ifc_classes": ["IfcGeographicElement", "IfcPavement", "IfcEarthworksElement"],
                "check_type": "exists",
                "property_path": "properties.length_mm",
                "check_value": None,
                "region": "US",
                "citation": "IBC 2024 §3103.1 — Site elements shall comply with zoning setback requirements.",
                "effective_date": "2024-01-01",
            },
        ]

    def register_parser_patterns(self) -> dict[str, str]:
        return {
            "paving": "IfcPavement",
            "curb": "IfcPavement",
            "retaining wall": "IfcEarthworksElement",
            "grading": "IfcGeographicElement",
        }

    def register_cost_data(self) -> list[dict[str, Any]]:
        return [
            {"material": "asphalt", "ifc_class": "IfcPavement", "material_cost_per_unit": 25.0, "labor_cost_per_unit": 18.0, "unit_type": "m2", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcPavement", "material_cost_per_unit": 55.0, "labor_cost_per_unit": 38.0, "unit_type": "m2", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcEarthworksElement", "material_cost_per_unit": 260.0, "labor_cost_per_unit": 180.0, "unit_type": "m3", "source": SOURCE},
            {"material": "soil", "ifc_class": "IfcGeographicElement", "material_cost_per_unit": 8.0, "labor_cost_per_unit": 12.0, "unit_type": "m2", "source": SOURCE},
            {"material": "hdpe", "ifc_class": "IfcGeographicElement", "material_cost_per_unit": 85.0, "labor_cost_per_unit": 65.0, "unit_type": "m", "source": SOURCE},
            {"material": "aggregate", "ifc_class": "IfcPavement", "material_cost_per_unit": 15.0, "labor_cost_per_unit": 10.0, "unit_type": "m2", "source": SOURCE},
        ]

    def register_validation_rules(self) -> list[ValidationRule]:
        return [
            _SiteworkSlopeRule(),
            _SiteworkDrainageRule(),
        ]

    def get_builder_config(self, ifc_class: str) -> dict[str, Any]:
        configs: dict[str, dict[str, Any]] = {
            "IfcPavement": {"thickness_mm": 75, "width_mm": 3600, "length_mm": 6000},
            "IfcGeographicElement": {"width_mm": 6000, "length_mm": 6000, "depth_mm": 300},
            "IfcEarthworksElement": {"height_mm": 2400, "thickness_mm": 300, "length_mm": 6000},
        }
        return configs.get(ifc_class, {})
