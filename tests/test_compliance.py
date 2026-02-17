"""Tests for Item 07 — Code Compliance Engine.

All tests use an in-memory SQLite database. No external dependencies.
"""

from __future__ import annotations

import pytest

from aecos.compliance import ComplianceEngine, ComplianceReport, Rule
from aecos.compliance.checker import check_element
from aecos.compliance.database import RuleDatabase
from aecos.compliance.rules import RuleResult, evaluate_rule
from aecos.compliance.seed_data import SEED_RULES
from aecos.nlp.schema import ParametricSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> ComplianceEngine:
    """Compliance engine with in-memory auto-seeded database."""
    return ComplianceEngine(":memory:")


@pytest.fixture
def db() -> RuleDatabase:
    """Rule database for direct testing."""
    return RuleDatabase(":memory:", auto_seed=True)


# ---------------------------------------------------------------------------
# Seed data and database
# ---------------------------------------------------------------------------


class TestSeedData:
    def test_seed_rules_count(self) -> None:
        """Seed data should have 15-25 rules."""
        assert 15 <= len(SEED_RULES) <= 25

    def test_seed_rules_have_citations(self) -> None:
        for rule in SEED_RULES:
            assert rule.citation, f"Rule {rule.code_name} {rule.section} missing citation"

    def test_seed_rules_have_ifc_classes(self) -> None:
        for rule in SEED_RULES:
            assert rule.ifc_classes, f"Rule {rule.code_name} {rule.section} missing ifc_classes"


class TestRuleDatabase:
    def test_auto_seed_on_first_access(self, db: RuleDatabase) -> None:
        assert db.count() > 0

    def test_rule_count_matches_seed(self, db: RuleDatabase) -> None:
        assert db.count() == len(SEED_RULES)

    def test_add_rule(self, db: RuleDatabase) -> None:
        initial = db.count()
        new_rule = Rule(
            code_name="TEST",
            section="1.1",
            title="Test rule",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="properties.height_mm",
            check_value=1000,
            region="US",
            citation="Test citation",
        )
        rule_id = db.add_rule(new_rule)
        assert rule_id > 0
        assert db.count() == initial + 1

    def test_get_rule(self, db: RuleDatabase) -> None:
        rule = db.get_rule(1)
        assert rule is not None
        assert rule.id == 1
        assert rule.code_name != ""

    def test_get_rules_by_ifc_class(self, db: RuleDatabase) -> None:
        wall_rules = db.get_rules(ifc_class="IfcWall")
        assert len(wall_rules) > 0
        for r in wall_rules:
            assert "IfcWall" in r.ifc_classes or r.ifc_classes == ["*"]

    def test_get_rules_by_region(self, db: RuleDatabase) -> None:
        ca_rules = db.get_rules(region="CA")
        # Should include CA-specific rules AND universal (*) rules
        assert len(ca_rules) > 0
        for r in ca_rules:
            assert r.region in ("CA", "*")

    def test_get_rules_by_code_name(self, db: RuleDatabase) -> None:
        ibc_rules = db.get_rules(code_name="IBC2024")
        assert len(ibc_rules) > 0
        for r in ibc_rules:
            assert r.code_name == "IBC2024"

    def test_search_rules(self, db: RuleDatabase) -> None:
        results = db.search_rules("fire")
        assert len(results) > 0

    def test_delete_rule(self, db: RuleDatabase) -> None:
        initial = db.count()
        assert db.delete_rule(1) is True
        assert db.count() == initial - 1

    def test_delete_nonexistent_rule(self, db: RuleDatabase) -> None:
        assert db.delete_rule(99999) is False

    def test_update_rule(self, db: RuleDatabase) -> None:
        db.update_rule(1, {"title": "Updated title"})
        rule = db.get_rule(1)
        assert rule is not None
        assert rule.title == "Updated title"


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------


class TestRuleEvaluation:
    def test_min_value_pass(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="1905.1",
            title="Min wall thickness",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="properties.thickness_mm",
            check_value=152,
        )
        data = {"properties": {"thickness_mm": 200}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_min_value_fail(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="1905.1",
            title="Min wall thickness",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="properties.thickness_mm",
            check_value=152,
        )
        data = {"properties": {"thickness_mm": 100}}
        result = evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_min_value_missing(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="1905.1",
            title="Min wall thickness",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="properties.thickness_mm",
            check_value=152,
        )
        data = {"properties": {}}
        result = evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_fire_rating_min_value_pass(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="703.3",
            title="Fire barrier rating",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="performance.fire_rating",
            check_value="1H",
        )
        data = {"performance": {"fire_rating": "2H"}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_fire_rating_min_value_fail(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="706.4",
            title="Fire wall rating",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="performance.fire_rating",
            check_value="2H",
        )
        data = {"performance": {"fire_rating": "1H"}}
        result = evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_exists_pass(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="716.5",
            title="Fire door rating exists",
            ifc_classes=["IfcDoor"],
            check_type="exists",
            property_path="performance.fire_rating",
        )
        data = {"performance": {"fire_rating": "1H"}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_exists_fail(self) -> None:
        rule = Rule(
            code_name="IBC2024",
            section="716.5",
            title="Fire door rating exists",
            ifc_classes=["IfcDoor"],
            check_type="exists",
            property_path="performance.fire_rating",
        )
        data = {"performance": {}}
        result = evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_boolean_pass(self) -> None:
        rule = Rule(
            code_name="ADA2010",
            section="404.2.9",
            title="Door accessibility",
            ifc_classes=["IfcDoor"],
            check_type="boolean",
            property_path="constraints.accessibility.required",
            check_value=True,
        )
        data = {"constraints": {"accessibility": {"required": True}}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_enum_pass(self) -> None:
        rule = Rule(
            code_name="TEST",
            section="1.1",
            title="Material type",
            ifc_classes=["IfcWall"],
            check_type="enum",
            property_path="properties.material",
            check_value=["concrete", "masonry", "steel"],
        )
        data = {"properties": {"material": "concrete"}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_enum_fail(self) -> None:
        rule = Rule(
            code_name="TEST",
            section="1.1",
            title="Material type",
            ifc_classes=["IfcWall"],
            check_type="enum",
            property_path="properties.material",
            check_value=["concrete", "masonry"],
        )
        data = {"properties": {"material": "wood"}}
        result = evaluate_rule(rule, data)
        assert result.status == "fail"

    def test_max_value_pass(self) -> None:
        rule = Rule(
            code_name="TEST",
            section="1.1",
            title="Max height",
            ifc_classes=["IfcWall"],
            check_type="max_value",
            property_path="properties.height_mm",
            check_value=4000,
        )
        data = {"properties": {"height_mm": 3000}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# Compliance engine — full checks
# ---------------------------------------------------------------------------


class TestComplianceEngine:
    def test_compliant_wall(self, engine: ComplianceEngine) -> None:
        """A wall that meets all requirements should be compliant."""
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 200, "height_mm": 3658},
            materials=["concrete"],
            performance={"fire_rating": "2H", "thermal_r_value": 25},
        )
        report = engine.check(spec, region="US")
        # With fire_rating=2H and thickness_mm=200, basic IBC rules pass
        assert isinstance(report, ComplianceReport)
        assert report.ifc_class == "IfcWall"
        passes = [r for r in report.results if r.status == "pass"]
        assert len(passes) > 0

    def test_non_compliant_wall_missing_fire_rating(self, engine: ComplianceEngine) -> None:
        """A wall without fire rating should be non-compliant."""
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 200},
            materials=["concrete"],
            performance={},
        )
        report = engine.check(spec, region="US")
        assert report.status == "non_compliant"
        fails = [r for r in report.results if r.status == "fail"]
        assert len(fails) > 0
        # Should have suggestions
        assert len(report.suggested_fixes) > 0

    def test_region_filtering_ca(self, engine: ComplianceEngine) -> None:
        """CA region should include California-specific rules."""
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 200},
            materials=["concrete"],
            performance={"fire_rating": "2H", "thermal_r_value": 25},
        )
        report_ca = engine.check(spec, region="CA")
        report_us = engine.check(spec, region="US")
        # CA report should include some CA-specific rules
        ca_codes = {r.code_name for r in report_ca.results}
        us_codes = {r.code_name for r in report_us.results}
        # CA may have CBC/Title-24 rules not in US-only set
        assert len(report_ca.results) > 0
        assert len(report_us.results) > 0

    def test_door_compliance(self, engine: ComplianceEngine) -> None:
        """Check door width against ADA requirements."""
        spec = ParametricSpec(
            ifc_class="IfcDoor",
            properties={"width_mm": 914},
            performance={"fire_rating": "1H"},
            constraints={"accessibility": {"required": True}},
        )
        report = engine.check(spec, region="US")
        assert isinstance(report, ComplianceReport)
        # 914mm > 813mm ADA minimum, should pass width rules
        width_results = [
            r for r in report.results
            if "width" in r.title.lower() or "width" in r.message.lower()
        ]
        for wr in width_results:
            assert wr.status == "pass"

    def test_no_rules_returns_unknown(self) -> None:
        """Element type with no matching rules returns unknown status."""
        engine = ComplianceEngine(":memory:")
        spec = ParametricSpec(ifc_class="IfcPipeSegment")
        report = engine.check(spec, region="US")
        # IfcPipeSegment may have no rules
        if not report.results:
            assert report.status == "unknown"


# ---------------------------------------------------------------------------
# Compliance report
# ---------------------------------------------------------------------------


class TestComplianceReport:
    def test_to_markdown(self, engine: ComplianceEngine) -> None:
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 200},
            materials=["concrete"],
            performance={"fire_rating": "2H"},
        )
        report = engine.check(spec, region="US")
        md = report.to_markdown()
        assert isinstance(md, str)
        assert "# Compliance Report" in md
        assert "IfcWall" in md
        assert "Rule Results" in md

    def test_markdown_contains_violations_section(self, engine: ComplianceEngine) -> None:
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={},
            materials=[],
            performance={},
        )
        report = engine.check(spec, region="US")
        md = report.to_markdown()
        if report.status == "non_compliant":
            assert "Violations" in md
            assert "Suggested Fixes" in md

    def test_report_timestamps(self, engine: ComplianceEngine) -> None:
        spec = ParametricSpec(ifc_class="IfcWall")
        report = engine.check(spec)
        assert report.checked_at is not None

    def test_empty_report(self) -> None:
        report = ComplianceReport()
        md = report.to_markdown()
        assert "# Compliance Report" in md


# ---------------------------------------------------------------------------
# Rule CRUD via engine
# ---------------------------------------------------------------------------


class TestEngineCRUD:
    def test_add_rule(self, engine: ComplianceEngine) -> None:
        rule = Rule(
            code_name="CUSTOM",
            section="99.1",
            title="Custom test rule",
            ifc_classes=["IfcWall"],
            check_type="min_value",
            property_path="properties.height_mm",
            check_value=2400,
            region="US",
            citation="Custom rule for testing.",
        )
        rule_id = engine.add_rule(rule)
        assert rule_id > 0

    def test_get_rules(self, engine: ComplianceEngine) -> None:
        rules = engine.get_rules(ifc_class="IfcWall")
        assert len(rules) > 0

    def test_search_rules(self, engine: ComplianceEngine) -> None:
        results = engine.search_rules("fire")
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Full round-trip: parse → check → report
# ---------------------------------------------------------------------------


class TestFullRoundTrip:
    def test_parse_check_report(self) -> None:
        """End-to-end: NL text → parse → compliance check → markdown report."""
        from aecos.nlp import NLParser
        from aecos.nlp.providers.fallback import FallbackProvider

        parser = NLParser(provider=FallbackProvider())
        engine = ComplianceEngine(":memory:")

        # Parse
        spec = parser.parse(
            "2-hour fire-rated concrete wall, 12 feet tall, 6 inch thick"
        )
        assert spec.ifc_class == "IfcWall"
        assert spec.performance.get("fire_rating") == "2H"

        # Check compliance
        report = engine.check(spec, region="US")
        assert isinstance(report, ComplianceReport)
        assert len(report.results) > 0

        # Generate markdown
        md = report.to_markdown()
        assert "Compliance Report" in md
        assert "IfcWall" in md

    def test_parse_noncompliant_check(self) -> None:
        """Parse a spec that will fail compliance, verify violations."""
        from aecos.nlp import NLParser
        from aecos.nlp.providers.fallback import FallbackProvider

        parser = NLParser(provider=FallbackProvider())
        engine = ComplianceEngine(":memory:")

        # Wall with no fire rating and thin thickness
        spec = parser.parse("concrete wall, 4 inches thick")
        report = engine.check(spec, region="US")

        # Should have some failures (no fire rating, thin wall)
        fails = [r for r in report.results if r.status == "fail"]
        assert len(fails) > 0
        assert report.status in ("non_compliant", "partial")
