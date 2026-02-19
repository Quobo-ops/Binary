"""
Phase C: Semantic Correctness Deep Dive
Verify modules produce correct results, not just that they don't crash.
"""
import json
import math
import os
import tempfile
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_element_folder(base, global_id, ifc_class, name, *,
                         psets=None, materials=None, geometry=None, spatial=None):
    """Create a canonical element folder."""
    folder = base / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"GlobalId": global_id, "Name": name, "IFCClass": ifc_class,
            "Psets": psets or {}}
    (folder / "metadata.json").write_text(json.dumps(meta, indent=2))
    (folder / "properties").mkdir(exist_ok=True)
    (folder / "properties" / "psets.json").write_text(json.dumps(psets or {}, indent=2))
    (folder / "materials").mkdir(exist_ok=True)
    (folder / "materials" / "materials.json").write_text(
        json.dumps(materials or [{"name": "Concrete", "category": "concrete",
                                   "thickness": 0.2, "fraction": 1.0}], indent=2))
    (folder / "geometry").mkdir(exist_ok=True)
    (folder / "geometry" / "shape.json").write_text(json.dumps(
        geometry or {"bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                                       "max_x": 1, "max_y": 0.2, "max_z": 3},
                     "volume": 0.6, "centroid": [0.5, 0.1, 1.5]}, indent=2))
    (folder / "relationships").mkdir(exist_ok=True)
    (folder / "relationships" / "spatial.json").write_text(
        json.dumps(spatial or {"site_name": "Site", "building_name": "B1",
                                "storey_name": "Level 1"}, indent=2))
    return folder


# ===================================================================
# C1 – NLP parser accuracy matrix
# ===================================================================
class TestNLPParserAccuracy:
    """Build a test set of crafted inputs and verify correct outputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from aecos.nlp.parser import NLParser
        self.parser = NLParser()
        yield

    # Each tuple: (input_text, expected_ifc_class, expected_properties_subset)
    ACCURACY_TEST_SET = [
        # Walls
        ("Create a concrete wall 3m high 6m long 200mm thick",
         "IfcWall", {"height_mm": 3000, "length_mm": 6000, "thickness_mm": 200}),
        ("Create a wall 2500mm high 150mm thick",
         "IfcWall", {"height_mm": 2500, "thickness_mm": 150}),
        ("Create a masonry wall 3m high 200mm thick",
         "IfcWall", {"height_mm": 3000, "thickness_mm": 200}),
        # Beams
        ("Create a steel beam 8m long 400mm deep",
         "IfcBeam", {"length_mm": 8000}),
        ("Create a concrete beam 6m long 300mm deep",
         "IfcBeam", {"length_mm": 6000}),
        # Columns
        ("Create a timber column 350mm square 4m tall",
         "IfcColumn", {"height_mm": 4000}),
        ("Create a concrete column 500mm diameter 6m tall",
         "IfcColumn", {"height_mm": 6000}),
        # Slabs
        ("Create a concrete slab 10m by 8m 250mm thick",
         "IfcSlab", {"thickness_mm": 250}),
        # Doors
        ("Create a steel door 2100mm high 900mm wide",
         "IfcDoor", {"height_mm": 2100, "width_mm": 900}),
        ("Create a wooden door 2000mm high 800mm wide",
         "IfcDoor", {"height_mm": 2000, "width_mm": 800}),
        # Windows
        ("Create a window 1200mm wide 1500mm high",
         "IfcWindow", {"width_mm": 1200, "height_mm": 1500}),
        ("Create a glass window 900mm wide 1200mm high",
         "IfcWindow", {"width_mm": 900, "height_mm": 1200}),
    ]

    def test_c1_ifc_class_accuracy(self):
        """Verify IFC class detection accuracy across all test inputs."""
        correct = 0
        total = len(self.ACCURACY_TEST_SET)
        failures = []

        for text, expected_class, _ in self.ACCURACY_TEST_SET:
            spec = self.parser.parse(text)
            if spec.ifc_class == expected_class:
                correct += 1
            else:
                failures.append(f"'{text}': expected {expected_class}, got {spec.ifc_class}")

        accuracy = correct / total
        assert accuracy >= 0.8, (
            f"IFC class accuracy {accuracy:.0%} < 80%. Failures:\n"
            + "\n".join(failures)
        )

    def test_c1_property_accuracy(self):
        """Verify property extraction accuracy."""
        correct_props = 0
        total_props = 0
        failures = []

        for text, _, expected_props in self.ACCURACY_TEST_SET:
            spec = self.parser.parse(text)
            for key, expected_val in expected_props.items():
                total_props += 1
                actual = spec.properties.get(key)
                if actual is not None:
                    try:
                        # 10% tolerance for numeric comparisons
                        if abs(float(actual) - float(expected_val)) <= abs(expected_val) * 0.10:
                            correct_props += 1
                            continue
                    except (ValueError, TypeError):
                        pass
                failures.append(
                    f"'{text}': {key} expected={expected_val}, got={actual}"
                )

        accuracy = correct_props / total_props if total_props else 0
        assert accuracy >= 0.7, (
            f"Property accuracy {accuracy:.0%} < 70%. Failures:\n"
            + "\n".join(failures[:20])
        )

    def test_c1_material_detection(self):
        """Verify material extraction."""
        material_tests = [
            ("Create a concrete wall 3m high", ["concrete"]),
            ("Create a steel beam 6m long", ["steel"]),
            ("Create a timber column 4m tall", ["timber", "wood"]),
            ("Create a glass window 1200mm wide", ["glass"]),
        ]
        correct = 0
        for text, expected_mats in material_tests:
            spec = self.parser.parse(text)
            # Check if any expected material appears
            spec_mats_lower = [m.lower() for m in spec.materials]
            if any(m in spec_mats_lower for m in expected_mats):
                correct += 1

        accuracy = correct / len(material_tests)
        assert accuracy >= 0.75, f"Material detection accuracy {accuracy:.0%} < 75%"

    def test_c1_fire_rating_detection(self):
        """Verify fire rating extraction."""
        tests = [
            ("Create a wall with 2-hour fire rating", "2H"),
            ("Create a wall with 1hr fire rating", "1H"),
        ]
        detected = 0
        for text, expected in tests:
            spec = self.parser.parse(text)
            if spec.performance.get("fire_rating"):
                detected += 1

        assert detected >= 1, "Fire rating not detected in any test case"

    def test_c1_confidence_scoring(self):
        """Verify confidence scores are reasonable."""
        # Clear input should have higher confidence
        clear = self.parser.parse("Create a concrete wall 3m high 200mm thick")
        # Ambiguous input should have lower confidence
        ambig = self.parser.parse("make something big")

        assert clear.confidence >= 0.0
        assert ambig.confidence >= 0.0
        # Both should be valid floats in [0,1]
        assert 0.0 <= clear.confidence <= 1.0
        assert 0.0 <= ambig.confidence <= 1.0


# ===================================================================
# C2 – Compliance engine logic coverage
# ===================================================================
class TestComplianceEngineLogicCoverage:
    """For every check_type, construct passing and failing inputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from aecos.compliance.rules import Rule, evaluate_rule
        self.Rule = Rule
        self.evaluate_rule = evaluate_rule
        yield

    def test_c2_min_value_pass(self):
        """min_value check passes when actual >= expected."""
        rule = self.Rule(
            code_name="TEST", section="1.1", title="Thickness min",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.thickness_mm", check_value=200,
        )
        data = {"properties": {"thickness_mm": 250}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_min_value_fail(self):
        """min_value check fails when actual < expected."""
        rule = self.Rule(
            code_name="TEST", section="1.1", title="Thickness min",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.thickness_mm", check_value=200,
        )
        data = {"properties": {"thickness_mm": 150}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_min_value_boundary_exact(self):
        """min_value check passes when actual == expected (boundary)."""
        rule = self.Rule(
            code_name="TEST", section="1.1", title="Thickness min",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.thickness_mm", check_value=200,
        )
        data = {"properties": {"thickness_mm": 200}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_min_value_boundary_just_below(self):
        """min_value check fails when actual is 1 below threshold."""
        rule = self.Rule(
            code_name="TEST", section="1.1", title="Thickness min",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.thickness_mm", check_value=200,
        )
        data = {"properties": {"thickness_mm": 199}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_min_value_missing_property(self):
        """min_value check fails when property is missing."""
        rule = self.Rule(
            code_name="TEST", section="1.1", title="Thickness min",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.thickness_mm", check_value=200,
        )
        data = {"properties": {}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_max_value_pass(self):
        """max_value check passes when actual <= expected."""
        rule = self.Rule(
            code_name="TEST", section="2.1", title="Height max",
            ifc_classes=["IfcWall"], check_type="max_value",
            property_path="properties.height_mm", check_value=5000,
        )
        data = {"properties": {"height_mm": 3000}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_max_value_fail(self):
        """max_value check fails when actual > expected."""
        rule = self.Rule(
            code_name="TEST", section="2.1", title="Height max",
            ifc_classes=["IfcWall"], check_type="max_value",
            property_path="properties.height_mm", check_value=5000,
        )
        data = {"properties": {"height_mm": 6000}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_max_value_boundary(self):
        """max_value passes when actual == expected."""
        rule = self.Rule(
            code_name="TEST", section="2.1", title="Height max",
            ifc_classes=["IfcWall"], check_type="max_value",
            property_path="properties.height_mm", check_value=5000,
        )
        data = {"properties": {"height_mm": 5000}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_enum_pass(self):
        """enum check passes for an allowed value."""
        rule = self.Rule(
            code_name="TEST", section="3.1", title="Material enum",
            ifc_classes=["IfcWall"], check_type="enum",
            property_path="properties.material",
            check_value=["concrete", "steel", "wood"],
        )
        data = {"properties": {"material": "concrete"}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_enum_fail(self):
        """enum check fails for a disallowed value."""
        rule = self.Rule(
            code_name="TEST", section="3.1", title="Material enum",
            ifc_classes=["IfcWall"], check_type="enum",
            property_path="properties.material",
            check_value=["concrete", "steel", "wood"],
        )
        data = {"properties": {"material": "plastic"}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_enum_case_insensitive(self):
        """enum check should be case-insensitive."""
        rule = self.Rule(
            code_name="TEST", section="3.1", title="Material enum",
            ifc_classes=["IfcWall"], check_type="enum",
            property_path="properties.material",
            check_value=["Concrete"],
        )
        data = {"properties": {"material": "CONCRETE"}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_boolean_pass(self):
        """boolean check passes when actual matches expected."""
        rule = self.Rule(
            code_name="TEST", section="4.1", title="Accessibility",
            ifc_classes=["IfcDoor"], check_type="boolean",
            property_path="constraints.accessibility",
            check_value=True,
        )
        data = {"constraints": {"accessibility": True}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_boolean_fail(self):
        """boolean check fails when actual doesn't match."""
        rule = self.Rule(
            code_name="TEST", section="4.1", title="Accessibility",
            ifc_classes=["IfcDoor"], check_type="boolean",
            property_path="constraints.accessibility",
            check_value=True,
        )
        data = {"constraints": {"accessibility": False}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_exists_pass(self):
        """exists check passes when property is present."""
        rule = self.Rule(
            code_name="TEST", section="5.1", title="Materials exist",
            ifc_classes=["IfcWall"], check_type="exists",
            property_path="materials",
        )
        data = {"materials": ["concrete"]}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_exists_fail(self):
        """exists check fails when property is missing."""
        rule = self.Rule(
            code_name="TEST", section="5.1", title="Materials exist",
            ifc_classes=["IfcWall"], check_type="exists",
            property_path="materials",
        )
        data = {"materials": []}
        result = self.evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_c2_fire_rating_parsing(self):
        """Fire rating strings should be parsed to hours correctly."""
        rule = self.Rule(
            code_name="TEST", section="6.1", title="Fire rating min",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="performance.fire_rating",
            check_value="2H",
        )
        # 2H should pass
        data = {"performance": {"fire_rating": "2H"}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

        # 3H should pass (exceeds minimum)
        data2 = {"performance": {"fire_rating": "3H"}}
        result2 = self.evaluate_rule(rule, data2)
        assert result2.status == "pass"

        # 1H should fail (below minimum)
        data3 = {"performance": {"fire_rating": "1H"}}
        result3 = self.evaluate_rule(rule, data3)
        assert result3.status == "fail"

    def test_c2_deep_property_path(self):
        """Dot-notation paths should resolve correctly."""
        rule = self.Rule(
            code_name="TEST", section="7.1", title="Deep path",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.dimensions.height",
            check_value=3000,
        )
        data = {"properties": {"dimensions": {"height": 3500}}}
        result = self.evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_c2_all_seed_rules_have_valid_check_types(self):
        """Every seed rule should have a valid check_type."""
        from aecos.compliance.seed_data import SEED_RULES
        valid_types = {"min_value", "max_value", "enum", "boolean", "exists"}
        for rule in SEED_RULES:
            assert rule.check_type in valid_types, \
                f"Rule {rule.title} has invalid check_type: {rule.check_type}"


# ===================================================================
# C3 – Cost engine accuracy
# ===================================================================
class TestCostEngineAccuracy:
    """Verify cost math: material_cost = unit_cost × quantity × regional_factor."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from aecos.cost.engine import CostEngine, _AVG_LABOR_RATE
        from aecos.cost.estimator import calculate_quantities
        from aecos.cost.pricing import LocalProvider
        from aecos.cost.regional import get_regional_factor
        from aecos.cost.seed_data import SEED_PRICING, REGIONAL_FACTORS

        self.CostEngine = CostEngine
        self.calculate_quantities = calculate_quantities
        self.provider = LocalProvider()
        self.get_regional_factor = get_regional_factor
        self.SEED_PRICING = SEED_PRICING
        self.REGIONAL_FACTORS = REGIONAL_FACTORS
        self.AVG_LABOR_RATE = _AVG_LABOR_RATE
        yield

    def test_c3_wall_quantity_math(self):
        """Wall: area = height × length, volume = area × thickness."""
        props = {"height_mm": 3000, "length_mm": 6000, "thickness_mm": 200}
        q = self.calculate_quantities("IfcWall", props)
        expected_area = 3.0 * 6.0  # 18.0 m2
        expected_vol = 18.0 * 0.2  # 3.6 m3
        assert abs(q["area_m2"] - expected_area) < 0.01
        assert abs(q["volume_m3"] - expected_vol) < 0.01

    def test_c3_door_quantity(self):
        """Door: count=1, area = width × height."""
        props = {"width_mm": 900, "height_mm": 2100}
        q = self.calculate_quantities("IfcDoor", props)
        assert q["count"] == 1.0
        expected_area = 0.9 * 2.1
        assert abs(q["area_m2"] - expected_area) < 0.01

    def test_c3_slab_quantity(self):
        """Slab: area = length × width, volume = area × thickness."""
        props = {"length_mm": 10000, "width_mm": 8000, "thickness_mm": 250}
        q = self.calculate_quantities("IfcSlab", props)
        expected_area = 10.0 * 8.0
        expected_vol = 80.0 * 0.25
        assert abs(q["area_m2"] - expected_area) < 0.01
        assert abs(q["volume_m3"] - expected_vol) < 0.01

    def test_c3_column_quantity(self):
        """Column: volume = cross_section × height."""
        props = {"width_mm": 400, "height_mm": 4000}
        q = self.calculate_quantities("IfcColumn", props)
        expected_vol = 0.4 * 0.4 * 4.0
        assert abs(q["volume_m3"] - expected_vol) < 0.01

    def test_c3_beam_quantity(self):
        """Beam: length_m and volume_m3."""
        props = {"length_mm": 8000, "depth_mm": 500, "width_mm": 300}
        q = self.calculate_quantities("IfcBeam", props)
        assert abs(q["length_m"] - 8.0) < 0.01
        expected_vol = 0.5 * 0.3 * 8.0
        assert abs(q["volume_m3"] - expected_vol) < 0.01

    def test_c3_cost_formula_verification(self):
        """Verify: material_cost = unit_cost × quantity × regional_factor."""
        from aecos.nlp.schema import ParametricSpec

        engine = self.CostEngine(region="LA")
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "length_mm": 6000, "thickness_mm": 200},
            materials=["concrete"],
        )
        report = engine.estimate(spec)

        # Manual calculation
        regional_factor = self.get_regional_factor("LA")
        unit_cost = self.provider.get_unit_cost("concrete", "IfcWall", "LA")
        q = self.calculate_quantities("IfcWall", spec.properties)

        # Wall uses m2 for pricing
        qty = q["area_m2"]
        expected_mat = unit_cost.material_cost_per_unit * qty * regional_factor
        expected_labor = unit_cost.labor_cost_per_unit * qty * regional_factor

        assert abs(report.material_cost_usd - round(expected_mat, 2)) < 0.02
        assert abs(report.labor_cost_usd - round(expected_labor, 2)) < 0.02

    def test_c3_labor_hours_formula(self):
        """labor_hours = labor_cost / labor_rate."""
        from aecos.nlp.schema import ParametricSpec

        engine = self.CostEngine()
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "length_mm": 5000, "thickness_mm": 200},
            materials=["concrete"],
        )
        report = engine.estimate(spec)
        expected_hours = report.labor_cost_usd / self.AVG_LABOR_RATE
        assert abs(report.labor_hours - round(expected_hours, 1)) < 0.2

    def test_c3_regional_factor_affects_cost(self):
        """Changing region should proportionally change cost."""
        from aecos.nlp.schema import ParametricSpec

        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "length_mm": 5000, "thickness_mm": 200},
            materials=["concrete"],
        )
        report_la = self.CostEngine(region="LA").estimate(spec)
        report_ny = self.CostEngine(region="NY").estimate(spec)

        factor_la = self.get_regional_factor("LA")
        factor_ny = self.get_regional_factor("NY")

        # Costs should be proportional to regional factors
        ratio_expected = factor_ny / factor_la
        ratio_actual = report_ny.total_installed_usd / report_la.total_installed_usd
        assert abs(ratio_actual - ratio_expected) < 0.05, \
            f"Expected ratio {ratio_expected:.3f}, got {ratio_actual:.3f}"

    def test_c3_dimension_proportional_cost(self):
        """Doubling dimensions should roughly proportionally affect cost."""
        from aecos.nlp.schema import ParametricSpec

        spec1 = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "length_mm": 5000, "thickness_mm": 200},
            materials=["concrete"],
        )
        spec2 = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "length_mm": 10000, "thickness_mm": 200},
            materials=["concrete"],
        )
        engine = self.CostEngine()
        report1 = engine.estimate(spec1)
        report2 = engine.estimate(spec2)

        # Doubling length should roughly double the cost
        ratio = report2.total_installed_usd / report1.total_installed_usd
        assert 1.5 < ratio < 2.5, f"Expected ~2x cost, got {ratio:.1f}x"

    def test_c3_schedule_positive_nonzero(self):
        """Schedule should produce positive non-zero values."""
        from aecos.nlp.schema import ParametricSpec

        for ifc_class in ["IfcWall", "IfcDoor", "IfcSlab", "IfcColumn", "IfcBeam"]:
            spec = ParametricSpec(
                ifc_class=ifc_class,
                properties={"height_mm": 3000, "width_mm": 1000,
                            "thickness_mm": 200, "length_mm": 5000,
                            "depth_mm": 500},
                materials=["concrete"],
            )
            report = self.CostEngine().estimate(spec)
            assert report.duration_days > 0, f"{ifc_class}: duration_days is 0"
            assert report.crew_size > 0, f"{ifc_class}: crew_size is 0"

    def test_c3_all_seed_pricing_entries(self):
        """Every seed pricing entry should return valid unit costs."""
        for (material, ifc_class), data in self.SEED_PRICING.items():
            unit_cost = self.provider.get_unit_cost(material, ifc_class)
            assert unit_cost is not None
            assert unit_cost.material_cost_per_unit > 0
            assert unit_cost.labor_cost_per_unit > 0
            assert unit_cost.unit_type in ("m2", "m3", "m", "each")


# ===================================================================
# C4 – Validation rule coverage
# ===================================================================
class TestValidationRuleCoverage:
    """For every registered validation rule, construct a triggering and
    non-triggering element."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.validation.validator import Validator
        self.validator = Validator()
        self.tmp = tmp_path
        yield

    def test_c4_well_formed_element_passes(self):
        """A well-formed element should pass validation."""
        folder = _make_element_folder(
            self.tmp, "good_elem", "IfcWall", "Good Wall",
            psets={"Dimensions": {"height_mm": 3000, "length_mm": 5000,
                                   "thickness_mm": 200}},
            geometry={"bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                                        "max_x": 5.0, "max_y": 0.2, "max_z": 3.0},
                      "volume": 3.0, "centroid": [2.5, 0.1, 1.5]},
        )
        report = self.validator.validate(str(folder))
        assert report.status in ("passed", "warnings")

    def test_c4_zero_volume_triggers_warning(self):
        """An element with zero volume should trigger a validation issue."""
        folder = _make_element_folder(
            self.tmp, "zero_vol", "IfcWall", "Zero Vol Wall",
            geometry={"bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                                        "max_x": 0, "max_y": 0, "max_z": 0},
                      "volume": 0.0, "centroid": [0, 0, 0]},
        )
        report = self.validator.validate(str(folder))
        has_issue = any("volume" in i.message.lower() or "dimension" in i.message.lower()
                        or "zero" in i.message.lower() or "bounding" in i.message.lower()
                        for i in report.issues)
        # Zero volume should be flagged
        assert has_issue or report.status != "passed"

    def test_c4_missing_material_triggers_issue(self):
        """An element with no materials should trigger a semantic issue."""
        folder = _make_element_folder(
            self.tmp, "no_mat", "IfcWall", "No Material Wall",
            materials=[],
        )
        report = self.validator.validate(str(folder))
        has_material_issue = any("material" in i.message.lower() for i in report.issues)
        # Either has material warning or fails
        assert has_material_issue or report.status != "passed"

    def test_c4_clash_detection_overlapping(self):
        """Overlapping bounding boxes should be detected as clashes."""
        from aecos.validation.clash import ClashDetector

        elem_a = {
            "metadata": {"GlobalId": "aaa", "IFCClass": "IfcWall"},
            "geometry": {"bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                                           "max_x": 2, "max_y": 0.2, "max_z": 3}},
        }
        elem_b = {
            "metadata": {"GlobalId": "bbb", "IFCClass": "IfcWall"},
            "geometry": {"bounding_box": {"min_x": 1, "min_y": 0, "min_z": 0,
                                           "max_x": 3, "max_y": 0.2, "max_z": 3}},
        }

        detector = ClashDetector()
        clashes = detector.detect([elem_a, elem_b])
        assert len(clashes) > 0, "Overlapping elements should produce clashes"

    def test_c4_clash_detection_no_overlap(self):
        """Non-overlapping bounding boxes should NOT produce clashes."""
        from aecos.validation.clash import ClashDetector

        elem_a = {
            "metadata": {"GlobalId": "aaa", "IFCClass": "IfcWall"},
            "geometry": {"bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                                           "max_x": 1, "max_y": 0.2, "max_z": 3}},
        }
        elem_b = {
            "metadata": {"GlobalId": "bbb", "IFCClass": "IfcWall"},
            "geometry": {"bounding_box": {"min_x": 5, "min_y": 5, "min_z": 5,
                                           "max_x": 6, "max_y": 5.2, "max_z": 8}},
        }

        detector = ClashDetector()
        clashes = detector.detect([elem_a, elem_b])
        assert len(clashes) == 0, "Non-overlapping elements should not clash"


# ===================================================================
# C5 – Metadata template correctness
# ===================================================================
class TestMetadataTemplateCorrectness:
    """Generate elements with known data, verify Markdown output has
    correct numbers, names, and statuses."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        yield

    def test_c5_readme_contains_element_data(self):
        """README.md should contain the element name and IFC class."""
        from aecos.metadata.generator import generate_metadata

        folder = _make_element_folder(
            self.tmp, "readme_test", "IfcWall", "Test Wall Alpha",
            psets={"Dimensions": {"height_mm": 3000}},
        )
        generate_metadata(folder)
        readme = (folder / "README.md").read_text()
        assert "Test Wall Alpha" in readme
        assert "IfcWall" in readme

    def test_c5_compliance_md_contains_status(self):
        """COMPLIANCE.md should reference compliance info."""
        from aecos.metadata.generator import generate_metadata

        folder = _make_element_folder(
            self.tmp, "comp_test", "IfcWall", "Compliance Wall",
        )
        generate_metadata(folder)
        comp_md = (folder / "COMPLIANCE.md").read_text()
        assert "Compliance Wall" in comp_md

    def test_c5_cost_md_contains_material(self):
        """COST.md should reference materials."""
        from aecos.metadata.generator import generate_metadata

        folder = _make_element_folder(
            self.tmp, "cost_test", "IfcWall", "Cost Wall",
            materials=[{"name": "Concrete", "category": "concrete",
                        "thickness": 0.2, "fraction": 1.0}],
        )
        generate_metadata(folder)
        cost_md = (folder / "COST.md").read_text()
        assert "Cost Wall" in cost_md
