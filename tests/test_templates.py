"""Tests for the Template Library (Item 02).

Covers CRUD operations, search, promote, and registry consistency.
Fixtures create synthetic element folders matching Item 01's output format.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aecos.templates.library import MANIFEST_FILENAME, TemplateLibrary
from aecos.templates.registry import TemplateRegistry
from aecos.templates.tagging import TemplateTags


# ---------------------------------------------------------------------------
# Fixtures: synthetic element folders
# ---------------------------------------------------------------------------


def _make_element_folder(root: Path, global_id: str = "ABC123", **overrides: object) -> Path:
    """Create a minimal element folder matching Item 01 output format."""
    folder = root / f"element_{global_id}"
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
    props_dir.mkdir()
    psets = {
        "Pset_WallCommon": {"IsExternal": True, "FireRating": "2HR"},
    }
    (props_dir / "psets.json").write_text(json.dumps(psets, indent=2))

    mat_dir = folder / "materials"
    mat_dir.mkdir()
    materials = [
        {"name": "Concrete", "thickness": 200.0, "category": None, "fraction": None},
        {"name": "Insulation", "thickness": 50.0, "category": None, "fraction": None},
    ]
    (mat_dir / "materials.json").write_text(json.dumps(materials, indent=2))

    geo_dir = folder / "geometry"
    geo_dir.mkdir()
    (geo_dir / "shape.json").write_text(json.dumps({
        "bounding_box": {"min_x": 0, "min_y": 0, "min_z": 0, "max_x": 6, "max_y": 0.25, "max_z": 3},
        "volume": 4.5,
        "centroid": [3.0, 0.125, 1.5],
    }, indent=2))

    rel_dir = folder / "relationships"
    rel_dir.mkdir()
    spatial = {
        "site_name": "TestSite",
        "site_id": "SITE01",
        "building_name": "TestBuilding",
        "building_id": "BLDG01",
        "storey_name": "Level 1",
        "storey_id": "STR01",
    }
    (rel_dir / "spatial.json").write_text(json.dumps(spatial, indent=2))

    return folder


@pytest.fixture()
def element_folder(tmp_path: Path) -> Path:
    return _make_element_folder(tmp_path)


@pytest.fixture()
def library(tmp_path: Path) -> TemplateLibrary:
    lib_root = tmp_path / "template_library"
    return TemplateLibrary(lib_root)


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestTemplateLibraryCRUD:
    def test_add_template(self, library: TemplateLibrary, element_folder: Path):
        dest = library.add_template(
            "wall_01",
            element_folder,
            tags=TemplateTags(ifc_class="IfcWall", material=["Concrete"]),
            description="Exterior concrete wall",
        )
        assert dest.is_dir()
        assert (dest / "metadata.json").is_file()
        assert (dest / MANIFEST_FILENAME).is_file()
        assert len(library.registry) == 1

    def test_get_template(self, library: TemplateLibrary, element_folder: Path):
        library.add_template("wall_01", element_folder)
        folder = library.get_template("wall_01")
        assert folder is not None
        assert folder.is_dir()

    def test_get_template_missing(self, library: TemplateLibrary):
        assert library.get_template("nonexistent") is None

    def test_get_manifest(self, library: TemplateLibrary, element_folder: Path):
        library.add_template(
            "wall_01",
            element_folder,
            tags=TemplateTags(ifc_class="IfcWall"),
            version="2.0.0",
            author="tester",
            description="A wall",
        )
        manifest = library.get_manifest("wall_01")
        assert manifest is not None
        assert manifest["template_id"] == "wall_01"
        assert manifest["version"] == "2.0.0"
        assert manifest["author"] == "tester"
        assert manifest["tags"]["ifc_class"] == "IfcWall"

    def test_update_template(self, library: TemplateLibrary, element_folder: Path):
        library.add_template("wall_01", element_folder, description="v1")
        library.update_template("wall_01", description="v2", version="2.0.0")

        manifest = library.get_manifest("wall_01")
        assert manifest is not None
        assert manifest["description"] == "v2"
        assert manifest["version"] == "2.0.0"

    def test_update_template_missing_raises(self, library: TemplateLibrary):
        with pytest.raises(KeyError):
            library.update_template("nonexistent", description="nope")

    def test_remove_template(self, library: TemplateLibrary, element_folder: Path):
        library.add_template("wall_01", element_folder)
        assert library.remove_template("wall_01") is True
        assert library.get_template("wall_01") is None
        assert len(library.registry) == 0

    def test_remove_template_missing(self, library: TemplateLibrary):
        assert library.remove_template("nonexistent") is False

    def test_add_overwrites_existing(self, library: TemplateLibrary, element_folder: Path):
        library.add_template("wall_01", element_folder, description="first")
        library.add_template("wall_01", element_folder, description="second")
        manifest = library.get_manifest("wall_01")
        assert manifest is not None
        assert manifest["description"] == "second"
        assert len(library.registry) == 1


# ---------------------------------------------------------------------------
# Registry persistence tests
# ---------------------------------------------------------------------------


class TestRegistryPersistence:
    def test_registry_survives_reload(self, library: TemplateLibrary, element_folder: Path):
        library.add_template(
            "wall_01",
            element_folder,
            tags=TemplateTags(ifc_class="IfcWall"),
        )
        # Reload from disk
        lib2 = TemplateLibrary(library.root)
        assert len(lib2.registry) == 1
        entry = lib2.registry.get("wall_01")
        assert entry is not None
        assert entry.tags.ifc_class == "IfcWall"

    def test_registry_json_structure(self, library: TemplateLibrary, element_folder: Path):
        library.add_template("wall_01", element_folder)
        reg_path = library.root / "registry.json"
        assert reg_path.is_file()

        data = json.loads(reg_path.read_text())
        assert "version" in data
        assert "templates" in data
        assert len(data["templates"]) == 1
        assert data["templates"][0]["template_id"] == "wall_01"


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------


class TestTemplateSearch:
    def _populate(self, library: TemplateLibrary, tmp_path: Path) -> None:
        """Add several templates with diverse tags."""
        wall_folder = _make_element_folder(tmp_path, "W1", name="ConcreteWall", ifc_class="IfcWall")
        library.add_template(
            "W1", wall_folder,
            tags=TemplateTags(
                ifc_class="IfcWall",
                material=["Concrete"],
                region=["Louisiana"],
                compliance_codes=["IBC-2021"],
            ),
            description="Exterior concrete wall for Louisiana projects",
        )

        door_folder = _make_element_folder(tmp_path, "D1", name="FireDoor", ifc_class="IfcDoor")
        library.add_template(
            "D1", door_folder,
            tags=TemplateTags(
                ifc_class="IfcDoor",
                material=["Steel"],
                region=["Louisiana", "Texas"],
                compliance_codes=["IBC-2021", "NFPA-80"],
            ),
            description="Fire-rated steel door",
        )

        slab_folder = _make_element_folder(tmp_path, "S1", name="GroundSlab", ifc_class="IfcSlab")
        library.add_template(
            "S1", slab_folder,
            tags=TemplateTags(
                ifc_class="IfcSlab",
                material=["Concrete", "Rebar"],
                region=["California"],
                compliance_codes=["CBC-2022"],
            ),
            description="Ground floor concrete slab",
        )

    def test_search_by_ifc_class(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"ifc_class": "IfcWall"})
        assert len(results) == 1
        assert results[0].template_id == "W1"

    def test_search_by_material(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"material": "Concrete"})
        assert len(results) == 2  # wall + slab

    def test_search_by_region(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"region": "Louisiana"})
        assert len(results) == 2  # wall + door

    def test_search_by_compliance_code(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"compliance_codes": "NFPA-80"})
        assert len(results) == 1
        assert results[0].template_id == "D1"

    def test_search_by_keyword(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"keyword": "steel"})
        assert len(results) == 1
        assert results[0].template_id == "D1"

    def test_search_multiple_filters(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"material": "Concrete", "region": "Louisiana"})
        assert len(results) == 1
        assert results[0].template_id == "W1"

    def test_search_empty_results(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"ifc_class": "IfcBeam"})
        assert results == []

    def test_search_by_tags(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"tags": ["Concrete", "Louisiana"]})
        assert len(results) == 1
        assert results[0].template_id == "W1"

    def test_search_by_description(self, library: TemplateLibrary, tmp_path: Path):
        self._populate(library, tmp_path)
        results = library.search({"description": "fire-rated"})
        assert len(results) == 1
        assert results[0].template_id == "D1"


# ---------------------------------------------------------------------------
# Promote tests
# ---------------------------------------------------------------------------


class TestPromoteToTemplate:
    def test_promote_basic(self, library: TemplateLibrary, element_folder: Path):
        dest = library.promote_to_template(element_folder)
        assert dest.is_dir()
        assert (dest / MANIFEST_FILENAME).is_file()
        assert len(library.registry) == 1

    def test_promote_derives_id_from_metadata(self, library: TemplateLibrary, element_folder: Path):
        library.promote_to_template(element_folder)
        # The element fixture has GlobalId "ABC123"
        assert library.get_template("ABC123") is not None

    def test_promote_auto_populates_ifc_class(self, library: TemplateLibrary, element_folder: Path):
        library.promote_to_template(element_folder)
        manifest = library.get_manifest("ABC123")
        assert manifest is not None
        assert manifest["tags"]["ifc_class"] == "IfcWall"

    def test_promote_with_custom_tags(self, library: TemplateLibrary, element_folder: Path):
        library.promote_to_template(
            element_folder,
            tags=TemplateTags(
                ifc_class="IfcWall",
                material=["Concrete"],
                region=["Louisiana"],
            ),
            description="Promoted wall",
        )
        manifest = library.get_manifest("ABC123")
        assert manifest is not None
        assert "Concrete" in manifest["tags"]["material"]
        assert "Louisiana" in manifest["tags"]["region"]

    def test_promote_creates_valid_manifest(self, library: TemplateLibrary, element_folder: Path):
        library.promote_to_template(
            element_folder,
            tags={"ifc_class": "IfcWall", "material": ["Concrete"]},
            version="1.0.0",
            author="tester",
            description="Test wall template",
        )
        manifest = library.get_manifest("ABC123")
        assert manifest is not None
        assert manifest["template_id"] == "ABC123"
        assert manifest["version"] == "1.0.0"
        assert manifest["author"] == "tester"
        assert manifest["description"] == "Test wall template"
        assert manifest["tags"]["ifc_class"] == "IfcWall"
        assert manifest["tags"]["material"] == ["Concrete"]

    def test_promote_generates_markdown(self, library: TemplateLibrary, element_folder: Path):
        dest = library.promote_to_template(element_folder, description="A promoted wall")
        assert (dest / "README.md").is_file()
        assert (dest / "COMPLIANCE.md").is_file()
        assert (dest / "COST.md").is_file()
        assert (dest / "USAGE.md").is_file()

        readme = (dest / "README.md").read_text()
        assert "Template:" in readme

    def test_promote_missing_folder_raises(self, library: TemplateLibrary, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            library.promote_to_template(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# Tagging tests
# ---------------------------------------------------------------------------


class TestTemplateTags:
    def test_matches_ifc_class(self):
        tags = TemplateTags(ifc_class="IfcWall")
        assert tags.matches({"ifc_class": "IfcWall"})
        assert tags.matches({"ifc_class": "ifcwall"})  # case-insensitive
        assert not tags.matches({"ifc_class": "IfcDoor"})

    def test_matches_material(self):
        tags = TemplateTags(material=["Concrete", "Steel"])
        assert tags.matches({"material": "Concrete"})
        assert tags.matches({"material": ["Steel"]})
        assert not tags.matches({"material": "Wood"})

    def test_matches_region(self):
        tags = TemplateTags(region=["Louisiana", "Texas"])
        assert tags.matches({"region": "Louisiana"})
        assert not tags.matches({"region": "California"})

    def test_matches_empty_query(self):
        tags = TemplateTags(ifc_class="IfcWall")
        assert tags.matches({})  # no filters = matches everything

    def test_matches_multiple_filters(self):
        tags = TemplateTags(ifc_class="IfcWall", material=["Concrete"], region=["Louisiana"])
        assert tags.matches({"ifc_class": "IfcWall", "material": "Concrete"})
        assert not tags.matches({"ifc_class": "IfcWall", "material": "Steel"})
