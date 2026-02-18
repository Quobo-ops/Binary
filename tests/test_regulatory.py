"""Tests for Item 15 — Regulatory Auto-Update.

Covers: UpdateMonitor, RuleDiffer, RuleUpdater, ImpactAnalyzer,
UpdateScheduler, UpdateReport, and the full pipeline.

All tests run offline with zero network access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.rules import Rule
from aecos.regulatory.differ import RuleDiffer, RuleDiffResult
from aecos.regulatory.impact import ImpactAnalyzer, ImpactReport
from aecos.regulatory.monitor import UpdateCheckResult, UpdateMonitor
from aecos.regulatory.report import UpdateReport
from aecos.regulatory.scheduler import UpdateScheduler
from aecos.regulatory.sources import CodeSource, DEFAULT_SOURCES
from aecos.regulatory.updater import RuleUpdater, UpdateResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_rule(
    code_name: str = "IBC2024",
    section: str = "1.1",
    title: str = "Test rule",
    ifc_classes: list[str] | None = None,
    check_type: str = "min_value",
    property_path: str = "properties.thickness_mm",
    check_value: int = 152,
    region: str = "US",
    citation: str = "Test citation",
    rule_id: int | None = None,
) -> Rule:
    return Rule(
        id=rule_id,
        code_name=code_name,
        section=section,
        title=title,
        ifc_classes=ifc_classes or ["IfcWall"],
        check_type=check_type,
        property_path=property_path,
        check_value=check_value,
        region=region,
        citation=citation,
    )


@pytest.fixture
def engine() -> ComplianceEngine:
    return ComplianceEngine(":memory:")


@pytest.fixture
def differ() -> RuleDiffer:
    return RuleDiffer()


# ---------------------------------------------------------------------------
# CodeSource and DEFAULT_SOURCES
# ---------------------------------------------------------------------------


class TestCodeSources:
    def test_default_sources_count(self) -> None:
        assert len(DEFAULT_SOURCES) >= 6

    def test_default_sources_have_names(self) -> None:
        for src in DEFAULT_SOURCES:
            assert src.code_name != ""
            assert src.current_version != ""

    def test_default_sources_manual_method(self) -> None:
        for src in DEFAULT_SOURCES:
            assert src.check_method == "manual"

    def test_code_source_model(self) -> None:
        src = CodeSource(
            code_name="TEST",
            current_version="1.0",
            check_method="manual",
            description="Test source",
        )
        assert src.code_name == "TEST"
        assert src.current_version == "1.0"


# ---------------------------------------------------------------------------
# UpdateMonitor
# ---------------------------------------------------------------------------


class TestUpdateMonitor:
    def test_init_with_default_sources(self) -> None:
        monitor = UpdateMonitor()
        assert len(monitor.sources) >= 6

    def test_add_source(self) -> None:
        monitor = UpdateMonitor(sources=[])
        src = CodeSource(code_name="CUSTOM", current_version="1.0")
        monitor.add_source(src)
        assert monitor.get_source("CUSTOM") is not None

    def test_get_source(self) -> None:
        monitor = UpdateMonitor()
        src = monitor.get_source("IBC2024")
        assert src is not None
        assert src.code_name == "IBC2024"

    def test_get_source_nonexistent(self) -> None:
        monitor = UpdateMonitor()
        assert monitor.get_source("NONEXIST") is None

    def test_check_source_manual_returns_no_update(self) -> None:
        monitor = UpdateMonitor()
        src = monitor.get_source("IBC2024")
        result = monitor.check_source(src)
        assert isinstance(result, UpdateCheckResult)
        assert result.new_version_available is False
        assert result.source_method == "manual"

    def test_check_all_returns_results(self) -> None:
        monitor = UpdateMonitor()
        results = monitor.check_all()
        assert len(results) >= 6
        for r in results:
            assert isinstance(r, UpdateCheckResult)
            assert r.code_name != ""

    def test_check_all_offline(self) -> None:
        """All checks should work without network access."""
        monitor = UpdateMonitor()
        results = monitor.check_all()
        for r in results:
            assert r.new_version_available is False


# ---------------------------------------------------------------------------
# RuleDiffer
# ---------------------------------------------------------------------------


class TestRuleDiffer:
    def test_empty_diff(self, differ: RuleDiffer) -> None:
        result = differ.diff_rules([], [])
        assert not result.has_changes
        assert result.total_changes == 0

    def test_added_rules(self, differ: RuleDiffer) -> None:
        old: list[Rule] = []
        new = [_make_rule(section="1.1"), _make_rule(section="1.2")]
        result = differ.diff_rules(old, new)
        assert len(result.added) == 2
        assert len(result.removed) == 0
        assert result.has_changes

    def test_removed_rules(self, differ: RuleDiffer) -> None:
        old = [_make_rule(section="1.1"), _make_rule(section="1.2")]
        new: list[Rule] = []
        result = differ.diff_rules(old, new)
        assert len(result.removed) == 2
        assert len(result.added) == 0

    def test_modified_rules(self, differ: RuleDiffer) -> None:
        old = [_make_rule(section="1.1", title="Original")]
        new = [_make_rule(section="1.1", title="Updated")]
        result = differ.diff_rules(old, new)
        assert len(result.modified) == 1
        old_rule, new_rule = result.modified[0]
        assert old_rule.title == "Original"
        assert new_rule.title == "Updated"

    def test_unchanged_rules(self, differ: RuleDiffer) -> None:
        rule = _make_rule(section="1.1")
        result = differ.diff_rules([rule], [rule])
        assert len(result.unchanged) == 1
        assert not result.has_changes

    def test_mixed_changes(self, differ: RuleDiffer) -> None:
        old = [
            _make_rule(section="1.1", title="Keep"),
            _make_rule(section="1.2", title="Modify"),
            _make_rule(section="1.3", title="Remove"),
        ]
        new = [
            _make_rule(section="1.1", title="Keep"),
            _make_rule(section="1.2", title="Modified"),
            _make_rule(section="1.4", title="Add"),
        ]
        result = differ.diff_rules(old, new)
        assert len(result.unchanged) == 1
        assert len(result.modified) == 1
        assert len(result.removed) == 1
        assert len(result.added) == 1

    def test_summary_format(self, differ: RuleDiffer) -> None:
        old = [_make_rule(section="1.1")]
        new = [_make_rule(section="1.2")]
        result = differ.diff_rules(old, new)
        summary = result.summary()
        assert "Added:" in summary
        assert "Removed:" in summary
        assert "Modified:" in summary

    def test_key_by_code_name_section(self, differ: RuleDiffer) -> None:
        """Rules with same code_name+section are the same rule."""
        old = [_make_rule(code_name="A", section="1")]
        new = [_make_rule(code_name="A", section="1", title="Changed")]
        result = differ.diff_rules(old, new)
        assert len(result.modified) == 1
        assert len(result.added) == 0


# ---------------------------------------------------------------------------
# RuleUpdater
# ---------------------------------------------------------------------------


class TestRuleUpdater:
    def test_apply_empty_diff(self, engine: ComplianceEngine) -> None:
        updater = RuleUpdater(engine)
        diff = RuleDiffResult()
        result = updater.apply_update(diff)
        assert result.success is True
        assert result.rules_added == 0

    def test_apply_additions(self, engine: ComplianceEngine) -> None:
        updater = RuleUpdater(engine)
        diff = RuleDiffResult(added=[_make_rule(section="99.1"), _make_rule(section="99.2")])
        result = updater.apply_update(diff, code_name="TEST")
        assert result.success is True
        assert result.rules_added == 2

    def test_apply_modifications(self, engine: ComplianceEngine) -> None:
        # Add a rule first to get an ID
        rule_id = engine.add_rule(_make_rule(section="1.1", title="Original"))
        old_rule = engine.db.get_rule(rule_id)
        new_rule = _make_rule(section="1.1", title="Updated")

        updater = RuleUpdater(engine)
        diff = RuleDiffResult(modified=[(old_rule, new_rule)])
        result = updater.apply_update(diff)
        assert result.success is True
        assert result.rules_modified == 1

        # Verify update took effect
        updated = engine.db.get_rule(rule_id)
        assert updated.title == "Updated"

    def test_apply_removals(self, engine: ComplianceEngine) -> None:
        rule_id = engine.add_rule(_make_rule(section="1.1"))
        rule = engine.db.get_rule(rule_id)

        updater = RuleUpdater(engine)
        diff = RuleDiffResult(removed=[rule])
        result = updater.apply_update(diff)
        assert result.success is True
        assert result.rules_removed == 1

    def test_backup_created(self, engine: ComplianceEngine, tmp_path: Path) -> None:
        updater = RuleUpdater(engine, project_root=tmp_path)
        diff = RuleDiffResult(added=[_make_rule(section="99.1")])
        result = updater.apply_update(diff, code_name="TEST")
        assert result.backup_path != ""
        assert Path(result.backup_path).is_file()

    def test_backup_contains_rules(self, engine: ComplianceEngine, tmp_path: Path) -> None:
        updater = RuleUpdater(engine, project_root=tmp_path)
        diff = RuleDiffResult(added=[_make_rule(section="99.1")])
        result = updater.apply_update(diff, code_name="TEST")
        backup_data = json.loads(Path(result.backup_path).read_text())
        assert isinstance(backup_data, list)


# ---------------------------------------------------------------------------
# ImpactAnalyzer
# ---------------------------------------------------------------------------


class TestImpactAnalyzer:
    def test_no_changes_no_impact(self) -> None:
        analyzer = ImpactAnalyzer()
        diff = RuleDiffResult()
        report = analyzer.analyze(diff)
        assert isinstance(report, ImpactReport)
        assert report.total_affected == 0

    def test_affected_ifc_classes_collected(self) -> None:
        analyzer = ImpactAnalyzer()
        diff = RuleDiffResult(
            added=[_make_rule(ifc_classes=["IfcBeam"])],
            removed=[_make_rule(ifc_classes=["IfcColumn"])],
        )
        report = analyzer.analyze(diff)
        assert "IfcBeam" in report.affected_ifc_classes
        assert "IfcColumn" in report.affected_ifc_classes

    def test_scan_elements(self, tmp_path: Path) -> None:
        """Elements matching affected IFC classes should be detected."""
        analyzer = ImpactAnalyzer(project_root=tmp_path)

        # Create a mock element folder with metadata
        elem_dir = tmp_path / "elements" / "element_TEST001"
        elem_dir.mkdir(parents=True)
        meta = {"IFCClass": "IfcWall", "GlobalId": "TEST001"}
        (elem_dir / "metadata.json").write_text(json.dumps(meta))

        diff = RuleDiffResult(added=[_make_rule(ifc_classes=["IfcWall"])])
        report = analyzer.analyze(diff)
        assert "element_TEST001" in report.affected_elements

    def test_scan_templates(self, tmp_path: Path) -> None:
        """Templates matching affected IFC classes should be detected."""
        analyzer = ImpactAnalyzer(project_root=tmp_path)
        lib_path = tmp_path / "templates"

        # Create a mock template folder
        tmpl_dir = lib_path / "template_wall_basic"
        tmpl_dir.mkdir(parents=True)
        meta = {"IFCClass": "IfcWall"}
        (tmpl_dir / "metadata.json").write_text(json.dumps(meta))

        diff = RuleDiffResult(added=[_make_rule(ifc_classes=["IfcWall"])])
        report = analyzer.analyze(diff, library_path=lib_path)
        assert "template_wall_basic" in report.affected_templates

    def test_summary_format(self) -> None:
        report = ImpactReport(
            affected_templates=["t1"],
            affected_elements=["e1", "e2"],
        )
        summary = report.summary()
        assert "1 templates" in summary
        assert "2 elements" in summary


# ---------------------------------------------------------------------------
# UpdateScheduler
# ---------------------------------------------------------------------------


class TestUpdateScheduler:
    def test_initial_state(self) -> None:
        scheduler = UpdateScheduler()
        assert scheduler.is_running is False

    def test_schedule_and_stop(self) -> None:
        scheduler = UpdateScheduler()
        scheduler.schedule_check(interval_hours=1)
        assert scheduler.is_running is True
        scheduler.stop()
        assert scheduler.is_running is False

    def test_check_now(self) -> None:
        results = []
        scheduler = UpdateScheduler(check_callback=lambda: results.append("checked"))
        scheduler.check_now()
        assert "checked" in results

    def test_state_persistence(self, tmp_path: Path) -> None:
        scheduler = UpdateScheduler(project_root=tmp_path)
        scheduler.schedule_check(interval_hours=24)
        scheduler.stop()

        state_path = tmp_path / ".aecos" / "regulatory_schedule.json"
        assert state_path.is_file()
        state = json.loads(state_path.read_text())
        assert state["interval_hours"] == 24


# ---------------------------------------------------------------------------
# UpdateReport
# ---------------------------------------------------------------------------


class TestUpdateReport:
    def test_to_markdown(self) -> None:
        report = UpdateReport(
            code_name="IBC2024",
            old_version="2024.0",
            new_version="2024.1",
            changes_summary="Added 2 rules, Modified 1",
            rules_added=2,
            rules_modified=1,
            rules_removed=0,
            affected_templates_count=3,
            affected_elements_count=5,
        )
        md = report.to_markdown()
        assert "# Regulatory Update Report" in md
        assert "IBC2024" in md
        assert "2024.0" in md
        assert "2024.1" in md
        assert "Added" in md
        assert "Modified" in md

    def test_markdown_impact_section(self) -> None:
        report = UpdateReport(
            code_name="TEST",
            affected_templates_count=1,
            affected_elements_count=2,
        )
        md = report.to_markdown()
        assert "Impact Assessment" in md
        assert "Action Required" in md

    def test_empty_report(self) -> None:
        report = UpdateReport()
        md = report.to_markdown()
        assert "# Regulatory Update Report" in md

    def test_git_tag_in_markdown(self) -> None:
        report = UpdateReport(
            code_name="IBC2024",
            git_tag="regulatory/IBC2024/2024.1/20260218",
        )
        md = report.to_markdown()
        assert "regulatory/IBC2024/2024.1/20260218" in md


# ---------------------------------------------------------------------------
# Full pipeline: monitor → diff → update → impact → report
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_manual_update_pipeline(self, tmp_path: Path) -> None:
        """End-to-end: create rules, diff, apply, analyze impact."""
        engine = ComplianceEngine(":memory:")

        # Add initial rules
        engine.add_rule(_make_rule(section="1.1", title="Original rule"))

        # Prepare new rules (modify + add)
        new_rules = [
            _make_rule(section="1.1", title="Updated rule"),
            _make_rule(section="2.1", title="Brand new rule"),
        ]

        # Diff
        old_rules = engine.get_rules(code_name="IBC2024")
        differ = RuleDiffer()
        diff = differ.diff_rules(old_rules, new_rules)

        assert diff.has_changes
        assert len(diff.added) == 1
        assert len(diff.modified) == 1

        # Apply
        updater = RuleUpdater(engine, project_root=tmp_path)
        result = updater.apply_update(diff, code_name="IBC2024", version="2024.1")
        assert result.success is True
        assert result.rules_added == 1
        assert result.rules_modified == 1

        # Impact
        analyzer = ImpactAnalyzer(project_root=tmp_path)
        impact = analyzer.analyze(diff)
        assert isinstance(impact, ImpactReport)

        # Report
        report = UpdateReport(
            code_name="IBC2024",
            old_version="2024.0",
            new_version="2024.1",
            changes_summary=diff.summary(),
            rules_added=result.rules_added,
            rules_modified=result.rules_modified,
            rules_removed=result.rules_removed,
        )
        md = report.to_markdown()
        assert "IBC2024" in md

    def test_no_changes_pipeline(self) -> None:
        """When rules are identical, no changes should be applied."""
        engine = ComplianceEngine(":memory:")
        rule = _make_rule(section="1.1")
        engine.add_rule(rule)

        old_rules = engine.get_rules(code_name="IBC2024")
        differ = RuleDiffer()
        diff = differ.diff_rules(old_rules, old_rules)

        assert not diff.has_changes
        updater = RuleUpdater(engine)
        result = updater.apply_update(diff)
        assert result.success is True
        assert result.rules_added == 0
