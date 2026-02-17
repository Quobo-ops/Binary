"""Tests for the Python API Wrapper (Item 05).

Covers the AecOS facade CRUD, search, project init, and the
extract+commit flow.  All tests use temporary directories with real
git repos.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from aecos.api.facade import AecOS
from aecos.api.elements import (
    create_element,
    delete_element,
    get_element,
    list_elements,
    update_element,
)
from aecos.api.projects import init_project
from aecos.api.search import SearchResults, unified_search
from aecos.models.element import Element
from aecos.templates.tagging import TemplateTags
from aecos.vcs.repo import RepoManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_git_user(path: Path) -> None:
    """Set git user.name, user.email, and disable GPG signing in a temp repo."""
    subprocess.run(["git", "config", "user.email", "test@aecos.dev"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "AEC OS Test"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, capture_output=True)


def _init_project(tmp_path: Path, name: str = "TestProject") -> Path:
    """Initialise an AEC OS project for testing."""
    root = tmp_path / "project"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, capture_output=True)
    _configure_git_user(root)

    # Use init_project to set up structure
    init_project(root, name)
    return root


def _make_element_folder(root: Path, global_id: str = "ABC123", **overrides: Any) -> Path:
    """Create a minimal element folder matching Item 01 output format."""
    elem_dir = root / "elements"
    elem_dir.mkdir(parents=True, exist_ok=True)
    folder = elem_dir / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)

    metadata = {
        "GlobalId": global_id,
        "Name": overrides.get("name", "TestWall"),
        "IFCClass": overrides.get("ifc_class", "IfcWall"),
        "ObjectType": overrides.get("object_type", "Standard Wall"),
        "Tag": None,
        "Psets": {"Pset_WallCommon.IsExternal": True, "Pset_WallCommon.FireRating": "2HR"},
    }
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2))

    props_dir = folder / "properties"
    props_dir.mkdir(exist_ok=True)
    (props_dir / "psets.json").write_text(json.dumps(
        {"Pset_WallCommon": {"IsExternal": True, "FireRating": "2HR"}}, indent=2
    ))

    mat_dir = folder / "materials"
    mat_dir.mkdir(exist_ok=True)
    (mat_dir / "materials.json").write_text(json.dumps(
        [{"name": "Concrete", "thickness": 200.0, "category": None, "fraction": None}], indent=2
    ))

    geo_dir = folder / "geometry"
    geo_dir.mkdir(exist_ok=True)
    (geo_dir / "shape.json").write_text(json.dumps({
        "bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0, "max_x": 6, "max_y": 0.25, "max_z": 3},
        "volume": 4.5,
        "centroid": [3.0, 0.125, 1.5],
    }, indent=2))

    rel_dir = folder / "relationships"
    rel_dir.mkdir(exist_ok=True)
    (rel_dir / "spatial.json").write_text(json.dumps({
        "site_name": "TestSite", "building_name": "TestBuilding", "storey_name": "Level 1",
    }, indent=2))

    return folder


# ---------------------------------------------------------------------------
# Element CRUD tests (module-level functions)
# ---------------------------------------------------------------------------


class TestElementCRUD:
    @pytest.fixture()
    def project(self, tmp_path: Path) -> Path:
        return _init_project(tmp_path)

    def test_create_element(self, project: Path):
        elem = create_element(
            project,
            "IfcWall",
            name="NewWall",
            properties={"Pset_WallCommon": {"IsExternal": True}},
            materials=[{"name": "Concrete", "thickness": 200.0}],
        )
        assert isinstance(elem, Element)
        assert elem.ifc_class == "IfcWall"
        assert elem.name == "NewWall"
        assert len(elem.materials) == 1

        # Verify folder was created
        folder = project / "elements" / f"element_{elem.global_id}"
        assert folder.is_dir()
        assert (folder / "metadata.json").is_file()
        assert (folder / "properties" / "psets.json").is_file()
        assert (folder / "materials" / "materials.json").is_file()
        assert (folder / "README.md").is_file()

    def test_get_element(self, project: Path):
        elem = create_element(project, "IfcDoor", name="TestDoor")
        loaded = get_element(project, elem.global_id)
        assert loaded is not None
        assert loaded.global_id == elem.global_id
        assert loaded.ifc_class == "IfcDoor"
        assert loaded.name == "TestDoor"

    def test_get_element_missing(self, project: Path):
        assert get_element(project, "NONEXISTENT") is None

    def test_update_element(self, project: Path):
        elem = create_element(project, "IfcWall", name="OriginalName")
        updated = update_element(project, elem.global_id, {"name": "NewName"})
        assert updated.name == "NewName"

    def test_update_element_properties(self, project: Path):
        elem = create_element(
            project, "IfcWall",
            properties={"Pset_WallCommon": {"IsExternal": True}},
        )
        updated = update_element(
            project, elem.global_id,
            {"properties": {"Pset_WallCommon": {"FireRating": "2HR"}}},
        )
        assert "Pset_WallCommon" in updated.psets
        assert updated.psets["Pset_WallCommon"]["FireRating"] == "2HR"
        assert updated.psets["Pset_WallCommon"]["IsExternal"] is True

    def test_update_element_missing_raises(self, project: Path):
        with pytest.raises(FileNotFoundError):
            update_element(project, "MISSING", {"name": "x"})

    def test_delete_element(self, project: Path):
        elem = create_element(project, "IfcSlab", name="TestSlab")
        assert delete_element(project, elem.global_id) is True
        assert get_element(project, elem.global_id) is None

    def test_delete_element_missing(self, project: Path):
        assert delete_element(project, "MISSING") is False

    def test_list_elements(self, project: Path):
        create_element(project, "IfcWall", name="Wall1")
        create_element(project, "IfcDoor", name="Door1")
        create_element(project, "IfcWall", name="Wall2")

        all_elems = list_elements(project)
        assert len(all_elems) == 3

    def test_list_elements_filter_ifc_class(self, project: Path):
        create_element(project, "IfcWall", name="Wall1")
        create_element(project, "IfcDoor", name="Door1")

        walls = list_elements(project, {"ifc_class": "IfcWall"})
        assert len(walls) == 1
        assert walls[0].ifc_class == "IfcWall"

    def test_list_elements_filter_material(self, project: Path):
        create_element(
            project, "IfcWall", name="ConcreteWall",
            materials=[{"name": "Concrete", "thickness": 200.0}],
        )
        create_element(project, "IfcDoor", name="Door1")

        results = list_elements(project, {"material": "Concrete"})
        assert len(results) == 1
        assert results[0].name == "ConcreteWall"


# ---------------------------------------------------------------------------
# AecOS Facade tests
# ---------------------------------------------------------------------------


class TestAecOSFacade:
    @pytest.fixture()
    def aecos(self, tmp_path: Path) -> AecOS:
        """Create an AecOS instance with a fresh git repo."""
        root = tmp_path / "project"
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        _configure_git_user(root)
        # Initial commit so the repo is valid
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)
        return AecOS(root, auto_commit=True)

    def test_init_auto_detects_repo(self, aecos: AecOS):
        assert aecos.repo.is_repo()

    def test_create_element_through_facade(self, aecos: AecOS):
        elem = aecos.create_element("IfcWall", name="FacadeWall")
        assert isinstance(elem, Element)
        assert elem.ifc_class == "IfcWall"

    def test_create_element_auto_commits(self, aecos: AecOS):
        aecos.create_element("IfcWall", name="AutoCommitWall")
        assert aecos.is_clean()

    def test_get_element_through_facade(self, aecos: AecOS):
        elem = aecos.create_element("IfcDoor", name="FacadeDoor")
        loaded = aecos.get_element(elem.global_id)
        assert loaded is not None
        assert loaded.name == "FacadeDoor"

    def test_update_element_through_facade(self, aecos: AecOS):
        elem = aecos.create_element("IfcWall", name="Original")
        updated = aecos.update_element(elem.global_id, {"name": "Updated"})
        assert updated.name == "Updated"

    def test_update_element_auto_commits(self, aecos: AecOS):
        elem = aecos.create_element("IfcWall", name="WillUpdate")
        aecos.update_element(elem.global_id, {"name": "Updated"})
        assert aecos.is_clean()

    def test_delete_element_through_facade(self, aecos: AecOS):
        elem = aecos.create_element("IfcSlab", name="ToDelete")
        assert aecos.delete_element(elem.global_id) is True
        assert aecos.get_element(elem.global_id) is None

    def test_delete_element_auto_commits(self, aecos: AecOS):
        elem = aecos.create_element("IfcWall", name="WillDelete")
        aecos.delete_element(elem.global_id)
        assert aecos.is_clean()

    def test_list_elements_through_facade(self, aecos: AecOS):
        aecos.create_element("IfcWall", name="W1")
        aecos.create_element("IfcDoor", name="D1")
        elems = aecos.list_elements()
        assert len(elems) == 2

    def test_list_elements_with_filter(self, aecos: AecOS):
        aecos.create_element("IfcWall", name="W1")
        aecos.create_element("IfcDoor", name="D1")
        walls = aecos.list_elements({"ifc_class": "IfcWall"})
        assert len(walls) == 1

    def test_search_elements_and_templates(self, aecos: AecOS):
        aecos.create_element("IfcWall", name="SearchWall")
        results = aecos.search(ifc_class="IfcWall")
        assert isinstance(results, SearchResults)
        assert len(results.elements) == 1

    def test_manual_commit(self, aecos: AecOS):
        (aecos.project_root / "notes.txt").write_text("manual change")
        sha = aecos.commit("chore: add notes")
        assert len(sha) >= 7
        assert aecos.is_clean()

    def test_status(self, aecos: AecOS):
        assert aecos.status().strip() == ""
        (aecos.project_root / "dirty.txt").write_text("x")
        assert "dirty.txt" in aecos.status()


# ---------------------------------------------------------------------------
# Project operations tests
# ---------------------------------------------------------------------------


class TestProjectOperations:
    def test_init_project(self, tmp_path: Path):
        root = init_project(tmp_path / "new_project", "My AEC Project")
        assert root.is_dir()
        assert (root / "elements").is_dir()
        assert (root / "templates").is_dir()
        assert (root / "aecos_project.json").is_file()
        assert (root / ".gitignore").is_file()
        assert (root / ".gitattributes").is_file()

        # Verify git repo
        repo = RepoManager(root)
        assert repo.is_repo()

        # Verify config
        config = json.loads((root / "aecos_project.json").read_text())
        assert config["name"] == "My AEC Project"

    def test_init_project_has_commits(self, tmp_path: Path):
        root = init_project(tmp_path / "proj", "Test")
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=root, capture_output=True, text=True,
        )
        assert result.returncode == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) >= 1


# ---------------------------------------------------------------------------
# Promote to template tests
# ---------------------------------------------------------------------------


class TestPromoteToTemplate:
    @pytest.fixture()
    def aecos(self, tmp_path: Path) -> AecOS:
        root = tmp_path / "project"
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        _configure_git_user(root)
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)
        return AecOS(root, auto_commit=True)

    def test_promote_through_facade(self, aecos: AecOS):
        elem = aecos.create_element(
            "IfcWall", name="PromoteMe",
            materials=[{"name": "Concrete", "thickness": 200.0}],
        )
        dest = aecos.promote_to_template(
            elem.global_id,
            tags={"ifc_class": "IfcWall", "material": ["Concrete"]},
            description="Promoted wall",
        )
        assert dest.is_dir()
        assert (dest / "template_manifest.json").is_file()

    def test_promote_auto_commits(self, aecos: AecOS):
        elem = aecos.create_element("IfcWall", name="AutoPromote")
        aecos.promote_to_template(elem.global_id)
        assert aecos.is_clean()

    def test_promote_creates_searchable_template(self, aecos: AecOS):
        elem = aecos.create_element("IfcWall", name="SearchableWall")
        aecos.promote_to_template(
            elem.global_id,
            tags=TemplateTags(ifc_class="IfcWall", material=["Concrete"]),
        )
        results = aecos.search_templates({"ifc_class": "IfcWall"})
        assert len(results) == 1

    def test_bulk_promote(self, aecos: AecOS):
        e1 = aecos.create_element("IfcWall", name="BulkW1")
        e2 = aecos.create_element("IfcDoor", name="BulkD1")
        promoted = aecos.bulk_promote([e1.global_id, e2.global_id])
        assert len(promoted) == 2
        assert aecos.is_clean()


# ---------------------------------------------------------------------------
# Full round-trip tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_full_lifecycle(self, tmp_path: Path):
        """Full round-trip: init -> create -> commit -> search -> promote -> retrieve."""
        root = tmp_path / "lifecycle"
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        _configure_git_user(root)
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

        os = AecOS(root)

        # Create elements
        wall = os.create_element(
            "IfcWall", name="LifecycleWall",
            properties={"Pset_WallCommon": {"IsExternal": True, "FireRating": "2HR"}},
            materials=[{"name": "Concrete", "thickness": 200.0}],
        )
        door = os.create_element("IfcDoor", name="LifecycleDoor")

        # Verify search
        results = os.search(ifc_class="IfcWall")
        assert len(results.elements) == 1
        assert results.elements[0].name == "LifecycleWall"

        # Update
        os.update_element(wall.global_id, {"name": "RenamedWall"})
        updated = os.get_element(wall.global_id)
        assert updated is not None
        assert updated.name == "RenamedWall"

        # Promote to template
        dest = os.promote_to_template(
            wall.global_id,
            tags={"ifc_class": "IfcWall", "material": ["Concrete"]},
            description="A lifecycle wall",
        )
        assert dest.is_dir()

        # Search templates
        tmpl_results = os.search_templates({"ifc_class": "IfcWall"})
        assert len(tmpl_results) == 1

        # Delete the original element
        os.delete_element(door.global_id)
        assert os.get_element(door.global_id) is None

        # Everything committed
        assert os.is_clean()

    def test_every_mutating_call_produces_commit(self, tmp_path: Path):
        """Verify that every mutating API call results in a git commit."""
        root = tmp_path / "commitcheck"
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        _configure_git_user(root)
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

        os = AecOS(root)

        def _count_commits() -> int:
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=root, capture_output=True, text=True,
            )
            return int(result.stdout.strip())

        initial = _count_commits()

        # create_element -> +1 commit
        elem = os.create_element("IfcWall", name="CommitTest")
        assert _count_commits() == initial + 1

        # update_element -> +1 commit
        os.update_element(elem.global_id, {"name": "Updated"})
        assert _count_commits() == initial + 2

        # promote_to_template -> +1 commit
        os.promote_to_template(elem.global_id)
        assert _count_commits() == initial + 3

        # delete_element -> +1 commit
        os.delete_element(elem.global_id)
        assert _count_commits() == initial + 4

    def test_facade_without_auto_commit(self, tmp_path: Path):
        """Verify auto_commit=False skips git commits."""
        root = tmp_path / "nocommit"
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        _configure_git_user(root)
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

        os = AecOS(root, auto_commit=False)
        os.create_element("IfcWall", name="NoCommit")

        # Should have uncommitted changes
        assert not os.is_clean()


# ---------------------------------------------------------------------------
# Extract IFC tests (with mock)
# ---------------------------------------------------------------------------


class TestExtractIFC:
    def test_extract_ifc_with_mock(self, tmp_path: Path):
        """Test extract_ifc through facade using a mock IFC pipeline."""
        root = tmp_path / "extract_test"
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, capture_output=True)
        _configure_git_user(root)
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

        os = AecOS(root)

        # Mock the extraction pipeline to return synthetic elements
        mock_elements = [
            Element(global_id="MOCK01", ifc_class="IfcWall", name="MockWall"),
            Element(global_id="MOCK02", ifc_class="IfcDoor", name="MockDoor"),
        ]

        def mock_extract(ifc_path, output_dir):
            for elem in mock_elements:
                folder = Path(output_dir) / f"element_{elem.global_id}"
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "metadata.json").write_text(
                    json.dumps({
                        "GlobalId": elem.global_id,
                        "Name": elem.name,
                        "IFCClass": elem.ifc_class,
                    }, indent=2)
                )
            return mock_elements

        with patch("aecos.extraction.ifc_to_element_folders", side_effect=mock_extract):
            elements = os.extract_ifc("fake.ifc")

        assert len(elements) == 2
        assert elements[0].ifc_class == "IfcWall"
        assert os.is_clean()  # auto-committed
