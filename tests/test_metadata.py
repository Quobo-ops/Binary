"""Tests for the Markdown Metadata Layer (Item 03).

Covers generation from synthetic element folders, idempotency, content
validation for all four .md files, and template-aware generation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aecos.metadata.generator import generate_metadata


# ---------------------------------------------------------------------------
# Fixtures: synthetic element folders
# ---------------------------------------------------------------------------


def _make_element_folder(root: Path, global_id: str = "META01") -> Path:
    """Create a synthetic element folder matching Item 01 output."""
    folder = root / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)

    metadata = {
        "GlobalId": global_id,
        "Name": "ExteriorWall",
        "IFCClass": "IfcWall",
        "ObjectType": "Standard Wall",
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
        {"name": "Insulation", "thickness": 50.0, "category": "Thermal", "fraction": None},
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
        "building_name": "MainBuilding",
        "building_id": "BLDG01",
        "storey_name": "Level 1",
        "storey_id": "STR01",
    }
    (rel_dir / "spatial.json").write_text(json.dumps(spatial, indent=2))

    return folder


def _make_template_folder(root: Path, global_id: str = "TMPL01") -> Path:
    """Create a synthetic template folder (element + manifest)."""
    folder = _make_element_folder(root, global_id)

    manifest = {
        "template_id": global_id,
        "tags": {
            "ifc_class": "IfcWall",
            "material": ["Concrete"],
            "region": ["Louisiana"],
            "compliance_codes": ["IBC-2021"],
            "custom": ["fire-rated"],
        },
        "version": "1.0.0",
        "author": "tester",
        "description": "Fire-rated exterior concrete wall for Louisiana projects",
    }
    (folder / "template_manifest.json").write_text(json.dumps(manifest, indent=2))

    return folder


@pytest.fixture()
def element_folder(tmp_path: Path) -> Path:
    return _make_element_folder(tmp_path)


@pytest.fixture()
def template_folder(tmp_path: Path) -> Path:
    return _make_template_folder(tmp_path)


# ---------------------------------------------------------------------------
# Basic generation tests
# ---------------------------------------------------------------------------


class TestMetadataGeneration:
    def test_generates_four_files(self, element_folder: Path):
        paths = generate_metadata(element_folder)
        assert len(paths) == 6

        filenames = {p.name for p in paths}
        assert filenames == {"README.md", "COMPLIANCE.md", "COST.md", "USAGE.md", "VALIDATION.md", "SCHEDULE.md"}

    def test_all_files_exist(self, element_folder: Path):
        generate_metadata(element_folder)

        assert (element_folder / "README.md").is_file()
        assert (element_folder / "COMPLIANCE.md").is_file()
        assert (element_folder / "COST.md").is_file()
        assert (element_folder / "USAGE.md").is_file()

    def test_missing_folder_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            generate_metadata(tmp_path / "nonexistent")


# ---------------------------------------------------------------------------
# README.md content tests
# ---------------------------------------------------------------------------


class TestReadmeContent:
    def test_contains_element_name(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert "ExteriorWall" in readme

    def test_contains_ifc_class(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert "IfcWall" in readme

    def test_contains_global_id(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert "META01" in readme

    def test_contains_properties(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert "Pset_WallCommon" in readme
        assert "FireRating" in readme
        assert "2HR" in readme

    def test_contains_materials(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert "Concrete" in readme
        assert "Insulation" in readme
        assert "200.0" in readme

    def test_contains_spatial_location(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert "TestSite" in readme
        assert "MainBuilding" in readme
        assert "Level 1" in readme

    def test_element_readme_no_template_prefix(self, element_folder: Path):
        generate_metadata(element_folder)
        readme = (element_folder / "README.md").read_text()
        assert readme.startswith("# ExteriorWall")

    def test_template_readme_has_template_prefix(self, template_folder: Path):
        generate_metadata(template_folder)
        readme = (template_folder / "README.md").read_text()
        assert "# Template:" in readme

    def test_template_readme_has_description(self, template_folder: Path):
        generate_metadata(template_folder)
        readme = (template_folder / "README.md").read_text()
        assert "Fire-rated exterior concrete wall" in readme

    def test_template_readme_has_tags(self, template_folder: Path):
        generate_metadata(template_folder)
        readme = (template_folder / "README.md").read_text()
        assert "Tags" in readme
        assert "Concrete" in readme
        assert "Louisiana" in readme


# ---------------------------------------------------------------------------
# COMPLIANCE.md content tests
# ---------------------------------------------------------------------------


class TestComplianceContent:
    def test_contains_element_name(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "COMPLIANCE.md").read_text()
        assert "ExteriorWall" in content

    def test_contains_pset_listing(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "COMPLIANCE.md").read_text()
        assert "Pset_WallCommon" in content
        assert "FireRating" in content

    def test_contains_awaiting_placeholder(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "COMPLIANCE.md").read_text()
        assert "Awaiting compliance engine" in content

    def test_template_compliance_has_codes(self, template_folder: Path):
        generate_metadata(template_folder)
        content = (template_folder / "COMPLIANCE.md").read_text()
        assert "IBC-2021" in content


# ---------------------------------------------------------------------------
# COST.md content tests
# ---------------------------------------------------------------------------


class TestCostContent:
    def test_contains_element_name(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "COST.md").read_text()
        assert "ExteriorWall" in content

    def test_contains_materials(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "COST.md").read_text()
        assert "Concrete" in content

    def test_contains_awaiting_placeholder(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "COST.md").read_text()
        assert "Awaiting cost data from Item 10" in content


# ---------------------------------------------------------------------------
# USAGE.md content tests
# ---------------------------------------------------------------------------


class TestUsageContent:
    def test_contains_element_name(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "USAGE.md").read_text()
        assert "ExteriorWall" in content

    def test_contains_ifc_class(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "USAGE.md").read_text()
        assert "IfcWall" in content

    def test_element_usage_has_promote_instructions(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "USAGE.md").read_text()
        assert "promote" in content.lower()

    def test_template_usage_has_insertion_instructions(self, template_folder: Path):
        generate_metadata(template_folder)
        content = (template_folder / "USAGE.md").read_text()
        assert "TemplateLibrary" in content
        assert "get_template" in content

    def test_template_usage_has_region(self, template_folder: Path):
        generate_metadata(template_folder)
        content = (template_folder / "USAGE.md").read_text()
        assert "Louisiana" in content

    def test_contains_spatial_context(self, element_folder: Path):
        generate_metadata(element_folder)
        content = (element_folder / "USAGE.md").read_text()
        assert "TestSite" in content


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_generate_twice_produces_identical_output(self, element_folder: Path):
        generate_metadata(element_folder)

        first = {}
        for name in ("README.md", "COMPLIANCE.md", "COST.md", "USAGE.md"):
            first[name] = (element_folder / name).read_text()

        # Run again
        generate_metadata(element_folder)

        for name in ("README.md", "COMPLIANCE.md", "COST.md", "USAGE.md"):
            assert (element_folder / name).read_text() == first[name], (
                f"{name} changed on second run"
            )

    def test_template_generate_twice_identical(self, template_folder: Path):
        generate_metadata(template_folder)

        first = {}
        for name in ("README.md", "COMPLIANCE.md", "COST.md", "USAGE.md"):
            first[name] = (template_folder / name).read_text()

        generate_metadata(template_folder)

        for name in ("README.md", "COMPLIANCE.md", "COST.md", "USAGE.md"):
            assert (template_folder / name).read_text() == first[name]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_psets_json(self, tmp_path: Path):
        """Generation works even if psets.json is missing."""
        folder = tmp_path / "element_EMPTY"
        folder.mkdir()
        (folder / "metadata.json").write_text(json.dumps({
            "GlobalId": "EMPTY",
            "Name": "Empty",
            "IFCClass": "IfcWall",
        }))
        paths = generate_metadata(folder)
        assert len(paths) == 6

    def test_empty_materials(self, tmp_path: Path):
        """Generation works with no materials."""
        folder = tmp_path / "element_NOMAT"
        folder.mkdir()
        (folder / "metadata.json").write_text(json.dumps({
            "GlobalId": "NOMAT",
            "Name": "NoMat",
            "IFCClass": "IfcSlab",
        }))
        mat_dir = folder / "materials"
        mat_dir.mkdir()
        (mat_dir / "materials.json").write_text("[]")

        paths = generate_metadata(folder)
        assert len(paths) == 6
        readme = (folder / "README.md").read_text()
        assert "NoMat" in readme
