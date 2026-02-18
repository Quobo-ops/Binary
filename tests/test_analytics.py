"""Tests for Item 19 — Analytics Dashboard."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from aecos.analytics.collector import MetricsCollector
from aecos.analytics.dashboard import DashboardGenerator
from aecos.analytics.exporter import ReportExporter
from aecos.analytics.kpi import KPICalculator
from aecos.analytics.warehouse import DataWarehouse


# ── MetricsCollector ─────────────────────────────────────────────────────────

class TestMetricsCollector:

    def test_record_and_retrieve(self):
        collector = MetricsCollector(":memory:")
        eid = collector.record("parser", "parse_completed", 0.95, user="alice")
        assert eid > 0

        events = collector.get_events(module="parser")
        assert len(events) == 1
        assert events[0]["module"] == "parser"
        assert events[0]["event_type"] == "parse_completed"
        assert events[0]["value"] == 0.95
        collector.close()

    def test_record_multiple_events(self):
        collector = MetricsCollector(":memory:")
        for i in range(20):
            collector.record("generation", "element_generated", float(i * 100))

        events = collector.get_events(module="generation")
        assert len(events) == 20
        collector.close()

    def test_filter_by_event_type(self):
        collector = MetricsCollector(":memory:")
        collector.record("parser", "parse_completed", 0.9)
        collector.record("parser", "parse_failed", 0.0)
        collector.record("parser", "parse_completed", 0.85)

        events = collector.get_events(module="parser", event_type="parse_completed")
        assert len(events) == 2
        collector.close()


# ── DataWarehouse ────────────────────────────────────────────────────────────

class TestDataWarehouse:

    def _make_warehouse(self):
        collector = MetricsCollector(":memory:")
        wh = DataWarehouse(collector._conn)
        return collector, wh

    def test_count(self):
        collector, wh = self._make_warehouse()
        collector.record("generation", "element_generated", 100.0)
        collector.record("generation", "element_generated", 200.0)
        collector.record("generation", "element_generated", 300.0)

        assert wh.count("generation", "element_generated") == 3
        collector.close()

    def test_average(self):
        collector, wh = self._make_warehouse()
        collector.record("generation", "element_generated", 100.0)
        collector.record("generation", "element_generated", 200.0)
        collector.record("generation", "element_generated", 300.0)

        avg = wh.average("generation", "element_generated")
        assert avg == 200.0
        collector.close()

    def test_aggregate_by_day(self):
        collector, wh = self._make_warehouse()
        # Insert events that will all be on the same day
        for i in range(5):
            collector.record("generation", "element_generated", 100.0)

        result = wh.aggregate("generation", "element_generated", period="day")
        assert len(result) >= 1
        # Sum of values
        assert result[0][1] == 500.0
        collector.close()

    def test_aggregate_by_month(self):
        collector, wh = self._make_warehouse()
        for i in range(3):
            collector.record("compliance", "check_completed", 1.0)

        result = wh.aggregate("compliance", "check_completed", period="month")
        assert len(result) >= 1
        collector.close()

    def test_trend(self):
        collector, wh = self._make_warehouse()
        for i in range(5):
            collector.record("generation", "element_generated", float(i))

        trend = wh.trend("generation", "element_generated", periods=12)
        assert isinstance(trend, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in trend)
        collector.close()

    def test_distinct_users(self):
        collector, wh = self._make_warehouse()
        collector.record("parser", "parse_completed", 0.9, user="alice")
        collector.record("parser", "parse_completed", 0.8, user="bob")
        collector.record("parser", "parse_completed", 0.7, user="alice")

        assert wh.distinct_users() == 2
        collector.close()


# ── KPICalculator ────────────────────────────────────────────────────────────

class TestKPICalculator:

    def _make_kpi(self):
        collector = MetricsCollector(":memory:")
        wh = DataWarehouse(collector._conn)
        kpi = KPICalculator(wh)
        return collector, kpi

    def test_parse_accuracy(self):
        collector, kpi = self._make_kpi()
        # 8 high confidence, 2 low
        for _ in range(8):
            collector.record("parser", "parse_completed", 0.90)
        for _ in range(2):
            collector.record("parser", "parse_completed", 0.70)

        accuracy = kpi.parse_accuracy()
        assert accuracy == 80.0  # 8/10 = 80%
        collector.close()

    def test_template_reuse_rate(self):
        collector, kpi = self._make_kpi()
        # 10 generations, 7 used templates
        for _ in range(10):
            collector.record("generation", "element_generated", 100.0)
        for _ in range(7):
            collector.record("template", "reuse_count", 1.0)

        rate = kpi.template_reuse_rate()
        assert rate == 70.0
        collector.close()

    def test_compliance_pass_rate_all_pass(self):
        collector, kpi = self._make_kpi()
        for _ in range(5):
            collector.record("compliance", "check_completed", 1.0)

        assert kpi.compliance_pass_rate() == 100.0
        collector.close()

    def test_compliance_pass_rate_partial(self):
        collector, kpi = self._make_kpi()
        for _ in range(3):
            collector.record("compliance", "check_completed", 1.0)
        for _ in range(2):
            collector.record("compliance", "check_completed", 0.0)

        rate = kpi.compliance_pass_rate()
        assert rate == 60.0
        collector.close()

    def test_cost_avoidance(self):
        collector, kpi = self._make_kpi()
        for _ in range(10):
            collector.record("generation", "element_generated", 100.0)

        cost = kpi.cost_avoidance_estimate(avg_manual_hours=4.0, hourly_rate=85.0)
        assert cost == 10 * 4.0 * 85.0
        collector.close()

    def test_elements_generated(self):
        collector, kpi = self._make_kpi()
        for _ in range(15):
            collector.record("generation", "element_generated", 100.0)

        assert kpi.elements_generated() == 15
        collector.close()

    def test_all_kpis(self):
        collector, kpi = self._make_kpi()
        collector.record("parser", "parse_completed", 0.90, user="alice")
        collector.record("generation", "element_generated", 100.0, user="alice")
        collector.record("compliance", "check_completed", 1.0, user="alice")

        result = kpi.all_kpis()
        assert "parse_accuracy" in result
        assert "template_reuse_rate" in result
        assert "compliance_pass_rate" in result
        assert "cost_avoidance_usd" in result
        assert "active_users_30d" in result
        assert "elements_generated" in result
        collector.close()


# ── DashboardGenerator ───────────────────────────────────────────────────────

class TestDashboardGenerator:

    def test_generate_html(self):
        collector = MetricsCollector(":memory:")
        wh = DataWarehouse(collector._conn)
        kpi = KPICalculator(wh)
        gen = DashboardGenerator(kpi, wh)

        # Add some data
        collector.record("parser", "parse_completed", 0.95, user="alice")
        collector.record("generation", "element_generated", 150.0, user="alice")
        collector.record("compliance", "check_completed", 1.0, user="alice")

        with tempfile.TemporaryDirectory() as d:
            path = gen.generate_html(d)
            assert path.is_file()
            assert path.name == "DASHBOARD.html"

            content = path.read_text()
            assert "<!DOCTYPE html>" in content
            assert "AEC OS" in content
            assert "svg" in content.lower()  # SVG charts
            assert "Overview KPIs" in content
            assert "Productivity" in content
            assert "Compliance" in content
            assert "Cost" in content
            assert "Collaboration" in content
            assert "Security" in content
            assert "System Health" in content

        collector.close()


# ── ReportExporter ───────────────────────────────────────────────────────────

class TestReportExporter:

    def test_export_json(self):
        exporter = ReportExporter()
        kpis = {"parse_accuracy": 95.0, "elements_generated": 100}
        result = exporter.export_json(kpis)
        data = json.loads(result)
        assert data["kpis"]["parse_accuracy"] == 95.0

    def test_export_csv(self):
        exporter = ReportExporter()
        events = [
            {"id": 1, "timestamp": "2024-01-01", "module": "parser",
             "event_type": "parse_completed", "value": 0.9,
             "metadata_json": "{}", "user": "alice"},
        ]
        with tempfile.TemporaryDirectory() as d:
            path = exporter.export_csv(events, Path(d) / "events.csv")
            assert path.is_file()
            content = path.read_text()
            assert "parser" in content
            assert "alice" in content

    def test_export_markdown(self):
        exporter = ReportExporter()
        kpis = {"parse_accuracy": 95.0, "elements_generated": 100}
        md = exporter.export_markdown(kpis)
        assert "# AEC OS Analytics Report" in md
        assert "95.0" in md
        assert "100" in md

    def test_export_html(self):
        exporter = ReportExporter()
        kpis = {"parse_accuracy": 95.0}
        html = exporter.export_html(kpis)
        assert "<!DOCTYPE html>" in html
        assert "95.0" in html

    def test_export_csv_empty(self):
        exporter = ReportExporter()
        with tempfile.TemporaryDirectory() as d:
            path = exporter.export_csv([], Path(d) / "empty.csv")
            assert path.is_file()
            content = path.read_text()
            assert "id,timestamp" in content
