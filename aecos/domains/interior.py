"""InteriorDomain — partitions, ceilings, flooring, millwork."""

from __future__ import annotations

from typing import Any

from aecos.domains.base import DomainPlugin
from aecos.validation.rules.base import ValidationIssue, ValidationRule

SOURCE = "RSMeans 2026 Q1 estimated"


class _InteriorFinishRule(ValidationRule):
    """Interior finishes should specify material."""

    @property
    def name(self) -> str:
        return "interior_finish_material"

    @property
    def description(self) -> str:
        return "Interior covering elements must specify finish material."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class not in {"IfcCovering", "IfcFurniture"}:
            return []
        materials = element_data.get("materials", [])
        if materials:
            return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message=f"{ifc_class} element does not specify finish material.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Specify material (e.g. ACT, carpet, VCT, wood veneer).",
            )
        ]


class _InteriorClearanceRule(ValidationRule):
    """Furniture and casework must have clearance dimensions."""

    @property
    def name(self) -> str:
        return "interior_ada_clearance"

    @property
    def description(self) -> str:
        return "Interior elements must maintain ADA clearance requirements."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class != "IfcFurniture":
            return []
        # Just check that depth is specified for clearance analysis
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "depth_mm" in pset_props or "Depth" in pset_props:
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="info",
                message="Furniture element does not specify depth for ADA clearance analysis.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add depth_mm property for ADA clearance verification.",
            )
        ]


class InteriorDomain(DomainPlugin):
    """Interior finishes and fit-out domain."""

    @property
    def name(self) -> str:
        return "interior"

    @property
    def description(self) -> str:
        return "Interior: partitions, ceilings, flooring, millwork, and furnishings."

    @property
    def ifc_classes(self) -> list[str]:
        return ["IfcCovering", "IfcFurniture", "IfcCurtainWall", "IfcRailing"]

    def register_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template_id": "interior_act_ceiling",
                "ifc_class": "IfcCovering",
                "name": "ACT Ceiling 600x600",
                "description": "Acoustical ceiling tile 600x600mm, lay-in grid system.",
                "properties": {"width_mm": 600, "length_mm": 600, "thickness_mm": 19},
                "materials": ["mineral_fiber"],
                "tags": {"ifc_class": "IfcCovering", "material": ["mineral_fiber"]},
            },
            {
                "template_id": "interior_carpet_tile",
                "ifc_class": "IfcCovering",
                "name": "Carpet Tile",
                "description": "Commercial carpet tile 600x600mm, nylon broadloom.",
                "properties": {"width_mm": 600, "length_mm": 600, "thickness_mm": 8},
                "materials": ["nylon"],
                "tags": {"ifc_class": "IfcCovering", "material": ["nylon"]},
            },
            {
                "template_id": "interior_gypsum_partition",
                "ifc_class": "IfcCovering",
                "name": "Gypsum Board Partition",
                "description": "Metal stud partition with gypsum board both sides, 92mm.",
                "properties": {"thickness_mm": 92, "height_mm": 2700},
                "materials": ["gypsum"],
                "tags": {"ifc_class": "IfcCovering", "material": ["gypsum"]},
            },
            {
                "template_id": "interior_casework_upper",
                "ifc_class": "IfcFurniture",
                "name": "Upper Cabinet 900mm",
                "description": "Plastic laminate upper cabinet, 900mm wide.",
                "properties": {"width_mm": 900, "height_mm": 750, "depth_mm": 350},
                "materials": ["wood"],
                "tags": {"ifc_class": "IfcFurniture", "material": ["wood"]},
            },
            {
                "template_id": "interior_vct_floor",
                "ifc_class": "IfcCovering",
                "name": "VCT Flooring",
                "description": "Vinyl composition tile 305x305mm.",
                "properties": {"width_mm": 305, "length_mm": 305, "thickness_mm": 3},
                "materials": ["vinyl"],
                "tags": {"ifc_class": "IfcCovering", "material": ["vinyl"]},
            },
            {
                "template_id": "interior_wood_base",
                "ifc_class": "IfcCovering",
                "name": "Wood Base Molding",
                "description": "Hardwood base molding 100mm height.",
                "properties": {"height_mm": 100, "thickness_mm": 12, "length_mm": 2400},
                "materials": ["wood"],
                "tags": {"ifc_class": "IfcCovering", "material": ["wood"]},
            },
        ]

    def register_compliance_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "code_name": "IBC2024",
                "section": "803.1",
                "title": "Interior finish flame spread index",
                "ifc_classes": ["IfcCovering"],
                "check_type": "exists",
                "property_path": "materials",
                "check_value": None,
                "region": "US",
                "citation": "IBC 2024 §803.1 — Interior wall and ceiling finish materials shall be classified per ASTM E84.",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IBC2024",
                "section": "1208.2",
                "title": "Minimum ceiling height",
                "ifc_classes": ["IfcCovering"],
                "check_type": "min_value",
                "property_path": "properties.height_mm",
                "check_value": 2134,
                "region": "US",
                "citation": "IBC 2024 §1208.2 — Minimum ceiling height in habitable rooms shall be 2134 mm (7 ft).",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "ADA2010",
                "section": "306.2",
                "title": "Knee clearance under counters",
                "ifc_classes": ["IfcFurniture"],
                "check_type": "min_value",
                "property_path": "properties.depth_mm",
                "check_value": 200,
                "region": "US",
                "citation": "ADA 2010 §306.2 — Knee clearance shall extend 200 mm (8 in.) minimum under accessible counters.",
                "effective_date": "2010-09-15",
            },
            {
                "code_name": "ADA2010",
                "section": "307.2",
                "title": "Protruding objects clearance",
                "ifc_classes": ["IfcFurniture", "IfcCovering"],
                "check_type": "exists",
                "property_path": "properties.depth_mm",
                "check_value": None,
                "region": "US",
                "citation": "ADA 2010 §307.2 — Wall-mounted objects with leading edges 685-2032 mm above floor shall protrude no more than 100 mm.",
                "effective_date": "2010-09-15",
            },
        ]

    def register_parser_patterns(self) -> dict[str, str]:
        return {
            "ceiling": "IfcCovering",
            "act ceiling": "IfcCovering",
            "floor": "IfcCovering",
            "partition": "IfcCovering",
            "casework": "IfcFurniture",
            "railing": "IfcRailing",
        }

    def register_cost_data(self) -> list[dict[str, Any]]:
        return [
            {"material": "mineral_fiber", "ifc_class": "IfcCovering", "material_cost_per_unit": 18.0, "labor_cost_per_unit": 12.0, "unit_type": "m2", "source": SOURCE},
            {"material": "nylon", "ifc_class": "IfcCovering", "material_cost_per_unit": 35.0, "labor_cost_per_unit": 8.0, "unit_type": "m2", "source": SOURCE},
            {"material": "gypsum", "ifc_class": "IfcCovering", "material_cost_per_unit": 28.0, "labor_cost_per_unit": 32.0, "unit_type": "m2", "source": SOURCE},
            {"material": "wood", "ifc_class": "IfcFurniture", "material_cost_per_unit": 450.0, "labor_cost_per_unit": 180.0, "unit_type": "each", "source": SOURCE},
            {"material": "vinyl", "ifc_class": "IfcCovering", "material_cost_per_unit": 15.0, "labor_cost_per_unit": 10.0, "unit_type": "m2", "source": SOURCE},
            {"material": "wood", "ifc_class": "IfcCovering", "material_cost_per_unit": 22.0, "labor_cost_per_unit": 18.0, "unit_type": "m", "source": SOURCE},
        ]

    def register_validation_rules(self) -> list[ValidationRule]:
        return [
            _InteriorFinishRule(),
            _InteriorClearanceRule(),
        ]

    def get_builder_config(self, ifc_class: str) -> dict[str, Any]:
        configs: dict[str, dict[str, Any]] = {
            "IfcCovering": {"width_mm": 600, "length_mm": 600, "thickness_mm": 19},
            "IfcFurniture": {"width_mm": 900, "height_mm": 750, "depth_mm": 350},
            "IfcCurtainWall": {"width_mm": 1200, "height_mm": 3000, "thickness_mm": 100},
            "IfcRailing": {"height_mm": 1067, "length_mm": 3000},
        }
        return configs.get(ifc_class, {})
