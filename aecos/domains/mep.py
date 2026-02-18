"""MEPDomain — HVAC ducts, piping, electrical conduits, fixtures."""

from __future__ import annotations

from typing import Any

from aecos.domains.base import DomainPlugin
from aecos.validation.rules.base import ValidationIssue, ValidationRule

SOURCE = "RSMeans 2026 Q1 estimated"


class _MEPSystemTypeRule(ValidationRule):
    """MEP elements should specify a system type."""

    @property
    def name(self) -> str:
        return "mep_system_type"

    @property
    def description(self) -> str:
        return "MEP elements should specify their system classification."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        mep_classes = {
            "IfcDuctSegment", "IfcPipeSegment", "IfcCableSegment",
            "IfcPump", "IfcFan", "IfcFlowTerminal", "IfcAirTerminal",
            "IfcSanitaryTerminal",
        }
        if ifc_class not in mep_classes:
            return []
        psets = element_data.get("psets", {})
        for pset_props in psets.values():
            if "SystemType" in pset_props or "system_type" in pset_props:
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="info",
                message=f"{ifc_class} element does not specify a system type.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add SystemType property (e.g. HVAC, Plumbing, Electrical).",
            )
        ]


class _MEPDiameterRule(ValidationRule):
    """Ducts and pipes should have a diameter or size specified."""

    @property
    def name(self) -> str:
        return "mep_size_specified"

    @property
    def description(self) -> str:
        return "Ducts and pipes must specify diameter or dimensions."

    def check(self, element_data: dict[str, Any]) -> list[ValidationIssue]:
        ifc_class = element_data.get("metadata", {}).get("IFCClass", "")
        if ifc_class not in {"IfcDuctSegment", "IfcPipeSegment"}:
            return []
        psets = element_data.get("psets", {})
        size_keys = {"diameter_mm", "width_mm", "NominalDiameter", "Diameter"}
        for pset_props in psets.values():
            if any(k in pset_props for k in size_keys):
                return []
        return [
            ValidationIssue(
                rule_name=self.name,
                severity="warning",
                message=f"{ifc_class} element does not specify diameter or size.",
                element_id=element_data.get("metadata", {}).get("GlobalId", ""),
                suggestion="Add diameter_mm or NominalDiameter property.",
            )
        ]


class MEPDomain(DomainPlugin):
    """Mechanical, Electrical, and Plumbing domain."""

    @property
    def name(self) -> str:
        return "mep"

    @property
    def description(self) -> str:
        return "MEP: HVAC ducts, piping, electrical conduits, pumps, fans, and terminals."

    @property
    def ifc_classes(self) -> list[str]:
        return [
            "IfcDuctSegment", "IfcPipeSegment", "IfcCableSegment",
            "IfcPump", "IfcFan", "IfcFlowTerminal", "IfcAirTerminal",
            "IfcSanitaryTerminal",
        ]

    def register_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template_id": "mep_round_duct_200",
                "ifc_class": "IfcDuctSegment",
                "name": "Round Duct 200mm",
                "description": "Galvanized steel round duct 200mm diameter.",
                "properties": {"diameter_mm": 200, "length_mm": 3000, "shape": "round"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcDuctSegment", "material": ["steel"], "compliance_codes": ["IMC"]},
            },
            {
                "template_id": "mep_rectangular_duct",
                "ifc_class": "IfcDuctSegment",
                "name": "Rectangular Duct 600x400",
                "description": "Galvanized steel rectangular duct 600x400mm.",
                "properties": {"width_mm": 600, "height_mm": 400, "length_mm": 3000, "shape": "rectangular"},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcDuctSegment", "material": ["steel"], "compliance_codes": ["IMC"]},
            },
            {
                "template_id": "mep_copper_pipe_50",
                "ifc_class": "IfcPipeSegment",
                "name": "Copper Pipe 50mm",
                "description": "Type L copper pipe 50mm (2 in.) for domestic water.",
                "properties": {"diameter_mm": 50, "length_mm": 6000},
                "materials": ["copper"],
                "tags": {"ifc_class": "IfcPipeSegment", "material": ["copper"], "compliance_codes": ["IPC"]},
            },
            {
                "template_id": "mep_pvc_pipe_100",
                "ifc_class": "IfcPipeSegment",
                "name": "PVC Drain Pipe 100mm",
                "description": "PVC DWV pipe 100mm (4 in.) for drainage.",
                "properties": {"diameter_mm": 100, "length_mm": 3000},
                "materials": ["pvc"],
                "tags": {"ifc_class": "IfcPipeSegment", "material": ["pvc"], "compliance_codes": ["IPC"]},
            },
            {
                "template_id": "mep_electrical_conduit",
                "ifc_class": "IfcCableSegment",
                "name": "EMT Conduit 25mm",
                "description": "Electrical metallic tubing (EMT) conduit 25mm.",
                "properties": {"diameter_mm": 25, "length_mm": 3000},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcCableSegment", "material": ["steel"], "compliance_codes": ["NEC"]},
            },
            {
                "template_id": "mep_ahu",
                "ifc_class": "IfcFan",
                "name": "Air Handling Unit",
                "description": "Rooftop air handling unit, 10-ton capacity.",
                "properties": {"capacity_tons": 10, "cfm": 4000},
                "materials": ["steel"],
                "tags": {"ifc_class": "IfcFan", "material": ["steel"]},
            },
            {
                "template_id": "mep_supply_diffuser",
                "ifc_class": "IfcAirTerminal",
                "name": "Supply Air Diffuser",
                "description": "Square ceiling supply diffuser 600x600mm.",
                "properties": {"width_mm": 600, "height_mm": 600, "cfm": 200},
                "materials": ["aluminum"],
                "tags": {"ifc_class": "IfcAirTerminal", "material": ["aluminum"]},
            },
            {
                "template_id": "mep_lavatory",
                "ifc_class": "IfcSanitaryTerminal",
                "name": "Wall-Mount Lavatory",
                "description": "ADA-compliant wall-mounted lavatory.",
                "properties": {"width_mm": 500, "depth_mm": 400},
                "materials": ["ceramic"],
                "tags": {"ifc_class": "IfcSanitaryTerminal", "material": ["ceramic"], "compliance_codes": ["ADA2010"]},
            },
        ]

    def register_compliance_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "code_name": "IMC",
                "section": "603.4",
                "title": "Minimum duct size",
                "ifc_classes": ["IfcDuctSegment"],
                "check_type": "min_value",
                "property_path": "properties.diameter_mm",
                "check_value": 75,
                "region": "US",
                "citation": "International Mechanical Code §603.4 — Minimum duct size 75 mm (3 in.).",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IMC",
                "section": "604.1",
                "title": "Duct material specification required",
                "ifc_classes": ["IfcDuctSegment"],
                "check_type": "exists",
                "property_path": "materials",
                "check_value": None,
                "region": "US",
                "citation": "IMC §604.1 — Duct material shall be specified per Table 604.1.",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IPC",
                "section": "305.4.1",
                "title": "Minimum drain pipe slope",
                "ifc_classes": ["IfcPipeSegment"],
                "check_type": "exists",
                "property_path": "materials",
                "check_value": None,
                "region": "US",
                "citation": "International Plumbing Code §305.4.1 — Drain pipe materials must be specified.",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "IPC",
                "section": "903.1",
                "title": "Pipe sizing required",
                "ifc_classes": ["IfcPipeSegment"],
                "check_type": "min_value",
                "property_path": "properties.diameter_mm",
                "check_value": 15,
                "region": "US",
                "citation": "IPC §903.1 — Minimum pipe size 15 mm (1/2 in.) for water distribution.",
                "effective_date": "2024-01-01",
            },
            {
                "code_name": "NEC",
                "section": "344.24",
                "title": "Conduit minimum trade size",
                "ifc_classes": ["IfcCableSegment"],
                "check_type": "min_value",
                "property_path": "properties.diameter_mm",
                "check_value": 16,
                "region": "US",
                "citation": "NEC Article 344.24 — Minimum conduit trade size 16 mm (1/2 in.).",
                "effective_date": "2023-01-01",
            },
            {
                "code_name": "NEC",
                "section": "300.17",
                "title": "Conduit fill requirements — conduit must have material",
                "ifc_classes": ["IfcCableSegment"],
                "check_type": "exists",
                "property_path": "materials",
                "check_value": None,
                "region": "US",
                "citation": "NEC §300.17 — Conduit materials must be specified for fill calculations.",
                "effective_date": "2023-01-01",
            },
        ]

    def register_parser_patterns(self) -> dict[str, str]:
        return {
            "duct": "IfcDuctSegment",
            "pipe": "IfcPipeSegment",
            "conduit": "IfcCableSegment",
            "pump": "IfcPump",
            "fan": "IfcFan",
            "ahu": "IfcFan",
            "diffuser": "IfcAirTerminal",
            "fixture": "IfcSanitaryTerminal",
        }

    def register_cost_data(self) -> list[dict[str, Any]]:
        return [
            {"material": "steel", "ifc_class": "IfcDuctSegment", "material_cost_per_unit": 45.0, "labor_cost_per_unit": 38.0, "unit_type": "m", "source": SOURCE},
            {"material": "copper", "ifc_class": "IfcPipeSegment", "material_cost_per_unit": 65.0, "labor_cost_per_unit": 52.0, "unit_type": "m", "source": SOURCE},
            {"material": "pvc", "ifc_class": "IfcPipeSegment", "material_cost_per_unit": 18.0, "labor_cost_per_unit": 28.0, "unit_type": "m", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcCableSegment", "material_cost_per_unit": 12.0, "labor_cost_per_unit": 35.0, "unit_type": "m", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcPump", "material_cost_per_unit": 2500.0, "labor_cost_per_unit": 800.0, "unit_type": "each", "source": SOURCE},
            {"material": "steel", "ifc_class": "IfcFan", "material_cost_per_unit": 8500.0, "labor_cost_per_unit": 2200.0, "unit_type": "each", "source": SOURCE},
            {"material": "aluminum", "ifc_class": "IfcAirTerminal", "material_cost_per_unit": 85.0, "labor_cost_per_unit": 45.0, "unit_type": "each", "source": SOURCE},
            {"material": "ceramic", "ifc_class": "IfcSanitaryTerminal", "material_cost_per_unit": 320.0, "labor_cost_per_unit": 180.0, "unit_type": "each", "source": SOURCE},
        ]

    def register_validation_rules(self) -> list[ValidationRule]:
        return [
            _MEPSystemTypeRule(),
            _MEPDiameterRule(),
        ]

    def get_builder_config(self, ifc_class: str) -> dict[str, Any]:
        configs: dict[str, dict[str, Any]] = {
            "IfcDuctSegment": {"diameter_mm": 200, "length_mm": 3000, "shape": "round"},
            "IfcPipeSegment": {"diameter_mm": 50, "length_mm": 3000},
            "IfcCableSegment": {"diameter_mm": 25, "length_mm": 3000},
            "IfcPump": {"capacity_lps": 10},
            "IfcFan": {"capacity_tons": 10, "cfm": 4000},
            "IfcAirTerminal": {"width_mm": 600, "height_mm": 600, "cfm": 200},
            "IfcSanitaryTerminal": {"width_mm": 500, "depth_mm": 400},
        }
        return configs.get(ifc_class, {})
