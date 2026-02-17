"""Tests for Item 10 — Cost & Schedule Hooks.

Covers: CostEngine, estimator, pricing, schedule, regional, and reports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aecos.cost.engine import CostEngine
from aecos.cost.estimator import calculate_quantities
from aecos.cost.pricing import LocalProvider, UnitCost
from aecos.cost.regional import get_regional_factor, list_regions
from aecos.cost.report import CostReport
from aecos.cost.schedule import estimate_schedule
from aecos.cost.seed_data import SEED_PRICING
from aecos.generation.generator import ElementGenerator
from aecos.nlp.schema import ParametricSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wall_folder(tmp_path: Path) -> Path:
    gen = ElementGenerator(tmp_path)
    spec = ParametricSpec(
        ifc_class="IfcWall",
        name="Cost Test Wall",
        properties={"thickness_mm": 200.0, "height_mm": 3000.0, "length_mm": 5000.0},
        materials=["concrete"],
        performance={"fire_rating": "2H"},
    )
    return gen.generate(spec)


def _make_beam_folder(tmp_path: Path) -> Path:
    gen = ElementGenerator(tmp_path)
    spec = ParametricSpec(
        ifc_class="IfcBeam",
        properties={"depth_mm": 500.0, "width_mm": 300.0, "length_mm": 6000.0},
        materials=["steel"],
    )
    return gen.generate(spec)


# ---------------------------------------------------------------------------
# Quantity Takeoff
# ---------------------------------------------------------------------------

class TestQuantityTakeoff:
    """Test quantity calculation from properties."""

    def test_wall_quantities(self):
        q = calculate_quantities("IfcWall", {"height_mm": 3000, "length_mm": 5000, "thickness_mm": 200})
        assert "area_m2" in q
        assert q["area_m2"] == pytest.approx(15.0)
        assert "volume_m3" in q
        assert q["volume_m3"] == pytest.approx(3.0)

    def test_door_quantities(self):
        q = calculate_quantities("IfcDoor", {"width_mm": 914, "height_mm": 2134})
        assert "count" in q
        assert q["count"] == 1.0
        assert "area_m2" in q

    def test_window_quantities(self):
        q = calculate_quantities("IfcWindow", {"width_mm": 1200, "height_mm": 1500})
        assert q["count"] == 1.0
        assert q["area_m2"] == pytest.approx(1.8)

    def test_slab_quantities(self):
        q = calculate_quantities("IfcSlab", {"length_mm": 6000, "width_mm": 6000, "thickness_mm": 200})
        assert q["area_m2"] == pytest.approx(36.0)
        assert q["volume_m3"] == pytest.approx(7.2)

    def test_column_quantities(self):
        q = calculate_quantities("IfcColumn", {"width_mm": 400, "height_mm": 3600, "depth_mm": 400})
        assert "volume_m3" in q
        assert q["volume_m3"] > 0

    def test_beam_quantities(self):
        q = calculate_quantities("IfcBeam", {"depth_mm": 500, "width_mm": 300, "length_mm": 6000})
        assert "length_m" in q
        assert q["length_m"] == pytest.approx(6.0)
        assert "volume_m3" in q


# ---------------------------------------------------------------------------
# Pricing Provider
# ---------------------------------------------------------------------------

class TestPricingProvider:
    """Test the LocalProvider with embedded seed data."""

    def test_local_provider_available(self):
        provider = LocalProvider()
        assert provider.is_available()

    def test_concrete_wall_pricing(self):
        provider = LocalProvider()
        uc = provider.get_unit_cost("concrete", "IfcWall")
        assert uc is not None
        assert uc.material_cost_per_unit > 0
        assert uc.labor_cost_per_unit > 0
        assert uc.unit_type == "m2"

    def test_steel_beam_pricing(self):
        provider = LocalProvider()
        uc = provider.get_unit_cost("steel", "IfcBeam")
        assert uc.unit_type == "m"

    def test_unknown_material_fallback(self):
        provider = LocalProvider()
        uc = provider.get_unit_cost("unknownium", "IfcFoo")
        assert uc is not None
        assert uc.material_cost_per_unit > 0

    def test_all_seed_data_valid(self):
        """All seed data entries return valid pricing."""
        provider = LocalProvider()
        for (material, ifc_class) in SEED_PRICING:
            uc = provider.get_unit_cost(material, ifc_class)
            assert uc is not None
            assert uc.material_cost_per_unit > 0
            assert uc.labor_cost_per_unit > 0
            assert uc.unit_type != ""
            assert uc.source != ""


# ---------------------------------------------------------------------------
# Regional Factors
# ---------------------------------------------------------------------------

class TestRegionalFactors:
    """Test regional cost adjustment factors."""

    def test_louisiana_factor(self):
        factor = get_regional_factor("LA")
        assert factor == pytest.approx(0.92)

    def test_california_factor(self):
        factor = get_regional_factor("CA")
        assert factor == pytest.approx(1.15)

    def test_new_york_factor(self):
        factor = get_regional_factor("NY")
        assert factor == pytest.approx(1.35)

    def test_texas_factor(self):
        factor = get_regional_factor("TX")
        assert factor == pytest.approx(0.88)

    def test_us_average(self):
        factor = get_regional_factor("US_AVG")
        assert factor == pytest.approx(1.0)

    def test_default_region(self):
        factor = get_regional_factor(None)
        assert factor == pytest.approx(0.92)  # Louisiana default

    def test_unknown_region_defaults_1(self):
        factor = get_regional_factor("MARS")
        assert factor == pytest.approx(1.0)

    def test_list_regions(self):
        regions = list_regions()
        assert "LA" in regions
        assert "CA" in regions
        assert len(regions) >= 5


# ---------------------------------------------------------------------------
# Schedule Estimation
# ---------------------------------------------------------------------------

class TestScheduleEstimation:
    """Test schedule/duration estimation."""

    def test_wall_schedule(self):
        q = calculate_quantities("IfcWall", {"height_mm": 3000, "length_mm": 5000, "thickness_mm": 200})
        schedule = estimate_schedule("IfcWall", q)
        assert schedule["duration_days"] > 0
        assert schedule["crew_size"] > 0
        assert schedule["predecessor_type"] != ""

    def test_door_schedule(self):
        q = calculate_quantities("IfcDoor", {"width_mm": 914, "height_mm": 2134})
        schedule = estimate_schedule("IfcDoor", q)
        assert schedule["duration_days"] > 0
        assert schedule["crew_size"] > 0

    def test_beam_schedule(self):
        q = calculate_quantities("IfcBeam", {"depth_mm": 500, "width_mm": 300, "length_mm": 6000})
        schedule = estimate_schedule("IfcBeam", q)
        assert schedule["duration_days"] > 0

    def test_unknown_class_schedule(self):
        schedule = estimate_schedule("IfcFoo", {"count": 1})
        assert schedule["duration_days"] > 0


# ---------------------------------------------------------------------------
# CostEngine - Main Entry Point
# ---------------------------------------------------------------------------

class TestCostEngine:
    """Test the CostEngine end-to-end."""

    def test_estimate_concrete_wall_folder(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)

        assert isinstance(report, CostReport)
        assert report.material_cost_usd > 0
        assert report.labor_cost_usd > 0
        assert report.total_installed_usd > 0
        assert report.total_installed_usd == pytest.approx(
            report.material_cost_usd + report.labor_cost_usd
        )

    def test_estimate_with_louisiana_region(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine(region="LA")
        report = engine.estimate(folder)
        assert report.regional_factor == pytest.approx(0.92)
        assert report.region == "LA"

    def test_estimate_with_california_region(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder, region="CA")
        assert report.regional_factor == pytest.approx(1.15)

    def test_estimate_from_spec(self):
        spec = ParametricSpec(
            ifc_class="IfcWall",
            name="Spec Wall",
            properties={"thickness_mm": 200, "height_mm": 3000, "length_mm": 5000},
            materials=["concrete"],
        )
        engine = CostEngine()
        report = engine.estimate(spec)
        assert report.total_installed_usd > 0

    def test_estimate_beam(self, tmp_path: Path):
        folder = _make_beam_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)
        assert report.total_installed_usd > 0
        assert report.duration_days > 0
        assert report.crew_size > 0

    def test_labor_hours_positive(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)
        assert report.labor_hours > 0

    def test_schedule_in_report(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)
        assert report.duration_days > 0
        assert report.crew_size > 0
        assert report.predecessor_type != ""


# ---------------------------------------------------------------------------
# CostReport
# ---------------------------------------------------------------------------

class TestCostReport:
    """Test CostReport Markdown and JSON generation."""

    def test_to_markdown(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)
        md = report.to_markdown()
        assert "# Cost Report" in md
        assert "Material Cost" in md
        assert "Labor Cost" in md
        assert "Total Installed" in md
        assert "$" in md

    def test_to_schedule_markdown(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)
        md = report.to_schedule_markdown()
        assert "# Schedule" in md
        assert "Duration" in md
        assert "Crew Size" in md

    def test_to_json(self, tmp_path: Path):
        folder = _make_wall_folder(tmp_path)
        engine = CostEngine()
        report = engine.estimate(folder)
        data = json.loads(report.to_json())
        assert "material_cost_usd" in data
        assert "labor_cost_usd" in data
        assert "total_installed_usd" in data
        assert data["total_installed_usd"] > 0

    def test_round_trip_spec_to_report_to_markdown(self):
        """Full round-trip: spec → cost → report → markdown."""
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"thickness_mm": 200, "height_mm": 3000, "length_mm": 5000},
            materials=["concrete"],
        )
        engine = CostEngine()
        report = engine.estimate(spec, region="LA")
        md = report.to_markdown()
        assert "# Cost Report" in md
        assert report.regional_factor == pytest.approx(0.92)

        schedule_md = report.to_schedule_markdown()
        assert "# Schedule" in schedule_md
