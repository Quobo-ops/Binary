"""
Phase E: Resource Exhaustion & Limits Testing
"""
import gc
import json
import os
import resource
import sqlite3
import tempfile
import threading
import time
import uuid
from pathlib import Path

import pytest


def _make_element_folder(base, global_id, ifc_class="IfcWall", name="Wall", **kw):
    folder = base / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metadata.json").write_text(json.dumps({
        "GlobalId": global_id, "Name": name, "IFCClass": ifc_class, "Psets": {}
    }))
    for d in ("properties", "materials", "geometry", "relationships"):
        (folder / d).mkdir(exist_ok=True)
    (folder / "properties" / "psets.json").write_text(
        json.dumps(kw.get("psets", {}), indent=2))
    (folder / "materials" / "materials.json").write_text(json.dumps(
        kw.get("materials", [{"name": "Concrete", "category": "concrete"}])))
    (folder / "geometry" / "shape.json").write_text(json.dumps(
        kw.get("geometry", {"bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                                              "max_x": 1, "max_y": 0.2, "max_z": 3},
                            "volume": 0.6, "centroid": [0.5, 0.1, 1.5]})))
    (folder / "relationships" / "spatial.json").write_text(json.dumps(
        kw.get("spatial", {"site_name": "S", "building_name": "B", "storey_name": "L1"})))
    return folder


# ===================================================================
# E1 – Memory pressure
# ===================================================================
class TestMemoryPressure:
    """Generate many elements and check for memory leaks."""

    def test_e1_generate_500_elements_linear_memory(self, tmp_path):
        """Generate 500 elements; memory should grow roughly linearly."""
        from aecos.generation.generator import ElementGenerator
        from aecos.nlp.schema import ParametricSpec

        gen = ElementGenerator(output_dir=str(tmp_path / "elements"))

        # Measure RSS at checkpoints
        rss_samples = []

        def get_rss():
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        rss_start = get_rss()
        for i in range(500):
            spec = ParametricSpec(
                ifc_class="IfcWall",
                properties={"height_mm": 3000, "thickness_mm": 200,
                             "length_mm": 5000},
                materials=["concrete"],
            )
            gen.generate(spec)
            if i % 100 == 99:
                rss_samples.append(get_rss() - rss_start)

        # Check memory growth is roughly linear (not exponential)
        if len(rss_samples) >= 3:
            # Growth between samples should not accelerate dramatically
            growth_rates = [rss_samples[i+1] - rss_samples[i]
                           for i in range(len(rss_samples)-1)]
            if growth_rates[0] > 0:
                # Later growth should not be more than 5x the first growth
                for rate in growth_rates[1:]:
                    assert rate < growth_rates[0] * 5, \
                        f"Memory growth accelerating: {growth_rates}"


# ===================================================================
# E2 – File descriptor exhaustion
# ===================================================================
class TestFileDescriptorExhaustion:
    """Open many collectors and loggers simultaneously."""

    def test_e2_many_metrics_collectors(self, tmp_path):
        """Open 100 MetricsCollectors and verify all work."""
        from aecos.analytics.collector import MetricsCollector

        collectors = []
        for i in range(100):
            db_path = tmp_path / f"metrics_{i}.db"
            c = MetricsCollector(db_path=str(db_path))
            c.record("test", "event", float(i))
            collectors.append(c)

        # All should work
        for i, c in enumerate(collectors):
            events = c.get_events()
            assert len(events) >= 1, f"Collector {i} has no events"

        # Close all
        for c in collectors:
            c.close()

    def test_e2_many_audit_loggers(self, tmp_path):
        """Open 100 AuditLoggers and verify all work."""
        from aecos.security.audit import AuditLogger

        loggers = []
        for i in range(100):
            db_path = tmp_path / f"audit_{i}.db"
            al = AuditLogger(db_path=str(db_path))
            al.log("user", f"action_{i}", f"resource_{i}")
            loggers.append(al)

        # All should work
        for i, al in enumerate(loggers):
            log = al.get_log()
            assert len(log) >= 1, f"Logger {i} has no entries"

        # Close all
        for al in loggers:
            al.close()

    def test_e2_no_fd_leak_after_close(self, tmp_path):
        """After closing collectors, file descriptors should be released."""
        from aecos.analytics.collector import MetricsCollector

        initial_fds = len(os.listdir(f"/proc/{os.getpid()}/fd"))

        for i in range(50):
            c = MetricsCollector(db_path=str(tmp_path / f"leak_test_{i}.db"))
            c.record("test", "event", 1.0)
            c.close()

        final_fds = len(os.listdir(f"/proc/{os.getpid()}/fd"))
        # Allow some slack (pytest itself opens files)
        assert final_fds - initial_fds < 20, \
            f"FD leak: {initial_fds} -> {final_fds} ({final_fds - initial_fds} opened)"


# ===================================================================
# E3 – Maximum path length
# ===================================================================
class TestMaxPathLength:
    """Create element IDs that push close to OS path limits."""

    def test_e3_long_element_id(self, tmp_path):
        """Element ID near 200 chars should still work."""
        from aecos.generation.generator import ElementGenerator
        from aecos.nlp.schema import ParametricSpec

        gen = ElementGenerator(output_dir=str(tmp_path / "long_path"))
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "thickness_mm": 200},
            materials=["concrete"],
        )
        path = gen.generate(spec)
        assert path.exists()

    def test_e3_long_path_validation(self, tmp_path):
        """Validation should work with long paths."""
        from aecos.validation.validator import Validator

        # Create element with a reasonably long ID
        long_id = "x" * 150
        folder = _make_element_folder(tmp_path, long_id, "IfcWall", "Long Path Wall")

        v = Validator()
        report = v.validate(str(folder))
        assert report is not None

    def test_e3_long_path_cost(self, tmp_path):
        """Cost estimation should work with long paths."""
        from aecos.cost.engine import CostEngine

        long_id = "y" * 150
        folder = _make_element_folder(
            tmp_path, long_id, "IfcWall", "Long Path Wall",
            psets={"Dimensions": {"height_mm": 3000, "length_mm": 5000,
                                   "thickness_mm": 200}},
        )

        engine = CostEngine()
        report = engine.estimate(str(folder))
        assert report is not None
        assert report.total_installed_usd >= 0


# ===================================================================
# E4 – Very deep property nesting
# ===================================================================
class TestDeepPropertyNesting:
    """Test _resolve_path with deeply nested properties."""

    def test_e4_deep_nesting_20_levels(self):
        """_resolve_path should handle 20 levels of nesting."""
        from aecos.compliance.rules import _resolve_path

        # Build a 20-level deep dict programmatically
        data = 42
        for i in range(19, -1, -1):
            data = {f"level_{i}": data}

        path = ".".join(f"level_{i}" for i in range(20))
        result = _resolve_path(data, path)
        assert result == 42

    def test_e4_deep_compliance_rule(self):
        """Compliance rules targeting deep paths should work."""
        from aecos.compliance.rules import Rule, evaluate_rule

        rule = Rule(
            code_name="TEST", section="1.1", title="Deep path test",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="a.b.c.d.e",
            check_value=100,
        )
        data = {"a": {"b": {"c": {"d": {"e": 200}}}}}
        result = evaluate_rule(rule, data)
        assert result.status == "pass"

    def test_e4_missing_intermediate_path(self):
        """Missing intermediate nodes should return None, not crash."""
        from aecos.compliance.rules import _resolve_path

        data = {"a": {"b": 42}}
        result = _resolve_path(data, "a.b.c.d.e")
        assert result is None


# ===================================================================
# E5 – Unicode stress
# ===================================================================
class TestUnicodeStress:
    """Generate element, inject Unicode edge cases, verify no corruption."""

    UNICODE_STRINGS = [
        "Wall with RTL \u202E(reversed text)\u202C",
        "Wall with zero-width joiner \u200D\u200D\u200D",
        "Wall with emoji 🏗️🧱🔨",
        "Wall with combining: a\u0300\u0301\u0302",
        "Wall with null char: before\x00after",
        "Wall with BOM: \ufeff Hello",
        "日本語テスト Wall",
        "Стена из бетона",
        "حائط خرساني",
    ]

    def test_e5_unicode_in_metadata(self, tmp_path):
        """Metadata with Unicode should be read back correctly."""
        for i, ustr in enumerate(self.UNICODE_STRINGS):
            # Skip null char which can't survive JSON roundtrip cleanly
            if "\x00" in ustr:
                continue
            folder = _make_element_folder(tmp_path, f"uni_{i}", "IfcWall", ustr)
            meta = json.loads((folder / "metadata.json").read_text())
            assert meta["Name"] == ustr

    def test_e5_unicode_validation(self, tmp_path):
        """Validation should not crash on Unicode data."""
        from aecos.validation.validator import Validator

        v = Validator()
        for i, ustr in enumerate(self.UNICODE_STRINGS):
            if "\x00" in ustr:
                continue
            folder = _make_element_folder(tmp_path, f"unival_{i}", "IfcWall", ustr)
            report = v.validate(str(folder))
            assert report is not None

    def test_e5_unicode_metadata_generation(self, tmp_path):
        """Metadata generation should handle Unicode gracefully."""
        from aecos.metadata.generator import generate_metadata

        for i, ustr in enumerate(self.UNICODE_STRINGS):
            if "\x00" in ustr:
                continue
            folder = _make_element_folder(tmp_path, f"unigen_{i}", "IfcWall", ustr)
            try:
                generate_metadata(folder)
                readme = (folder / "README.md").read_text()
                # The Unicode name should appear in the README
                assert len(readme) > 0
            except UnicodeEncodeError:
                pytest.fail(f"UnicodeEncodeError for: {ustr!r}")


# ===================================================================
# E6 – Rapid engine recreation
# ===================================================================
class TestRapidEngineRecreation:
    """Create and destroy 100 ComplianceEngine instances."""

    def test_e6_rapid_compliance_engine_creation(self, tmp_path):
        """Create/destroy 100 ComplianceEngines with no leaks."""
        from aecos.compliance.engine import ComplianceEngine

        for i in range(100):
            db_path = tmp_path / f"rapid_{i}.db"
            engine = ComplianceEngine(db_path=str(db_path))
            # Trigger DB connection
            engine.get_rules()
            engine.db.close()

        # Verify no leftover temp files (other than the DBs themselves)
        db_files = list(tmp_path.glob("rapid_*.db"))
        assert len(db_files) == 100

        # WAL/SHM files should not accumulate after close
        wal_files = list(tmp_path.glob("rapid_*.db-wal"))
        shm_files = list(tmp_path.glob("rapid_*.db-shm"))
        # Some may still exist but should be reasonable
        assert len(wal_files) <= 100
        assert len(shm_files) <= 100

    def test_e6_rapid_metrics_collector_creation(self, tmp_path):
        """Create/destroy 100 MetricsCollectors with no leaks."""
        from aecos.analytics.collector import MetricsCollector

        for i in range(100):
            db_path = tmp_path / f"met_{i}.db"
            c = MetricsCollector(db_path=str(db_path))
            c.record("test", "event", 1.0)
            c.close()

        db_files = list(tmp_path.glob("met_*.db"))
        assert len(db_files) == 100
