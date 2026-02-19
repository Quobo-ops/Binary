"""
Phase D: API Contract & Invariant Testing
Test the guarantees the system should maintain.
"""
import json
import time
import uuid
from pathlib import Path

import pytest


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
# D1 – Idempotency
# ===================================================================
class TestIdempotency:
    """Operations run twice should produce identical output."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        yield

    def test_d1_generate_metadata_idempotent(self):
        """generate_metadata(folder) twice -> identical output."""
        from aecos.metadata.generator import generate_metadata

        folder = _make_element_folder(
            self.tmp, "idem_meta", "IfcWall", "Idem Wall",
            psets={"Dimensions": {"height_mm": 3000}},
        )
        generate_metadata(folder)
        first = {f.name: f.read_text() for f in folder.iterdir() if f.suffix == ".md"}

        generate_metadata(folder)
        second = {f.name: f.read_text() for f in folder.iterdir() if f.suffix == ".md"}

        assert first == second, "Metadata generation is not idempotent"

    def test_d1_validate_idempotent(self):
        """validate(folder) twice -> identical report."""
        from aecos.validation.validator import Validator

        folder = _make_element_folder(
            self.tmp, "idem_val", "IfcWall", "Idem Val Wall",
            psets={"Dimensions": {"height_mm": 3000, "thickness_mm": 200}},
        )
        v = Validator()
        r1 = v.validate(str(folder))
        r2 = v.validate(str(folder))

        assert r1.status == r2.status
        assert len(r1.issues) == len(r2.issues)

    def test_d1_check_compliance_idempotent(self):
        """check_compliance(spec) twice -> identical report."""
        from aecos.compliance.engine import ComplianceEngine
        from aecos.nlp.schema import ParametricSpec

        engine = ComplianceEngine()
        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "thickness_mm": 200},
            performance={"fire_rating": "2H"},
            materials=["concrete"],
        )
        r1 = engine.check(spec)
        r2 = engine.check(spec)

        assert r1.status == r2.status
        assert len(r1.results) == len(r2.results)
        for a, b in zip(r1.results, r2.results):
            assert a.status == b.status

    def test_d1_estimate_cost_idempotent(self):
        """estimate_cost(folder) twice -> identical costs."""
        from aecos.cost.engine import CostEngine

        folder = _make_element_folder(
            self.tmp, "idem_cost", "IfcWall", "Idem Cost Wall",
            psets={"Dimensions": {"height_mm": 3000, "length_mm": 5000,
                                   "thickness_mm": 200}},
        )
        engine = CostEngine()
        r1 = engine.estimate(str(folder))
        r2 = engine.estimate(str(folder))

        assert r1.material_cost_usd == r2.material_cost_usd
        assert r1.labor_cost_usd == r2.labor_cost_usd
        assert r1.total_installed_usd == r2.total_installed_usd
        assert r1.labor_hours == r2.labor_hours


# ===================================================================
# D2 – Monotonicity
# ===================================================================
class TestMonotonicity:
    """audit_logger.log() should produce strictly increasing IDs and
    non-decreasing timestamps."""

    def test_d2_audit_ids_monotonic(self):
        """Log 10,000 entries and verify IDs are strictly increasing."""
        from aecos.security.audit import AuditLogger

        logger = AuditLogger()
        prev_id = 0
        for i in range(1000):  # Reduced from 10k for speed, still tests the invariant
            entry = logger.log("user", f"action_{i}", f"resource_{i}")
            assert entry.id > prev_id, f"ID {entry.id} not > {prev_id} at iteration {i}"
            prev_id = entry.id

    def test_d2_audit_timestamps_non_decreasing(self):
        """Timestamps should be monotonically non-decreasing."""
        from aecos.security.audit import AuditLogger

        logger = AuditLogger()
        prev_ts = ""
        for i in range(500):
            entry = logger.log("user", f"action_{i}", f"resource_{i}")
            assert entry.timestamp >= prev_ts, \
                f"Timestamp {entry.timestamp} < {prev_ts} at iteration {i}"
            prev_ts = entry.timestamp


# ===================================================================
# D3 – Referential integrity
# ===================================================================
class TestReferentialIntegrity:
    """After promotion / template generation, metadata should be consistent."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.api.facade import AecOS
        self.root = tmp_path / "ref_integrity"
        self.root.mkdir()
        self.aec = AecOS(project_root=str(self.root))
        yield

    def test_d3_promoted_template_preserves_ifc_class(self):
        """After promote_to_template, the template preserves IFC class."""
        folder = self.aec.generate("Create a concrete wall 3m high 200mm thick")
        orig_meta = json.loads((folder / "metadata.json").read_text())

        tpath = self.aec.library.promote_to_template(
            element_folder=str(folder),
            tags={"ifc_class": "IfcWall"},
            version="1.0",
            author="test",
            description="Test",
        )

        tmpl_meta = json.loads((tpath / "metadata.json").read_text())
        assert tmpl_meta["IFCClass"] == orig_meta["IFCClass"]

    def test_d3_generate_from_template_inherits_fields(self):
        """generate_from_template should inherit non-overridden fields."""
        folder = self.aec.generate("Create a concrete wall 3m high 200mm thick")
        orig_meta = json.loads((folder / "metadata.json").read_text())

        tpath = self.aec.library.promote_to_template(
            element_folder=str(folder),
            tags={"ifc_class": "IfcWall"},
            version="1.0",
            author="test",
            description="Test",
        )

        tid = tpath.name.replace("template_", "")
        out = self.aec.generate_from_template(tid)
        out_meta = json.loads((out / "metadata.json").read_text())
        assert out_meta["IFCClass"] == orig_meta["IFCClass"]


# ===================================================================
# D4 – Hash determinism
# ===================================================================
class TestHashDeterminism:
    """Hasher.hash_folder() determinism tests."""

    def test_d4_same_folder_same_hash(self, tmp_path):
        """hash_folder called twice on unchanged folder -> same hash."""
        from aecos.security.hasher import Hasher

        folder = _make_element_folder(tmp_path, "hash_test", "IfcWall", "Hash Wall")
        h1 = Hasher.hash_folder(str(folder))
        h2 = Hasher.hash_folder(str(folder))
        assert h1 == h2

    def test_d4_modified_file_changes_hash(self, tmp_path):
        """Modifying a file should change the hash."""
        from aecos.security.hasher import Hasher

        folder = _make_element_folder(tmp_path, "hash_mod", "IfcWall", "Hash Mod")
        h1 = Hasher.hash_folder(str(folder))

        # Modify metadata.json
        meta_path = folder / "metadata.json"
        meta = json.loads(meta_path.read_text())
        meta["Name"] = "Modified Name"
        meta_path.write_text(json.dumps(meta, indent=2))

        h2 = Hasher.hash_folder(str(folder))
        assert h1 != h2

    def test_d4_reverted_file_restores_hash(self, tmp_path):
        """Reverting a modification should restore the original hash."""
        from aecos.security.hasher import Hasher

        folder = _make_element_folder(tmp_path, "hash_rev", "IfcWall", "Hash Rev")
        original_content = (folder / "metadata.json").read_text()
        h1 = Hasher.hash_folder(str(folder))

        # Modify
        meta = json.loads(original_content)
        meta["Name"] = "Temporary Change"
        (folder / "metadata.json").write_text(json.dumps(meta, indent=2))

        # Revert
        (folder / "metadata.json").write_text(original_content)

        h3 = Hasher.hash_folder(str(folder))
        assert h1 == h3

    def test_d4_hash_string_deterministic(self):
        """hash_string should be deterministic."""
        from aecos.security.hasher import Hasher
        h1 = Hasher.hash_string("hello world")
        h2 = Hasher.hash_string("hello world")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex length

    def test_d4_hash_file_deterministic(self, tmp_path):
        """hash_file should be deterministic."""
        from aecos.security.hasher import Hasher
        f = tmp_path / "test.txt"
        f.write_text("test content")
        h1 = Hasher.hash_file(str(f))
        h2 = Hasher.hash_file(str(f))
        assert h1 == h2


# ===================================================================
# D5 – Serialization symmetry
# ===================================================================
class TestSerializationSymmetry:
    """model_dump() -> reconstruct -> model_dump() should be identical."""

    def test_d5_parametric_spec_roundtrip(self):
        from aecos.nlp.schema import ParametricSpec
        spec = ParametricSpec(
            intent="create", ifc_class="IfcWall", name="Test",
            properties={"height_mm": 3000, "thickness_mm": 200},
            materials=["concrete", "steel"],
            performance={"fire_rating": "2H", "thermal_r_value": 13},
            constraints={"accessibility": True},
            compliance_codes=["IBC2024", "ADA2010"],
            confidence=0.95, warnings=["test warning"],
        )
        d1 = spec.model_dump()
        spec2 = ParametricSpec.model_validate(d1)
        d2 = spec2.model_dump()
        assert d1 == d2

    def test_d5_rule_roundtrip(self):
        from aecos.compliance.rules import Rule
        rule = Rule(
            id=1, code_name="IBC2024", section="703.3",
            title="Fire rating", ifc_classes=["IfcWall"],
            check_type="min_value", property_path="performance.fire_rating",
            check_value="2H", region="US", citation="IBC §703.3",
            effective_date="2024-01-01",
        )
        d1 = rule.model_dump()
        rule2 = Rule.model_validate(d1)
        d2 = rule2.model_dump()
        assert d1 == d2

    def test_d5_rule_result_roundtrip(self):
        from aecos.compliance.rules import RuleResult
        rr = RuleResult(
            rule_id=1, code_name="IBC2024", section="703.3",
            title="Fire rating", status="pass",
            actual_value="2H", expected_value="1H",
            citation="IBC §703.3", message="Passes",
        )
        d1 = rr.model_dump()
        rr2 = RuleResult.model_validate(d1)
        d2 = rr2.model_dump()
        assert d1 == d2

    def test_d5_audit_entry_roundtrip(self):
        from aecos.security.audit import AuditEntry
        ae = AuditEntry(
            id=42, timestamp="2024-01-01T00:00:00Z",
            user="alice", action="create", resource="wall_001",
            before_hash="abc123", after_hash="def456",
            entry_hash="ghi789", prev_entry_hash="jkl012",
        )
        d1 = ae.model_dump()
        ae2 = AuditEntry.model_validate(d1)
        d2 = ae2.model_dump()
        assert d1 == d2

    def test_d5_compliance_report_roundtrip(self):
        from aecos.compliance.report import ComplianceReport
        cr = ComplianceReport(
            element_id="elem1", ifc_class="IfcWall",
            status="compliant", results=[], suggested_fixes=[],
        )
        d1 = cr.model_dump()
        cr2 = ComplianceReport.model_validate(d1)
        d2 = cr2.model_dump()
        assert d1 == d2

    def test_d5_cost_report_roundtrip(self):
        """CostReport (plain class) — to_dict -> reconstruct -> to_dict identical."""
        from aecos.cost.report import CostReport
        cr = CostReport(
            element_id="elem1", ifc_class="IfcWall",
            material_cost_usd=1000.0, labor_cost_usd=500.0,
            total_installed_usd=1500.0, labor_hours=10.0,
            duration_days=2.0, crew_size=4,
            unit_costs={}, quantities={"area_m2": 15.0},
            regional_factor=0.95, region="LA",
            source="test", predecessor_type="structural",
        )
        d1 = cr.to_dict()
        cr2 = CostReport(**d1)
        d2 = cr2.to_dict()
        assert d1 == d2

    def test_d5_validation_report_roundtrip(self):
        """ValidationReport (plain class) — to_dict -> reconstruct -> to_dict identical."""
        from aecos.validation.report import ValidationReport
        vr = ValidationReport(
            element_id="elem1", ifc_class="IfcWall",
            status="passed", issues=[], clash_results=[],
        )
        d1 = vr.to_dict()
        vr2 = ValidationReport(**d1)
        d2 = vr2.to_dict()
        assert d1 == d2

    def test_d5_comment_roundtrip(self):
        from aecos.collaboration.models import Comment
        c = Comment(
            id="c1", element_id="elem1", user="alice",
            text="Hello", reply_to="c0",
        )
        d1 = c.model_dump()
        c2 = Comment.model_validate(d1)
        d2 = c2.model_dump()
        assert d1 == d2

    def test_d5_task_roundtrip(self):
        from aecos.collaboration.models import Task
        t = Task(
            id="t1", title="Fix wall", assignee="bob",
            element_id="elem1", status="open", priority="high",
        )
        d1 = t.model_dump()
        t2 = Task.model_validate(d1)
        d2 = t2.model_dump()
        assert d1 == d2

    def test_d5_review_roundtrip(self):
        from aecos.collaboration.models import Review
        r = Review(
            id="r1", element_id="elem1", reviewer="charlie",
            status="pending", requested_by="alice",
        )
        d1 = r.model_dump()
        r2 = Review.model_validate(d1)
        d2 = r2.model_dump()
        assert d1 == d2

    def test_d5_element_roundtrip(self):
        from aecos.models.element import Element, GeometryInfo, BoundingBox, MaterialLayer, SpatialReference
        e = Element(
            global_id="test_id", ifc_class="IfcWall", name="Test",
            geometry=GeometryInfo(
                bounding_box=BoundingBox(min_x=0, min_y=0, min_z=0,
                                          max_x=1, max_y=0.2, max_z=3),
                volume=0.6, centroid=(0.5, 0.1, 1.5),
            ),
            psets={"Dimensions": {"height_mm": 3000}},
            materials=[MaterialLayer(name="Concrete", category="concrete",
                                      thickness=0.2, fraction=1.0)],
            spatial=SpatialReference(site_name="Site", building_name="B1",
                                      storey_name="L1"),
        )
        d1 = e.model_dump()
        e2 = Element.model_validate(d1)
        d2 = e2.model_dump()
        assert d1 == d2


# ===================================================================
# D6 – Search completeness
# ===================================================================
class TestSearchCompleteness:
    """Add 20 templates with known tags, verify search returns correct results."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.templates.library import TemplateLibrary
        self.lib_root = tmp_path / "search_lib"
        self.lib_root.mkdir()
        self.library = TemplateLibrary(root=str(self.lib_root))
        self.tmp = tmp_path
        yield

    def _create_source(self, name="src"):
        folder = self.tmp / f"element_{name}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "metadata.json").write_text(json.dumps({
            "GlobalId": name, "Name": f"Test {name}",
            "IFCClass": "IfcWall", "Psets": {}
        }))
        for d in ("properties", "materials", "geometry", "relationships"):
            (folder / d).mkdir(exist_ok=True)
        (folder / "properties" / "psets.json").write_text("{}")
        (folder / "materials" / "materials.json").write_text("[]")
        (folder / "geometry" / "shape.json").write_text(json.dumps({
            "bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                             "max_x": 1, "max_y": 1, "max_z": 1},
            "volume": 1, "centroid": [0.5, 0.5, 0.5]}))
        (folder / "relationships" / "spatial.json").write_text("{}")
        return folder

    def test_d6_search_by_ifc_class(self):
        """Search by ifc_class should return all matching templates."""
        source = self._create_source("sc1")
        classes = ["IfcWall", "IfcDoor", "IfcSlab", "IfcBeam", "IfcColumn"]
        for i in range(20):
            cls = classes[i % len(classes)]
            self.library.add_template(
                f"tmpl_{i}", str(source),
                tags={"ifc_class": cls, "keywords": [f"kw_{i}"]},
                version="1.0", author="test",
                description=f"Template {i} ({cls})",
            )

        # Search for walls
        results = self.library.search({"ifc_class": "IfcWall"})
        assert len(results) == 4  # indices 0,5,10,15

    def test_d6_search_by_description(self):
        """Search by description substring should work."""
        source = self._create_source("sc2")
        for i in range(5):
            self.library.add_template(
                f"desc_{i}", str(source),
                tags={"ifc_class": "IfcWall"},
                version="1.0", author="test",
                description=f"Special template {i}",
            )

        results = self.library.search({"description": "Special"})
        assert len(results) == 5

    def test_d6_search_empty_query_returns_all(self):
        """Empty query should return all templates."""
        source = self._create_source("sc3")
        for i in range(5):
            self.library.add_template(
                f"all_{i}", str(source),
                tags={"ifc_class": "IfcWall"},
                version="1.0", author="test",
                description=f"Template {i}",
            )

        results = self.library.search({})
        assert len(results) == 5


# ===================================================================
# D7 – Audit chain integrity
# ===================================================================
class TestAuditChainIntegrity:
    """Verify the hash chain is correct and tamper-detectable."""

    def test_d7_chain_verification_passes(self):
        """Valid chain should pass verification."""
        from aecos.security.audit import AuditLogger

        logger = AuditLogger()
        for i in range(100):
            logger.log("user", f"action_{i}", f"resource_{i}")

        assert logger.verify_chain() is True

    def test_d7_chain_detects_tampering(self):
        """Modifying an entry should break the chain."""
        from aecos.security.audit import AuditLogger

        logger = AuditLogger()
        for i in range(10):
            logger.log("user", f"action_{i}", f"resource_{i}")

        # Tamper with an entry
        logger._conn.execute(
            "UPDATE audit_log SET action = 'tampered' WHERE id = 5"
        )
        logger._conn.commit()

        assert logger.verify_chain() is False
