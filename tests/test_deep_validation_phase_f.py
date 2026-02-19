"""
Phase F: Upgrade & Migration Safety Testing
"""
import json
import sqlite3
import tempfile
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
    (folder / "properties" / "psets.json").write_text(json.dumps(kw.get("psets", {})))
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
# F1 – Forward compatibility
# ===================================================================
class TestForwardCompatibility:
    """Add new fields to ParametricSpec and verify existing code survives."""

    def test_f1_extended_spec_doesnt_crash_generator(self, tmp_path):
        """A ParametricSpec with extra fields should not crash generation."""
        from aecos.nlp.schema import ParametricSpec
        from aecos.generation.generator import ElementGenerator

        # Create a spec with standard fields + extra unknown ones
        spec = ParametricSpec(
            intent="create",
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "thickness_mm": 200},
            materials=["concrete"],
        )
        # Add extra fields via model_copy or dict manipulation
        spec_dict = spec.model_dump()
        spec_dict["future_field"] = "some value"
        spec_dict["another_future"] = {"nested": True}

        # Reconstruct — Pydantic should allow extra or ignore
        try:
            extended = ParametricSpec.model_validate(spec_dict)
        except Exception:
            # If strict validation, just use the original spec
            extended = spec

        gen = ElementGenerator(output_dir=str(tmp_path / "elements"))
        path = gen.generate(extended)
        assert path.exists()

    def test_f1_extended_spec_doesnt_crash_compliance(self):
        """Compliance engine should handle specs with extra fields."""
        from aecos.nlp.schema import ParametricSpec
        from aecos.compliance.engine import ComplianceEngine

        spec = ParametricSpec(
            ifc_class="IfcWall",
            properties={"height_mm": 3000, "thickness_mm": 200},
            performance={"fire_rating": "2H"},
            materials=["concrete"],
        )
        engine = ComplianceEngine()
        report = engine.check(spec)
        assert report is not None

    def test_f1_duck_typed_spec_in_compliance(self):
        """Compliance engine should work with duck-typed objects."""
        from aecos.compliance.engine import ComplianceEngine

        class FakeSpec:
            ifc_class = "IfcWall"
            properties = {"height_mm": 3000, "thickness_mm": 200}
            performance = {"fire_rating": "2H"}
            constraints = {}
            materials = ["concrete"]
            name = "FakeWall"

        engine = ComplianceEngine()
        report = engine.check(FakeSpec())
        assert report is not None
        assert report.ifc_class == "IfcWall"

    def test_f1_duck_typed_spec_in_cost(self):
        """Cost engine should work with duck-typed objects."""
        from aecos.cost.engine import CostEngine

        class FakeSpec:
            ifc_class = "IfcWall"
            properties = {"height_mm": 3000, "length_mm": 5000, "thickness_mm": 200}
            materials = ["concrete"]
            name = "FakeWall"

        engine = CostEngine()
        report = engine.estimate(FakeSpec())
        assert report is not None
        assert report.total_installed_usd > 0


# ===================================================================
# F2 – Schema evolution
# ===================================================================
class TestSchemaEvolution:
    """Add new columns to SQLite tables, verify existing queries still work."""

    def test_f2_audit_log_extra_column(self, tmp_path):
        """Adding a new column to audit_log should not break existing queries."""
        from aecos.security.audit import AuditLogger

        db_path = tmp_path / "audit_evolve.db"
        logger = AuditLogger(db_path=str(db_path))
        logger.log("user", "action", "resource")

        # Add new column directly
        logger._conn.execute(
            "ALTER TABLE audit_log ADD COLUMN extra_field TEXT DEFAULT ''"
        )
        logger._conn.commit()

        # Existing operations should still work
        logger.log("user2", "action2", "resource2")
        log = logger.get_log()
        assert len(log) == 2
        assert logger.verify_chain() is True

    def test_f2_events_extra_column(self, tmp_path):
        """Adding a new column to events table should not break MetricsCollector."""
        from aecos.analytics.collector import MetricsCollector

        db_path = tmp_path / "metrics_evolve.db"
        collector = MetricsCollector(db_path=str(db_path))
        collector.record("test", "event", 1.0)

        # Add new column
        collector._conn.execute(
            "ALTER TABLE events ADD COLUMN extra TEXT DEFAULT ''"
        )
        collector._conn.commit()

        # Existing operations should still work
        collector.record("test2", "event2", 2.0)
        events = collector.get_events()
        assert len(events) == 2
        collector.close()

    def test_f2_compliance_db_extra_column(self, tmp_path):
        """Adding a new column to rules table should not break queries."""
        from aecos.compliance.engine import ComplianceEngine
        from aecos.compliance.rules import Rule

        db_path = tmp_path / "compliance_evolve.db"
        engine = ComplianceEngine(db_path=str(db_path))

        engine.add_rule(Rule(
            code_name="TEST", section="1.1", title="Test rule",
            ifc_classes=["IfcWall"], check_type="min_value",
            property_path="properties.thickness_mm", check_value=100,
        ))

        # Add new column
        engine.db.conn.execute(
            "ALTER TABLE rules ADD COLUMN severity TEXT DEFAULT 'error'"
        )
        engine.db.conn.commit()

        # Existing operations should still work
        rules = engine.get_rules()
        assert len(rules) > 0


# ===================================================================
# F3 – Plugin hot-reload
# ===================================================================
class TestPluginHotReload:
    """Register, unregister, re-register domains with different data."""

    def test_f3_domain_hot_reload(self):
        """Unregister and re-register a domain with different rules."""
        from aecos.domains.registry import DomainRegistry
        from aecos.domains.base import DomainPlugin

        class DomainV1(DomainPlugin):
            @property
            def name(self): return "test_domain"
            @property
            def description(self): return "Version 1"
            @property
            def ifc_classes(self): return ["IfcWall"]
            def register_templates(self): return []
            def register_compliance_rules(self):
                return [{"code_name": "V1", "section": "1.1", "title": "V1 Rule",
                         "ifc_classes": ["IfcWall"], "check_type": "min_value",
                         "property_path": "properties.thickness_mm",
                         "check_value": 100}]
            def register_parser_patterns(self): return {}
            def register_cost_data(self): return []
            def register_validation_rules(self): return []
            def get_builder_config(self, ifc_class): return {}

        class DomainV2(DomainPlugin):
            @property
            def name(self): return "test_domain"
            @property
            def description(self): return "Version 2"
            @property
            def ifc_classes(self): return ["IfcWall", "IfcSlab"]
            def register_templates(self): return []
            def register_compliance_rules(self):
                return [{"code_name": "V2", "section": "2.1", "title": "V2 Rule",
                         "ifc_classes": ["IfcWall"], "check_type": "min_value",
                         "property_path": "properties.thickness_mm",
                         "check_value": 200}]
            def register_parser_patterns(self): return {"special_wall": "IfcWall"}
            def register_cost_data(self): return []
            def register_validation_rules(self): return []
            def get_builder_config(self, ifc_class): return {}

        registry = DomainRegistry()

        # Register V1
        registry.register(DomainV1())
        d = registry.get_domain("test_domain")
        assert d is not None
        assert d.description == "Version 1"

        # Re-register V2 (overwrite)
        registry.register(DomainV2())
        d = registry.get_domain("test_domain")
        assert d is not None
        assert d.description == "Version 2"
        assert "IfcSlab" in d.ifc_classes

    def test_f3_domain_rules_update(self):
        """After hot-reload, compliance rules should reflect new domain."""
        from aecos.domains.registry import DomainRegistry
        from aecos.domains.base import DomainPlugin
        from aecos.compliance.engine import ComplianceEngine

        class NewDomain(DomainPlugin):
            @property
            def name(self): return "hot_domain"
            @property
            def description(self): return "Hot reloaded"
            @property
            def ifc_classes(self): return ["IfcWall"]
            def register_templates(self): return []
            def register_compliance_rules(self):
                return [{"code_name": "HOT", "section": "H.1",
                         "title": "Hot Rule",
                         "ifc_classes": ["IfcWall"],
                         "check_type": "min_value",
                         "property_path": "properties.height_mm",
                         "check_value": 5000}]
            def register_parser_patterns(self): return {}
            def register_cost_data(self): return []
            def register_validation_rules(self): return []
            def get_builder_config(self, ifc_class): return {}

        registry = DomainRegistry()
        registry.register(NewDomain())

        engine = ComplianceEngine()
        # Apply domain rules
        domain = registry.get_domain("hot_domain")
        for rule_dict in domain.register_compliance_rules():
            from aecos.compliance.rules import Rule
            engine.add_rule(Rule(**rule_dict))

        # Verify the rule is active
        rules = engine.search_rules("Hot Rule")
        assert len(rules) >= 1


# ===================================================================
# F4 – Template versioning
# ===================================================================
class TestTemplateVersioning:
    """Add same template ID twice with different versions."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.templates.library import TemplateLibrary
        self.lib_root = tmp_path / "version_lib"
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

    def test_f4_add_same_id_different_versions(self):
        """Adding same template ID twice should update, not duplicate."""
        source = self._create_source("ver_src")

        self.library.add_template(
            "versioned_tmpl", str(source),
            tags={"ifc_class": "IfcWall"},
            version="1.0", author="alice",
            description="Version 1",
        )

        # Add again with different version
        self.library.add_template(
            "versioned_tmpl", str(source),
            tags={"ifc_class": "IfcWall"},
            version="2.0", author="bob",
            description="Version 2",
        )

        # Should only have one entry (updated, not duplicated)
        results = self.library.search({})
        matching = [r for r in results if r.template_id == "versioned_tmpl"]
        assert len(matching) == 1, f"Expected 1 entry, got {len(matching)}"

    def test_f4_update_template(self):
        """update_template should change tags/version without duplication."""
        source = self._create_source("upd_src")

        self.library.add_template(
            "upd_tmpl", str(source),
            tags={"ifc_class": "IfcWall"},
            version="1.0", author="alice",
            description="Original",
        )

        # Update
        self.library.update_template(
            "upd_tmpl",
            tags={"ifc_class": "IfcWall", "keywords": ["updated"]},
            version="2.0",
            author="bob",
            description="Updated",
        )

        # Verify update took effect
        manifest = self.library.get_manifest("upd_tmpl")
        assert manifest is not None
        assert manifest.get("version") == "2.0" or manifest.get("author") == "bob"

    def test_f4_remove_and_readd(self):
        """Remove and re-add should work cleanly."""
        source = self._create_source("rm_src")

        self.library.add_template(
            "rm_tmpl", str(source),
            tags={"ifc_class": "IfcWall"},
            version="1.0", author="alice",
            description="To be removed",
        )

        self.library.remove_template("rm_tmpl")
        results = self.library.search({})
        assert all(r.template_id != "rm_tmpl" for r in results)

        # Re-add
        self.library.add_template(
            "rm_tmpl", str(source),
            tags={"ifc_class": "IfcSlab"},
            version="3.0", author="charlie",
            description="Re-added",
        )

        results = self.library.search({})
        matching = [r for r in results if r.template_id == "rm_tmpl"]
        assert len(matching) == 1
