"""StructuralDomain — beams, columns, slabs, foundations."""

from __future__ import annotations

from typing import Any

from aecos.domains.base import DomainPlugin
from aecos.validation.rules.base import ValidationIssue, ValidationRule

SOURCE = "RSMeans 2026 Q1 estimated"


class _StructuralLoadPathRule(ValidationRule):
    """Structural elements should have load-bearing property specified."""

    @property
    def name(self) -> str:
        return "structural_load_path"

    @property
    def description(self) -> str:
        return "Structural elements must specify load-bearing status."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        structural_classes = {"IfcBeam", "IfcColumn", "IfcSlab", "IfcFooting", "IfcPile", "IfcMember"}
        if ifc_class not in structural_classes:
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "LoadBearing" in pset_props:
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message=f"{ifc_class} element does not specify load-bearing status.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add LoadBearing property to element property sets.",
            )
        ]


class _StructuralProfileRule(ValidationRule):
    """Beams and columns should have a profile type specified."""

    @property
    def name(self) -> str:
        return "structural_profile_spec"

    @property
    def description(self) -> str:
        return "Beams and columns should specify a structural profile type."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class not in {"IfcBeam", "IfcColumn"}:
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "profile_type" in pset_props or "ProfileType" in pset_props:
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="info",
                message=f"{ifc_class} element does not specify a profile type.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Specify profile_type (e.g. W, HSS, or custom) for structural analysis.",
            )
        ]


class StructuralDomain(DomainPlugin):
    """Structural engineering domain — beams, columns, slabs, foundations."""

    @property
    def name(self) -> str:
        return "structural"

    @property
    def description(self) -> str:
        return "Structural engineering: beams, columns, slabs, footings, piles, and members."

    @property
    def ifc_classes(self) -> list[str]:
        return ["IfcBeam", "IfcColumn", "IfcSlab", "IfcFooting", "IfcPile", "IfcMember"]

    def register_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template_id": "structural_w12x26_beam",
                "ifc_class": "IfcBeam",
                "name": "Steel W12x26 Beam",
                "description": "Wide-flange steel beam W12x26 for typical floor framing.",
                "properties": {"depth_mm": 310, "width_mm": 165, "length_mm": 6000, "profile_type": "W12x26"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcBeam", "material": ["steel"], "compliance_codes": ["AISC360"]},
            },
            {
                "template_id": "structural_w16x40_beam",
                "ifc_class": "IfcBeam",
                "name": "Steel W16x40 Beam",
                "description": "Wide-flange steel beam W16x40 for heavy floor loads.",
                "properties": {"depth_mm": 407, "width_mm": 178, "length_mm": 9000, "profile_type": "W16x40"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcBeam", "material": ["steel"], "compliance_codes": ["AISC360"]},
            },
            {
                "template_id": "structural_concrete_beam",
                "ifc_class": "IfcBeam",
                "name": "Reinforced Concrete Beam",
                "description": "Cast-in-place reinforced concrete beam.",
                "properties": {"depth_mm": 600, "width_mm": 300, "length_mm": 7000},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcBeam", "material": ["concrete"], "compliance_codes": ["ACI318"]},
            },
            {
                "template_id": "structural_concrete_column",
                "ifc_class": "IfcColumn",
                "name": "Reinforced Concrete Column",
                "description": "Cast-in-place reinforced concrete column 450x450mm.",
                "properties": {"width_mm": 450, "depth_mm": 450, "height_mm": 3600},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcColumn", "material": ["concrete"], "compliance_codes": ["ACI318"]},
            },
            {
                "template_id": "structural_steel_column",
                "ifc_class": "IfcColumn",
                "name": "Steel W10x49 Column",
                "description": "Wide-flange steel column W10x49.",
                "properties": {"width_mm": 254, "depth_mm": 254, "height_mm": 3600, "profile_type": "W10x49"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcColumn", "material": ["steel"], "compliance_codes": ["AISC360"]},
            },
            {
                "template_id": "structural_concrete_slab_150",
                "ifc_class": "IfcSlab",
                "name": "Concrete Slab 150mm",
                "description": "150mm reinforced concrete floor slab on metal deck.",
                "properties": {"thickness_mm": 150, "width_mm": 3000, "length_mm": 6000},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcSlab", "material": ["concrete"], "compliance_codes": ["ACI318"]},
            },
            {
                "template_id": "structural_concrete_slab_200",
                "ifc_class": "IfcSlab",
                "name": "Concrete Slab 200mm",
                "description": "200mm reinforced concrete slab for heavy loads.",
                "properties": {"thickness_mm": 200, "width_mm": 3000, "length_mm": 6000},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcSlab", "material": ["concrete"], "compliance_codes": ["ACI318"]},
            },
            {
                "template_id": "structural_spread_footing",
                "ifc_class": "IfcFooting",
                "name": "Spread Footing",
                "description": "Reinforced concrete spread footing 1200x1200x400mm.",
                "properties": {"width_mm": 1200, "length_mm": 1200, "thickness_mm": 400},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcFooting", "material": ["concrete"], "compliance_codes": ["ACI318"]},
            },
            {
                "template_id": "structural_strip_footing",
                "ifc_class": "IfcFooting",
                "name": "Strip Footing",
                "description": "Continuous strip footing 600mm wide x 300mm deep.",
                "properties": {"width_mm": 600, "length_mm": 6000, "thickness_mm": 300},
                "materials": ["concrete"],
                "tags": {"ifc_class": "IfcFooting", "material": ["concrete"], "compliance_codes": ["ACI318"]},
            },
            {
                "template_id": "structural_driven_pile",
                "ifc_class": "IfcPile",
                "name": "Driven Steel H-Pile",
                "description": "HP12x53 driven steel pile for deep foundations.",
                "properties": {"width_mm": 305, "depth_mm": 305, "length_mm": 15000, "profile_type": "HP12x53"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcPile", "material": ["steel"], "compliance_codes": ["IBC2024"]},
            },
        ]

    def register_compliance_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "code_name": "ACI318-19",
                "section": "9.3.1",
                "title": "Minimum beam depth for deflection control",
                "ifc_classes": ["IfcBeam"],
                "check_type": "min_value",
                "property_path": "properties.depth_mm",
                "check_value": 200,
                "region": "US",
                "citation": "ACI 318-19 Table 9.3.1.1 — Minimum beam depth for members not supporting partitions.",
                "effective_date": "2019-05-01",
            },
            {
                "code_name": "ACI318-19",
                "section": "10.5.1",
                "title": "Minimum column dimension",
                "ifc_classes": ["IfcColumn"],
                "check_type": "min_value",
                "property_path": "properties.width_mm",
                "check_value": 250,
                "region": "US",
                "citation": "ACI 318-19 §10.5.1 — Minimum column cross-section dimension shall be 250 mm.",
                "effective_date": "2019-05-01",
            },
            {
                "code_name": "ACI318-19",
                "section": "7.3.1",
                "title": "Minimum slab thickness for deflection control",
                "ifc_classes": ["IfcSlab"],
                "check_type": "min_value",
                "property_path": "properties.thickness_mm",
                "check_value": 100,
                "region": "US",
                "citation": "ACI 318-19 Table 7.3.1.1 — Minimum thickness of one-way slabs.",
                "effective_date": "2019-05-01",
            },
            {
                "code_name": "AISC360",
                "section": "B4.1",
                "title": "Steel member width-to-thickness ratio",
                "ifc_classes": ["IfcBeam", "IfcColumn"],
                "check_type": "exists",
                "property_path": "properties.profile_type",
                "check_value": None,
                "region": "US",
                "citation": "AISC 360 §B4.1 — Steel members must have designated profile type for classification.",
                "effective_date": "2022-01-01",
            },
            {
                "code_name": "IBC2024",
                "section": "1809.5",
                "title": "Minimum footing depth below frost line",
                "ifc_classes": ["IfcFooting"],
                "check_type": "min_value",
                "property_path": "properties.thickness_mm",
                "check_value": 150,
                "region": "US",
                "citation": "IBC 2024 §1809.5 — Footings shall have a minimum thickness of 150 mm (6 in.).",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IBC2024",
                "section": "1810.3.2",
                "title": "Minimum pile diameter/width",
                "ifc_classes": ["IfcPile"],
                "check_type": "min_value",
                "property_path": "properties.width_mm",
                "check_value": 200,
                "region": "US",
                "citation": "IBC 2024 §1810.3.2 — Driven piles shall have a minimum nominal width of 200 mm (8 in.).",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "ASCE7-22",
                "section": "12.8.6",
                "title": "Seismic drift limits — structural elements must have materials",
                "ifc_classes": ["IfcBeam", "IfcColumn"],
                "check_type": "exists",
                "property_path": "materials",
                "check_value": None,
                "region": "US",
                "citation": "ASCE 7-22 §12.8.6 — Structural elements in seismic categories require material specification for drift analysis.",
                "effective_date": "2022-01-01",
            },
            {
                "code_name": "ACI318-19",
                "section": "11.3.1",
                "title": "Minimum bearing wall thickness",
                "ifc_classes": ["IfcWall"],
                "check_type": "min_value",
                "property_path": "properties.thickness_mm",
                "check_value": 100,
                "region": "US",
                "citation": "ACI 318-19 §11.3.1 — Minimum concrete bearing wall thickness for structural adequacy.",
                "effective_date": "2019-05-01",
            },
        ]

    def register_parser_patterns(self) -> dict[str, str]:
        return {
            "beam": "IfcBeam",
            "girder": "IfcBeam",
            "joist": "IfcBeam",
            "column": "IfcColumn",
            "foundation": "IfcFooting",
            "footing": "IfcFooting",
            "pile": "IfcPile",
        }

    def register_cost_data(self) -> list[dict[str, Any]]:
        return [
            {"material": "steel", "ifc_class": "IfcBeam", "material_cost_per_unit": 180.0, "labor_cost_per_unit": 120.0, "unit_type": "m", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcBeam", "material_cost_per_unit": 150.0, "labor_cost_per_unit": 95.0, "unit_type": "m", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcColumn", "material_cost_per_unit": 480.0, "labor_cost_per_unit": 280.0, "unit_type": "m3", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcColumn", "material_cost_per_unit": 320.0, "labor_cost_per_unit": 210.0, "unit_type": "m3", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcSlab", "material_cost_per_unit": 95.0, "labor_cost_per_unit": 70.0, "unit_type": "m2", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcFooting", "material_cost_per_unit": 280.0, "labor_cost_per_unit": 190.0, "unit_type": "m3", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcPile", "material_cost_per_unit": 350.0, "labor_cost_per_unit": 250.0, "unit_type": "m", "source": SOURCE},
            {"material": "concrete", "ifc_class": "IfcPile", "material_cost_per_unit": 220.0, "labor_cost_per_unit": 180.0, "unit_type": "m", "source": SOURCE},
        ]

    def register_validation_rules(self) -> list[ValidationRule]:
        return [
            _StructuralLoadPathRule(),
            _StructuralProfileRule(),
        ]

    def get_builder_config(self, ifc_class: str) -> dict[str, Any]:
        configs: dict[str, dict[str, Any]] = {
            "IfcBeam": {"depth_mm": 500, "width_mm": 300, "length_mm": 6000, "profile_type": "W", "load_bearing": True},
            "IfcColumn": {"width_mm": 450, "depth_mm": 450, "height_mm": 3600, "load_bearing": True},
            "IfcSlab": {"thickness_mm": 150, "width_mm": 3000, "length_mm": 6000},
            "IfcFooting": {"width_mm": 1200, "length_mm": 1200, "thickness_mm": 400},
            "IfcPile": {"width_mm": 305, "length_mm": 15000},
            "IfcMember": {"width_mm": 200, "depth_mm": 200, "length_mm": 3000},
        }
        return configs.get(ifc_class, {})
