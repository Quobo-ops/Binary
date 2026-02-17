"""Tests for Item 09 — Clash & Validation Suite.

Covers: Validator, all rule types, clash detection, and reports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aecos.generation.generator import ElementGenerator
from aecos.nlp.schema import ParametricSpec
from aecos.validation.clash import ClashDetector, ClashResult
from aecos.validation.report import ValidationReport
from aecos.validation.rules.base import ValidationIssue
from aecos.validation.validator import Validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wall_folder(tmp_path: Path, global_id: str = "WALL001", **dim_overrides) -> Path:
    """Create a well-formed wall element folder."""
    gen = ElementGenerator(tmp_path)
    dims = {"thickness_mm": 200.0, "height_mm": 3000.0, "length_mm": 5000.0}
    dims.update(dim_overrides)
    spec = ParametricSpec(
        ifc_class="IfcWall",
        name=f"Wall {global_id}",
        properties=dims,
        materials=["concrete"],
        performance={"fire_rating": "2H"},
    )
    return gen.generate(spec)


def _make_door_folder(tmp_path: Path) -> Path:
    gen = ElementGenerator(tmp_path)
    spec = ParametricSpec(
        ifc_class="IfcDoor",
        name="Test Door",
        properties={"width_mm": 914.0, "height_mm": 2134.0},
        materials=["wood"],
    )
    return gen.generate(spec)


def _make_beam_folder(tmp_path: Path, **overrides) -> Path:
    gen = ElementGenerator(tmp_path)
    dims = {"depth_mm": 500.0, "width_mm": 300.0, "length_mm": 6000.0}
    dims.update(overrides)
    spec = ParametricSpec(
        ifc_class="IfcBeam",
        properties=dims,
        materials=["steel"],
    )
    return gen.generate(spec)


# ---------------------------------------------------------------------------
# Validator - Full Pipeline
# ---------------------------------------------------------------------------

class TestValidator:
    """Test the Validator end-to-end."""

    def test_validate_well_formed_wall(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        v = Validator()
        report = v.validate(folder)
        assert report.status == "passed"
        # No errors expected
        errors = [i for i in report.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_validate_returns_report(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        v = Validator()
        report = v.validate(folder)
        assert isinstance(report, ValidationReport)
        assert report.element_id != ""
        assert report.ifc_class == "IfcWall"

    def test_default_rules_loaded(self):
        v = Validator()
        assert len(v.rules) > 0

    def test_validate_door(self, tmp_path: Path):
        folder = _make_door_folder(tmp_path)
        v = Validator()
        report = v.validate(folder)
        # Door should pass basic validation
        assert report.status in ("passed", "warnings")


# ---------------------------------------------------------------------------
# Semantic Rules
# ---------------------------------------------------------------------------

class TestSemanticRules:
    """Test semantic validation rules."""

    def test_missing_required_thickness(self, tmp_path: Path):
        """Wall without thickness_mm → semantic rule catches it."""
        gen = ElementGenerator(tmp_path)
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "length_mm": 5000},
            # thickness_mm intentionally omitted
        )
        folder = gen.generate(spec)

        # Manually remove thickness from Dimensions pset to trigger check
        psets_path = folder / "properties" / "psets.json"
        psets = json.loads(psets_path.read_text())
        if "thickness_mm" in psets.get("Dimensions", {}):
            del psets["Dimensions"]["thickness_mm"]
        psets_path.write_text(json.dumps(psets, indent=2))

        v = Validator()
        report = v.validate(folder)
        rule_names = [i.rule_name for i in report.issues]
        assert "semantic.required_properties" in rule_names

    def test_fire_rating_material_mismatch(self, tmp_path: Path):
        """Fire rating exceeding material capability → warning."""
        gen = ElementGenerator(tmp_path)
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 200, "height_mm": 3000, "length_mm": 5000},
            materials=["glass"],  # Glass cannot achieve fire rating
            performance={"fire_rating": "2H"},
        )
        folder = gen.generate(spec)

        v = Validator()
        report = v.validate(folder)
        fire_issues = [i for i in report.issues if i.rule_name == "semantic.material_fire_rating"]
        assert len(fire_issues) > 0
        assert fire_issues[0].severity == "warning"


# ---------------------------------------------------------------------------
# Geometric Rules
# ---------------------------------------------------------------------------

class TestGeometricRules:
    """Test geometric validation rules."""

    def test_door_clearance_warning(self, tmp_path: Path):
        """Door without swing space → warning."""
        gen = ElementGenerator(tmp_path)
        spec = ParametricSpec(
            ifc_class="IfcDoor",
            properties={"width_mm": 600, "height_mm": 2134},  # Narrow door
            materials=["wood"],
        )
        folder = gen.generate(spec)

        v = Validator()
        report = v.validate(folder)
        clearance_issues = [i for i in report.issues if i.rule_name == "geometric.door_clearance"]
        assert len(clearance_issues) > 0

    def test_valid_bounding_box(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        v = Validator()
        report = v.validate(folder)
        bb_issues = [i for i in report.issues if i.rule_name == "geometric.bounding_box_valid"]
        assert len(bb_issues) == 0


# ---------------------------------------------------------------------------
# Constructability Rules
# ---------------------------------------------------------------------------

class TestConstructabilityRules:
    """Test constructability validation rules."""

    def test_layer_ordering_warning(self, tmp_path: Path):
        """Impossible layer ordering → warning."""
        gen = ElementGenerator(tmp_path)
        # Interior material before exterior = bad ordering
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 300, "height_mm": 3000, "length_mm": 5000},
            materials=["gypsum", "insulation", "brick"],  # Wrong order
        )
        folder = gen.generate(spec)

        v = Validator()
        report = v.validate(folder)
        layer_issues = [i for i in report.issues if i.rule_name == "constructability.layer_ordering"]
        assert len(layer_issues) > 0

    def test_beam_span_depth_warning(self, tmp_path: Path):
        """Excessive beam span/depth ratio → warning."""
        folder = _make_beam_folder(tmp_path, depth_mm=100.0, length_mm=10000.0)

        v = Validator()
        report = v.validate(folder)
        span_issues = [i for i in report.issues if i.rule_name == "constructability.beam_span_depth"]
        assert len(span_issues) > 0


# ---------------------------------------------------------------------------
# Clash Detection
# ---------------------------------------------------------------------------

class TestClashDetection:
    """Test the ClashDetector."""

    def test_overlapping_boxes_detected(self):
        """Two overlapping bounding boxes → clash reported."""
        detector = ClashDetector(tolerance_m=0.0)
        elements = [
            {
                "metadata": {"GlobalId": "A"},
                "geometry": {
                    "bounding_box": {
                        "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                        "max_x": 2.0, "max_y": 1.0, "max_z": 3.0,
                    }
                },
            },
            {
                "metadata": {"GlobalId": "B"},
                "geometry": {
                    "bounding_box": {
                        "min_x": 1.0, "min_y": 0.0, "min_z": 0.0,
                        "max_x": 3.0, "max_y": 1.0, "max_z": 3.0,
                    }
                },
            },
        ]
        clashes = detector.detect(elements)
        assert len(clashes) > 0
        assert clashes[0].element_a_id == "A"
        assert clashes[0].element_b_id == "B"
        assert clashes[0].overlap_volume > 0

    def test_non_overlapping_no_clash(self):
        """Two non-overlapping elements → no clash."""
        detector = ClashDetector(tolerance_m=0.0)
        elements = [
            {
                "metadata": {"GlobalId": "A"},
                "geometry": {
                    "bounding_box": {
                        "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
                        "max_x": 1.0, "max_y": 1.0, "max_z": 1.0,
                    }
                },
            },
            {
                "metadata": {"GlobalId": "B"},
                "geometry": {
                    "bounding_box": {
                        "min_x": 5.0, "min_y": 5.0, "min_z": 5.0,
                        "max_x": 6.0, "max_y": 6.0, "max_z": 6.0,
                    }
                },
            },
        ]
        clashes = detector.detect(elements)
        assert len(clashes) == 0

    def test_clash_with_context(self, tmp_path: Path):
        """Validate with context elements triggers clash detection."""
        folder_a = _make_wall_folder(tmp_path / "a")
        folder_b = _make_wall_folder(tmp_path / "b")

        v = Validator()
        report = v.validate(folder_a, context_elements=[folder_b])
        assert isinstance(report, ValidationReport)


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------

class TestValidationReport:
    """Test ValidationReport model and Markdown generation."""

    def test_passed_report(self):
        report = ValidationReport(
            element_id="ELEM001",
            ifc_class="IfcWall",
            status="passed",
        )
        md = report.to_markdown()
        assert "# Validation Report" in md
        assert "PASSED" in md
        assert "ELEM001" in md

    def test_failed_report_with_issues(self):
        report = ValidationReport(
            element_id="ELEM002",
            ifc_class="IfcWall",
            status="failed",
            issues=[
                ValidationIssue(
                    rule_name="test.rule",
                    severity="error",
                    message="Something is wrong",
                    element_id="ELEM002",
                    suggestion="Fix it",
                ),
            ],
        )
        md = report.to_markdown()
        assert "FAILED" in md
        assert "Something is wrong" in md
        assert "Fix it" in md

    def test_to_json(self):
        report = ValidationReport(
            element_id="ELEM003",
            ifc_class="IfcDoor",
            status="warnings",
            issues=[
                ValidationIssue("r1", "warning", "Minor issue"),
            ],
        )
        data = json.loads(report.to_json())
        assert data["status"] == "warnings"
        assert len(data["issues"]) == 1

    def test_to_markdown_valid_markdown(self, tmp_path: Path):
        """Ensure to_markdown produces valid Markdown."""
        folder = _make_wall_folder(tmp_path)
        v = Validator()
        report = v.validate(folder)
        md = report.to_markdown()
        assert md.startswith("# Validation Report")
        assert "**IFC Class:**" in md
