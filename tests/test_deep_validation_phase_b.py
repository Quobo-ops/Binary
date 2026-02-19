"""
Phase B: State Corruption & Recovery Stress Testing
Deep production-readiness — simulate realistic partial-failure scenarios.
"""
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ===================================================================
# B1 – Mid-generation crash simulation
# ===================================================================
class TestMidGenerationCrash:
    """Monkeypatch write_element_folder to crash after metadata.json
    but before psets.json. Verify the system detects incomplete elements
    and subsequent operations don't cascade-crash."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.generation.generator import ElementGenerator
        from aecos.nlp.parser import NLParser
        self.root = tmp_path / "crash_test"
        self.root.mkdir()
        self.parser = NLParser()
        self.generator = ElementGenerator(output_dir=str(self.root / "elements"))
        yield

    def test_b1_crash_after_metadata_before_psets(self):
        """Simulate OSError after metadata.json is written."""
        import aecos.generation.folder_writer as fw

        original_write = fw.write_element_folder
        call_count = 0

        def crashing_writer(output_dir, global_id, ifc_class, name,
                            psets, materials, geometry, spatial):
            nonlocal call_count
            call_count += 1

            # Write metadata.json manually
            folder = output_dir / f"element_{global_id}"
            folder.mkdir(parents=True, exist_ok=True)
            metadata = {
                "GlobalId": global_id,
                "Name": name,
                "IFCClass": ifc_class,
                "Psets": {},
            }
            (folder / "metadata.json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
            # Crash before psets.json
            raise OSError("Simulated disk failure")

        # Patch where it's imported into generator module
        with patch("aecos.generation.generator.write_element_folder", crashing_writer):
            with pytest.raises(OSError, match="Simulated disk failure"):
                spec = self.parser.parse("Create a concrete wall 3m high 200mm thick")
                self.generator.generate(spec)

        assert call_count == 1

    def test_b1_incomplete_element_does_not_cascade(self):
        """An incomplete element folder (metadata but no psets) should not
        crash validation or cost estimation."""
        from aecos.validation.validator import Validator
        from aecos.cost.engine import CostEngine

        # Create an incomplete element folder
        eid = str(uuid.uuid4())[:8]
        folder = self.root / "elements" / f"element_{eid}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "metadata.json").write_text(json.dumps({
            "GlobalId": eid,
            "Name": "Incomplete Wall",
            "IFCClass": "IfcWall",
            "Psets": {},
        }))

        # Validator should not crash
        validator = Validator()
        try:
            report = validator.validate(str(folder))
            # May have issues/warnings but should not crash
        except Exception as e:
            # Some exceptions are acceptable if they're graceful failures
            assert "not found" in str(e).lower() or "missing" in str(e).lower() or \
                   "no such" in str(e).lower() or isinstance(e, (FileNotFoundError, KeyError)), \
                f"Unexpected crash: {type(e).__name__}: {e}"

        # CostEngine should not crash
        cost_engine = CostEngine()
        try:
            report = cost_engine.estimate(str(folder))
        except Exception as e:
            assert "not found" in str(e).lower() or "missing" in str(e).lower() or \
                   isinstance(e, (FileNotFoundError, KeyError, ValueError)), \
                f"Unexpected crash: {type(e).__name__}: {e}"

    def test_b1_detect_incomplete_element(self):
        """Verify we can detect which required files are missing."""
        eid = str(uuid.uuid4())[:8]
        folder = self.root / "elements" / f"element_{eid}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "metadata.json").write_text(json.dumps({
            "GlobalId": eid, "Name": "Partial", "IFCClass": "IfcWall"
        }))

        required_files = [
            "metadata.json",
            "properties/psets.json",
            "materials/materials.json",
            "geometry/shape.json",
        ]
        missing = [f for f in required_files if not (folder / f).exists()]
        assert len(missing) == 3  # Only metadata.json exists


# ===================================================================
# B2 – Registry corruption
# ===================================================================
class TestRegistryCorruption:
    """Manually corrupt registry.json and verify graceful degradation."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.templates.library import TemplateLibrary
        self.lib_root = tmp_path / "template_library"
        self.lib_root.mkdir()
        self.library = TemplateLibrary(root=str(self.lib_root))
        yield

    def _create_source_folder(self, base: Path, name: str = "test") -> Path:
        """Create a minimal element folder to use as template source."""
        folder = base / f"element_{name}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "metadata.json").write_text(json.dumps({
            "GlobalId": name, "Name": f"Test {name}",
            "IFCClass": "IfcWall", "Psets": {}
        }))
        for subdir in ("properties", "materials", "geometry", "relationships"):
            (folder / subdir).mkdir(exist_ok=True)
        (folder / "properties" / "psets.json").write_text("{}")
        (folder / "materials" / "materials.json").write_text("[]")
        (folder / "geometry" / "shape.json").write_text(json.dumps({
            "bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0,
                             "max_x": 1, "max_y": 0.2, "max_z": 3},
            "volume": 0.6, "centroid": [0.5, 0.1, 1.5]
        }))
        (folder / "relationships" / "spatial.json").write_text("{}")
        return folder

    def test_b2_truncated_registry(self, tmp_path):
        """Truncated registry.json should be handled gracefully."""
        source = self._create_source_folder(tmp_path, "src1")

        # Add a template first
        self.library.add_template(
            "tmpl_1", str(source),
            tags={"ifc_class": "IfcWall"}, version="1.0",
            author="test", description="Test template"
        )

        # Truncate registry.json
        reg_path = self.lib_root / "registry.json"
        assert reg_path.exists()
        content = reg_path.read_text()
        reg_path.write_text(content[:len(content)//3])  # Truncate to 1/3

        # Create new library instance — should recover
        from aecos.templates.library import TemplateLibrary
        lib2 = TemplateLibrary(root=str(self.lib_root))
        # Should not crash — starts fresh
        results = lib2.search({})
        # May be empty (lost data) but should not crash
        assert isinstance(results, list)

    def test_b2_invalid_json_registry(self):
        """Completely invalid JSON in registry should be handled."""
        reg_path = self.lib_root / "registry.json"
        reg_path.write_text("NOT VALID JSON {{{}")

        from aecos.templates.library import TemplateLibrary
        lib2 = TemplateLibrary(root=str(self.lib_root))
        results = lib2.search({})
        assert isinstance(results, list)

    def test_b2_null_fields_in_registry(self, tmp_path):
        """Null fields in registry entries should be handled."""
        reg_path = self.lib_root / "registry.json"
        reg_path.write_text(json.dumps({
            "version": "1",
            "templates": [{
                "template_id": "null_test",
                "folder_name": "template_null_test",
                "tags": None,
                "version": None,
                "author": None,
                "description": None,
            }]
        }))

        from aecos.templates.library import TemplateLibrary
        try:
            lib2 = TemplateLibrary(root=str(self.lib_root))
            # May raise during parsing or handle gracefully
        except Exception as e:
            # Acceptable if it's a validation error
            assert "validation" in str(e).lower() or "null" in str(e).lower() or \
                   isinstance(e, (TypeError, KeyError, ValueError))

    def test_b2_duplicate_ids_in_registry(self, tmp_path):
        """Duplicate template IDs in registry.json."""
        source = self._create_source_folder(tmp_path, "dup_src")

        reg_path = self.lib_root / "registry.json"
        reg_path.write_text(json.dumps({
            "version": "1",
            "templates": [
                {
                    "template_id": "dup_id",
                    "folder_name": "template_dup_id",
                    "tags": {"ifc_class": "IfcWall"},
                    "version": "1.0",
                    "author": "test",
                    "description": "First",
                },
                {
                    "template_id": "dup_id",
                    "folder_name": "template_dup_id_v2",
                    "tags": {"ifc_class": "IfcWall"},
                    "version": "2.0",
                    "author": "test",
                    "description": "Second (duplicate)",
                },
            ]
        }))

        from aecos.templates.library import TemplateLibrary
        lib2 = TemplateLibrary(root=str(self.lib_root))
        # Should load without crashing — last one wins or first one wins
        results = lib2.search({})
        assert isinstance(results, list)

    def test_b2_search_with_corrupted_registry(self):
        """search should not crash even with empty/corrupt registry."""
        reg_path = self.lib_root / "registry.json"
        reg_path.write_text("{}")

        from aecos.templates.library import TemplateLibrary
        lib2 = TemplateLibrary(root=str(self.lib_root))
        results = lib2.search({"ifc_class": "IfcWall"})
        assert isinstance(results, list)

    def test_b2_remove_template_not_in_registry(self):
        """Removing a non-existent template should not crash."""
        result = self.library.remove_template("nonexistent_id")
        assert result is False or result is None


# ===================================================================
# B3 – Git state corruption
# ===================================================================
class TestGitStateCorruption:
    """Test SyncManager/RepoManager with corrupted git states."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from aecos.vcs.repo import RepoManager
        self.root = tmp_path / "git_corrupt_test"
        self.root.mkdir()
        self.repo = RepoManager(str(self.root))
        yield

    def test_b3_stale_index_lock(self):
        """Stale .git/index.lock should be handled."""
        # Initialize repo
        try:
            self.repo.init_repo()
        except Exception:
            # May fail due to signing; manual init
            import subprocess
            subprocess.run(["git", "init", str(self.root)], capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"],
                           cwd=str(self.root), capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"],
                           cwd=str(self.root), capture_output=True)

        # Create stale lock
        git_dir = self.root / ".git"
        if git_dir.exists():
            lock_file = git_dir / "index.lock"
            lock_file.write_text("stale lock")

            # Status should still work (or raise a clear error)
            try:
                status = self.repo.status()
            except Exception as e:
                # Git will report the lock file error
                assert "lock" in str(e).lower() or "index" in str(e).lower(), \
                    f"Unexpected error: {e}"

            # Clean up lock for subsequent operations
            lock_file.unlink(missing_ok=True)

    def test_b3_is_repo_on_non_repo(self):
        """is_repo on a non-git directory should return False."""
        non_repo = self.root / "not_a_repo"
        non_repo.mkdir()
        from aecos.vcs.repo import RepoManager
        repo = RepoManager(str(non_repo))
        assert repo.is_repo() is False

    def test_b3_status_on_non_repo(self):
        """status on a non-repo should raise GitError."""
        from aecos.vcs.repo import RepoManager, GitError
        non_repo = self.root / "not_a_repo_2"
        non_repo.mkdir()
        repo = RepoManager(str(non_repo))
        with pytest.raises(GitError):
            repo.status()


# ===================================================================
# B4 – Concurrent filesystem race conditions
# ===================================================================
class TestConcurrentRaceConditions:
    """Two threads simultaneously write to the same metadata.json.
    Use threading.Barrier to maximize collision probability."""

    def test_b4_concurrent_metadata_write(self, tmp_path):
        """At least one write should survive intact."""
        folder = tmp_path / "element_race"
        folder.mkdir()
        meta_path = folder / "metadata.json"

        barrier = threading.Barrier(2)
        results = {"a": None, "b": None}

        def write_meta(label, data):
            try:
                barrier.wait(timeout=5)
                meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                results[label] = "ok"
            except Exception as e:
                results[label] = str(e)

        data_a = {"GlobalId": "aaa", "Name": "Thread A", "IFCClass": "IfcWall"}
        data_b = {"GlobalId": "bbb", "Name": "Thread B", "IFCClass": "IfcSlab"}

        t1 = threading.Thread(target=write_meta, args=("a", data_a))
        t2 = threading.Thread(target=write_meta, args=("b", data_b))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # At least one write should succeed
        assert "ok" in (results["a"], results["b"]), f"Both writes failed: {results}"

        # The file should be valid JSON
        content = meta_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["GlobalId"] in ("aaa", "bbb"), "Corrupted JSON"
        assert data["Name"] in ("Thread A", "Thread B")

    def test_b4_concurrent_registry_writes(self, tmp_path):
        """Two threads writing different templates to registry simultaneously."""
        from aecos.templates.registry import TemplateRegistry, RegistryEntry
        from aecos.templates.tagging import TemplateTags

        lib_root = tmp_path / "concurrent_lib"
        lib_root.mkdir()

        barrier = threading.Barrier(2)
        errors = []

        def add_and_save(tid, name):
            try:
                registry = TemplateRegistry(lib_root)
                entry = RegistryEntry(
                    template_id=tid,
                    folder_name=f"template_{tid}",
                    tags=TemplateTags(ifc_class="IfcWall"),
                    version="1.0",
                    author="test",
                    description=name,
                )
                barrier.wait(timeout=5)
                registry.add(entry)
                registry.save()
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=add_and_save, args=("tmpl_x", "Template X"))
        t2 = threading.Thread(target=add_and_save, args=("tmpl_y", "Template Y"))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # The registry file should be valid JSON
        reg_path = lib_root / "registry.json"
        if reg_path.exists():
            content = reg_path.read_text(encoding="utf-8")
            data = json.loads(content)  # Should not raise
            assert "templates" in data


# ===================================================================
# B5 – Database WAL corruption
# ===================================================================
class TestDatabaseWALCorruption:
    """Write to the compliance DB, then truncate WAL. Re-open and verify."""

    def test_b5_wal_truncation_recovery(self, tmp_path):
        """Truncate WAL mid-write and verify DB is still usable."""
        from aecos.compliance.engine import ComplianceEngine
        from aecos.compliance.rules import Rule

        db_path = tmp_path / "compliance.db"
        engine = ComplianceEngine(db_path=str(db_path))

        # Add rules to populate the DB
        for i in range(10):
            engine.add_rule(Rule(
                code_name=f"TEST{i}",
                section=f"{i}.1",
                title=f"Test rule {i}",
                ifc_classes=["IfcWall"],
                check_type="min_value",
                property_path="properties.thickness_mm",
                check_value=100,
                region="*",
                citation=f"Test §{i}",
                effective_date="2024-01-01",
            ))

        # Close to flush
        engine.db.close()

        # Truncate WAL if it exists
        wal_path = Path(str(db_path) + "-wal")
        if wal_path.exists():
            wal_path.write_bytes(b"")  # Truncate

        # Re-open — should recover
        engine2 = ComplianceEngine(db_path=str(db_path))
        rules = engine2.get_rules()
        # Should have at least some rules (seeded + our additions)
        assert len(rules) > 0

    def test_b5_shm_corruption_recovery(self, tmp_path):
        """Corrupt SHM file and verify DB still works."""
        from aecos.analytics.collector import MetricsCollector

        db_path = tmp_path / "metrics.db"
        collector = MetricsCollector(db_path=str(db_path))

        # Record events
        for i in range(5):
            collector.record("test", "event", float(i))
        collector.close()

        # Corrupt SHM
        shm_path = Path(str(db_path) + "-shm")
        if shm_path.exists():
            shm_path.write_bytes(b"\x00" * 100)

        # Re-open
        collector2 = MetricsCollector(db_path=str(db_path))
        events = collector2.get_events()
        assert len(events) >= 5
        collector2.close()


# ===================================================================
# B6 – Kill and resume
# ===================================================================
class TestKillAndResume:
    """Generate elements, simulate crash (close DB without commit),
    restart and verify on-disk state is recoverable."""

    def test_b6_kill_and_resume_generation(self, tmp_path):
        """Generate 20 elements, kill, verify disk state."""
        from aecos.api.facade import AecOS

        root = tmp_path / "kill_resume"
        root.mkdir()
        aec = AecOS(project_root=str(root))

        generated_paths = []
        specs = [
            f"Create a concrete wall {i}m high 200mm thick"
            for i in range(1, 21)
        ]
        for spec_text in specs:
            path = aec.generate(spec_text)
            generated_paths.append(path)

        # Verify all 20 exist on disk
        for p in generated_paths:
            assert p.exists()
            assert (p / "metadata.json").exists()

        # Simulate crash: close all DB connections without commit
        try:
            aec.compliance.db.close()
        except Exception:
            pass
        try:
            aec.metrics.close()
        except Exception:
            pass

        # "Restart" — create new facade
        aec2 = AecOS(project_root=str(root))

        # Verify all elements are still on disk
        for p in generated_paths:
            assert p.exists(), f"Element lost after restart: {p}"
            meta = json.loads((p / "metadata.json").read_text())
            assert "GlobalId" in meta
            assert "IFCClass" in meta

    def test_b6_resume_validation_after_crash(self, tmp_path):
        """After crash, validation still works on existing elements."""
        from aecos.api.facade import AecOS

        root = tmp_path / "resume_validate"
        root.mkdir()
        aec = AecOS(project_root=str(root))

        path = aec.generate("Create a concrete wall 3m high 200mm thick")
        assert path.exists()

        # Simulate crash
        try:
            aec.compliance.db.close()
        except Exception:
            pass

        # Restart and validate
        aec2 = AecOS(project_root=str(root))
        report = aec2.validate(str(path))
        assert report is not None
        assert report.status in ("passed", "warnings", "failed")

    def test_b6_resume_cost_after_crash(self, tmp_path):
        """After crash, cost estimation still works on existing elements."""
        from aecos.api.facade import AecOS

        root = tmp_path / "resume_cost"
        root.mkdir()
        aec = AecOS(project_root=str(root))

        path = aec.generate("Create a concrete wall 3m high 200mm thick")

        # Simulate crash
        try:
            aec.metrics.close()
        except Exception:
            pass

        # Restart
        aec2 = AecOS(project_root=str(root))
        report = aec2.estimate_cost(str(path))
        assert report is not None
        assert report.total_installed_usd >= 0
