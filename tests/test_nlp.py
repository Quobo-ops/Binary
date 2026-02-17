"""Tests for Item 06 — Natural Language Parser.

All tests use the FallbackProvider (rule-based regex engine).
No LLM or external service required.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aecos.nlp import NLParser, ParametricSpec
from aecos.nlp.constraints import (
    extract_accessibility,
    extract_constraints,
    extract_energy,
    extract_fire,
    extract_placement,
    extract_structural,
)
from aecos.nlp.intent import classify_intent
from aecos.nlp.properties import (
    classify_ifc_class,
    extract_codes,
    extract_dimensions,
    extract_materials,
    extract_performance,
)
from aecos.nlp.providers.fallback import FallbackProvider
from aecos.nlp.providers.ollama import OllamaProvider
from aecos.nlp.resolution import apply_context, compute_confidence, detect_ambiguities
from aecos.nlp.schema import ParametricSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> NLParser:
    """Parser with fallback-only (no LLM)."""
    return NLParser(provider=FallbackProvider())


# ---------------------------------------------------------------------------
# End-to-end parse tests
# ---------------------------------------------------------------------------


class TestNLParserEndToEnd:
    """Full parse pipeline — text in, ParametricSpec out."""

    def test_fire_rated_concrete_wall(self, parser: NLParser) -> None:
        spec = parser.parse("2-hour fire-rated concrete wall, 12 feet tall")
        assert spec.ifc_class == "IfcWall"
        assert spec.performance.get("fire_rating") == "2H"
        assert spec.properties.get("height_mm") == pytest.approx(3657.6, abs=1)
        assert "concrete" in spec.materials
        assert spec.intent == "create"
        assert spec.confidence > 0

    def test_ada_accessible_door(self, parser: NLParser) -> None:
        spec = parser.parse("ADA accessible door, 36 inches wide")
        assert spec.ifc_class == "IfcDoor"
        assert spec.properties.get("width_mm") == pytest.approx(914.4, abs=1)
        assert spec.constraints.get("accessibility", {}).get("required") is True
        assert "ADA2010" in spec.compliance_codes

    def test_title_24_exterior_wall(self, parser: NLParser) -> None:
        spec = parser.parse("Title 24 compliant exterior wall, R-21 insulation")
        assert spec.ifc_class == "IfcWall"
        assert "Title-24" in spec.compliance_codes
        assert spec.performance.get("thermal_r_value") == 21
        assert spec.constraints.get("placement", {}).get("location") == "exterior"

    def test_empty_input(self, parser: NLParser) -> None:
        spec = parser.parse("")
        assert spec.confidence == 0.0
        assert len(spec.warnings) > 0

    def test_vague_input_low_confidence(self, parser: NLParser) -> None:
        spec = parser.parse("wall")
        assert spec.ifc_class == "IfcWall"
        assert spec.confidence < 0.5
        assert len(spec.warnings) > 0  # Should warn about brief input


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


class TestIntentClassification:
    def test_create_add(self) -> None:
        assert classify_intent("Add a wall") == "create"

    def test_create_build(self) -> None:
        assert classify_intent("Build a concrete column") == "create"

    def test_find_search(self) -> None:
        assert classify_intent("Find all doors") == "find"

    def test_find_list(self) -> None:
        assert classify_intent("List all 2-hour walls") == "find"

    def test_modify_update(self) -> None:
        assert classify_intent("Update the beam") == "modify"

    def test_modify_change(self) -> None:
        assert classify_intent("Change the height to 10 feet") == "modify"

    def test_validate_check(self) -> None:
        assert classify_intent("Check compliance of the wall") == "validate"

    def test_validate_verify(self) -> None:
        assert classify_intent("Verify the door meets ADA") == "validate"

    def test_default_create(self) -> None:
        assert classify_intent("concrete wall 12 feet") == "create"


# ---------------------------------------------------------------------------
# Dimension extraction and unit conversion
# ---------------------------------------------------------------------------


class TestDimensionExtraction:
    def test_feet_to_mm(self) -> None:
        dims = extract_dimensions("12 feet tall")
        assert dims["height_mm"] == pytest.approx(3657.6, abs=1)

    def test_inches_to_mm(self) -> None:
        dims = extract_dimensions("6 inch thick")
        assert dims["thickness_mm"] == pytest.approx(152.4, abs=1)

    def test_feet_tall(self) -> None:
        dims = extract_dimensions("12-foot tall")
        assert dims["height_mm"] == pytest.approx(3657.6, abs=1)

    def test_inches_wide(self) -> None:
        dims = extract_dimensions("36 inches wide")
        assert dims["width_mm"] == pytest.approx(914.4, abs=1)

    def test_meters_to_mm(self) -> None:
        dims = extract_dimensions("3 meters tall")
        assert dims["height_mm"] == pytest.approx(3000.0, abs=1)

    def test_mm_passthrough(self) -> None:
        dims = extract_dimensions("150 mm thick")
        assert dims["thickness_mm"] == pytest.approx(150.0, abs=1)

    def test_multiple_dimensions(self) -> None:
        dims = extract_dimensions("10 feet tall, 6 inches thick")
        assert "height_mm" in dims
        assert "thickness_mm" in dims

    def test_no_dimensions(self) -> None:
        dims = extract_dimensions("a concrete wall")
        assert dims == {}


# ---------------------------------------------------------------------------
# Material extraction
# ---------------------------------------------------------------------------


class TestMaterialExtraction:
    def test_single_material(self) -> None:
        assert extract_materials("concrete wall") == ["concrete"]

    def test_multiple_materials(self) -> None:
        mats = extract_materials("steel beam with concrete slab and glass panel")
        assert "steel" in mats
        assert "concrete" in mats
        assert "glass" in mats

    def test_no_materials(self) -> None:
        assert extract_materials("tall wall in corridor") == []

    def test_deduplication(self) -> None:
        mats = extract_materials("concrete wall with concrete finish")
        assert mats.count("concrete") == 1


# ---------------------------------------------------------------------------
# Performance extraction
# ---------------------------------------------------------------------------


class TestPerformanceExtraction:
    def test_fire_rating(self) -> None:
        perf = extract_performance("2-hour fire-rated")
        assert perf["fire_rating"] == "2H"

    def test_fire_rating_reverse(self) -> None:
        perf = extract_performance("fire rated for 3 hours")
        assert perf["fire_rating"] == "3H"

    def test_stc(self) -> None:
        perf = extract_performance("STC 50 rating")
        assert perf["acoustic_stc"] == 50

    def test_r_value(self) -> None:
        perf = extract_performance("R-21 insulation")
        assert perf["thermal_r_value"] == 21

    def test_no_performance(self) -> None:
        assert extract_performance("a plain wall") == {}


# ---------------------------------------------------------------------------
# IFC class mapping
# ---------------------------------------------------------------------------


class TestIFCClassMapping:
    def test_wall(self) -> None:
        assert classify_ifc_class("concrete wall") == "IfcWall"

    def test_door(self) -> None:
        assert classify_ifc_class("accessible door") == "IfcDoor"

    def test_window(self) -> None:
        assert classify_ifc_class("double-pane window") == "IfcWindow"

    def test_beam(self) -> None:
        assert classify_ifc_class("steel beam") == "IfcBeam"

    def test_column(self) -> None:
        assert classify_ifc_class("reinforced column") == "IfcColumn"

    def test_slab(self) -> None:
        assert classify_ifc_class("concrete slab") == "IfcSlab"

    def test_unknown(self) -> None:
        assert classify_ifc_class("something random") == ""


# ---------------------------------------------------------------------------
# Code reference extraction
# ---------------------------------------------------------------------------


class TestCodeExtraction:
    def test_ibc(self) -> None:
        codes = extract_codes("meets IBC requirements")
        assert "IBC2024" in codes

    def test_ada(self) -> None:
        codes = extract_codes("ADA accessible")
        assert "ADA2010" in codes

    def test_title_24(self) -> None:
        codes = extract_codes("Title 24 compliant")
        assert "Title-24" in codes

    def test_cbc(self) -> None:
        codes = extract_codes("CBC 2025 fire rating")
        assert "CBC2025" in codes

    def test_section_reference(self) -> None:
        codes = extract_codes("per IBC-703")
        assert any("IBC" in c for c in codes)

    def test_no_codes(self) -> None:
        assert extract_codes("plain concrete wall") == []


# ---------------------------------------------------------------------------
# Constraint parsing
# ---------------------------------------------------------------------------


class TestConstraintParsing:
    def test_accessibility(self) -> None:
        c = extract_constraints("ADA accessible door")
        assert "accessibility" in c
        assert c["accessibility"]["required"] is True

    def test_energy(self) -> None:
        c = extract_constraints("Title 24 energy efficient wall")
        assert "energy_code" in c

    def test_fire(self) -> None:
        c = extract_constraints("2-hour fire-rated wall")
        assert "fire" in c
        assert c["fire"]["duration_hours"] == 2

    def test_structural(self) -> None:
        c = extract_constraints("load-bearing reinforced wall")
        assert "structural" in c
        assert c["structural"]["load_bearing"] is True
        assert c["structural"]["reinforced"] is True

    def test_placement_exterior(self) -> None:
        c = extract_constraints("exterior wall")
        assert c.get("placement", {}).get("location") == "exterior"

    def test_placement_between(self) -> None:
        c = extract_constraints("wall between Office A and Office B")
        assert "placement" in c
        assert c["placement"]["between"] == ["Office A", "Office B"]


# ---------------------------------------------------------------------------
# Confidence scoring and ambiguity detection
# ---------------------------------------------------------------------------


class TestConfidenceAndAmbiguity:
    def test_high_confidence_rich_input(self, parser: NLParser) -> None:
        spec = parser.parse(
            "Add a 2-hour fire-rated concrete wall, 12 feet tall, "
            "per IBC requirements"
        )
        assert spec.confidence >= 0.7

    def test_low_confidence_vague_input(self, parser: NLParser) -> None:
        spec = parser.parse("wall")
        assert spec.confidence < 0.5

    def test_ambiguity_no_ifc_class(self) -> None:
        spec = ParametricSpec()
        warnings = detect_ambiguities(spec, "something vague")
        assert any("IFC" in w for w in warnings)

    def test_ambiguity_brief_input(self) -> None:
        spec = ParametricSpec(ifc_class="IfcWall")
        warnings = detect_ambiguities(spec, "wall")
        assert any("brief" in w.lower() for w in warnings)

    def test_ambiguity_fire_no_duration(self) -> None:
        spec = ParametricSpec(
            ifc_class="IfcWall",
            performance={"fire_rating": "rated"},
        )
        warnings = detect_ambiguities(spec, "fire rated wall")
        assert any("duration" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Context injection
# ---------------------------------------------------------------------------


class TestContextInjection:
    def test_california_jurisdiction(self, parser: NLParser) -> None:
        spec = parser.parse(
            "exterior concrete wall",
            context={"jurisdiction": "California"},
        )
        assert "CBC2025" in spec.compliance_codes
        assert "Title-24" in spec.compliance_codes

    def test_climate_zone(self, parser: NLParser) -> None:
        spec = parser.parse(
            "exterior wall with insulation",
            context={"climate_zone": "4A"},
        )
        energy = spec.constraints.get("energy_code", {})
        assert energy.get("climate_zone") == "4A"

    def test_project_type(self, parser: NLParser) -> None:
        spec = parser.parse(
            "concrete wall",
            context={"project_type": "office_building"},
        )
        assert spec.constraints.get("project_type") == "office_building"


# ---------------------------------------------------------------------------
# LLM fallback behaviour
# ---------------------------------------------------------------------------


class TestLLMFallback:
    def test_ollama_unavailable_uses_fallback(self) -> None:
        """When OllamaProvider is not available, fallback engine is used."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False
        mock_provider.parse_with_llm.return_value = None

        parser = NLParser(provider=mock_provider)
        spec = parser.parse("2-hour fire-rated concrete wall")

        # Should still produce a valid result via fallback
        assert spec.ifc_class == "IfcWall"
        assert spec.performance.get("fire_rating") == "2H"
        assert "concrete" in spec.materials

    def test_ollama_returns_none_uses_fallback(self) -> None:
        """When LLM returns None, fallback engine is used."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.parse_with_llm.return_value = None

        parser = NLParser(provider=mock_provider)
        spec = parser.parse("concrete column 10 feet tall")

        assert spec.ifc_class == "IfcColumn"
        assert "concrete" in spec.materials

    def test_ollama_returns_invalid_json_uses_fallback(self) -> None:
        """When LLM returns invalid JSON, fallback engine is used."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.parse_with_llm.return_value = "not valid json {{"

        parser = NLParser(provider=mock_provider)
        spec = parser.parse("steel beam")

        assert spec.ifc_class == "IfcBeam"
        assert "steel" in spec.materials

    def test_fallback_provider_always_available(self) -> None:
        fb = FallbackProvider()
        assert fb.is_available() is True
        assert fb.parse_with_llm("anything") is None


# ---------------------------------------------------------------------------
# ParametricSpec model
# ---------------------------------------------------------------------------


class TestParametricSpec:
    def test_defaults(self) -> None:
        spec = ParametricSpec()
        assert spec.intent == "create"
        assert spec.ifc_class == ""
        assert spec.properties == {}
        assert spec.materials == []
        assert spec.performance == {}
        assert spec.constraints == {}
        assert spec.compliance_codes == []
        assert spec.confidence == 0.0
        assert spec.warnings == []

    def test_serialisation(self) -> None:
        spec = ParametricSpec(
            intent="create",
            ifc_class="IfcWall",
            properties={"height_mm": 3658.0},
            materials=["concrete"],
            performance={"fire_rating": "2H"},
            confidence=0.85,
        )
        data = spec.model_dump()
        assert data["ifc_class"] == "IfcWall"
        assert data["properties"]["height_mm"] == 3658.0
        assert data["confidence"] == 0.85
