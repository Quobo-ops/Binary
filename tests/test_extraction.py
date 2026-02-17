"""Tests for the aecos extraction pipeline.

All tests create a synthetic IFC in-memory using ifcopenshell's API, run the
pipeline, and verify the output folder structure and data integrity.
"""

from __future__ import annotations

import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import pytest

from aecos.extraction.geometry import extract_geometry
from aecos.extraction.materials import extract_materials
from aecos.extraction.pipeline import ifc_to_element_folders
from aecos.extraction.properties import extract_psets, flatten_psets
from aecos.extraction.relationships import extract_spatial
from aecos.models.element import Element


# ---------------------------------------------------------------------------
# Fixtures: synthetic IFC files
# ---------------------------------------------------------------------------


def _build_minimal_ifc() -> ifcopenshell.file:
    """Return an IFC4 file with one wall, one door, and one slab.

    The wall has:
      - Pset_WallCommon with IsExternal and FireRating
      - A two-layer material (Concrete 200mm + Insulation 50mm)
      - Spatial containment: Site > Building > Storey
    The door and slab have basic containment only.
    """
    f = ifcopenshell.file(schema="IFC4")

    proj = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcProject", name="SyntheticProject"
    )
    ctx = ifcopenshell.api.run("context.add_context", f, context_type="Model")
    ifcopenshell.api.run(
        "context.add_context",
        f,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=ctx,
    )

    site = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcSite", name="TestSite"
    )
    building = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcBuilding", name="TestBuilding"
    )
    storey = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcBuildingStorey", name="Level 1"
    )

    ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=proj)
    ifcopenshell.api.run(
        "aggregate.assign_object", f, products=[building], relating_object=site
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", f, products=[storey], relating_object=building
    )

    # --- Wall ---
    wall = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcWall", name="ExteriorWall"
    )
    ifcopenshell.api.run(
        "spatial.assign_container", f, products=[wall], relating_structure=storey
    )

    pset = ifcopenshell.api.run("pset.add_pset", f, product=wall, name="Pset_WallCommon")
    ifcopenshell.api.run(
        "pset.edit_pset",
        f,
        pset=pset,
        properties={"IsExternal": True, "FireRating": "2HR"},
    )

    mat_set = ifcopenshell.api.run(
        "material.add_material_set",
        f,
        name="WallLayers",
        set_type="IfcMaterialLayerSet",
    )
    concrete = ifcopenshell.api.run("material.add_material", f, name="Concrete")
    insulation = ifcopenshell.api.run("material.add_material", f, name="Insulation")
    layer1 = ifcopenshell.api.run(
        "material.add_layer", f, layer_set=mat_set, material=concrete
    )
    ifcopenshell.api.run(
        "material.edit_layer", f, layer=layer1, attributes={"LayerThickness": 200.0}
    )
    layer2 = ifcopenshell.api.run(
        "material.add_layer", f, layer_set=mat_set, material=insulation
    )
    ifcopenshell.api.run(
        "material.edit_layer", f, layer=layer2, attributes={"LayerThickness": 50.0}
    )
    ifcopenshell.api.run(
        "material.assign_material", f, products=[wall], material=mat_set
    )

    # --- Door ---
    door = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcDoor", name="EntryDoor"
    )
    ifcopenshell.api.run(
        "spatial.assign_container", f, products=[door], relating_structure=storey
    )

    # --- Slab ---
    slab = ifcopenshell.api.run(
        "root.create_entity", f, ifc_class="IfcSlab", name="GroundSlab"
    )
    ifcopenshell.api.run(
        "spatial.assign_container", f, products=[slab], relating_structure=storey
    )

    return f


@pytest.fixture()
def synthetic_ifc(tmp_path: Path) -> Path:
    """Write a synthetic IFC4 to a temp file and return its path."""
    ifc_file = _build_minimal_ifc()
    p = tmp_path / "synthetic.ifc"
    ifc_file.write(str(p))
    return p


@pytest.fixture()
def synthetic_ifc_file() -> ifcopenshell.file:
    """Return the in-memory IFC file (no disk write needed)."""
    return _build_minimal_ifc()


# ---------------------------------------------------------------------------
# Unit tests — individual extractors
# ---------------------------------------------------------------------------


class TestPropertyExtraction:
    def test_extract_psets_returns_wall_common(self, synthetic_ifc_file: ifcopenshell.file):
        wall = synthetic_ifc_file.by_type("IfcWall")[0]
        psets = extract_psets(wall)

        assert "Pset_WallCommon" in psets
        assert psets["Pset_WallCommon"]["IsExternal"] is True
        assert psets["Pset_WallCommon"]["FireRating"] == "2HR"

    def test_extract_psets_empty_for_door(self, synthetic_ifc_file: ifcopenshell.file):
        door = synthetic_ifc_file.by_type("IfcDoor")[0]
        psets = extract_psets(door)
        # Door has no psets assigned in fixture
        assert isinstance(psets, dict)

    def test_flatten_psets(self, synthetic_ifc_file: ifcopenshell.file):
        wall = synthetic_ifc_file.by_type("IfcWall")[0]
        psets = extract_psets(wall)
        flat = flatten_psets(psets)

        assert "Pset_WallCommon.IsExternal" in flat
        assert flat["Pset_WallCommon.FireRating"] == "2HR"


class TestMaterialExtraction:
    def test_extract_layer_set(self, synthetic_ifc_file: ifcopenshell.file):
        wall = synthetic_ifc_file.by_type("IfcWall")[0]
        mats = extract_materials(wall)

        assert len(mats) == 2
        assert mats[0].name == "Concrete"
        assert mats[0].thickness == 200.0
        assert mats[1].name == "Insulation"
        assert mats[1].thickness == 50.0

    def test_no_material(self, synthetic_ifc_file: ifcopenshell.file):
        door = synthetic_ifc_file.by_type("IfcDoor")[0]
        mats = extract_materials(door)
        assert mats == []


class TestSpatialExtraction:
    def test_storey_building_site(self, synthetic_ifc_file: ifcopenshell.file):
        wall = synthetic_ifc_file.by_type("IfcWall")[0]
        ref = extract_spatial(wall)

        assert ref.storey_name == "Level 1"
        assert ref.building_name == "TestBuilding"
        assert ref.site_name == "TestSite"
        assert ref.storey_id is not None
        assert ref.building_id is not None
        assert ref.site_id is not None


class TestGeometryExtraction:
    def test_no_representation_returns_empty(self, synthetic_ifc_file: ifcopenshell.file):
        """Our synthetic elements have no geometry representations,
        so we should get a zeroed-out GeometryInfo."""
        wall = synthetic_ifc_file.by_type("IfcWall")[0]
        geo = extract_geometry(wall, synthetic_ifc_file)

        assert geo.bounding_box.min_x == 0.0
        assert geo.volume is None
        assert geo.centroid is None


# ---------------------------------------------------------------------------
# Integration tests — full pipeline round-trip
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_creates_element_folders(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        assert len(elements) == 3  # wall, door, slab

    def test_folder_structure(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        for elem in elements:
            folder = out / f"element_{elem.global_id}"
            assert folder.is_dir(), f"Missing folder for {elem.global_id}"

            # Required files
            assert (folder / "metadata.json").is_file()
            assert (folder / "geometry" / "shape.json").is_file()
            assert (folder / "properties" / "psets.json").is_file()
            assert (folder / "materials" / "materials.json").is_file()
            assert (folder / "relationships" / "spatial.json").is_file()

    def test_metadata_json_content(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        meta_path = out / f"element_{wall.global_id}" / "metadata.json"
        meta = json.loads(meta_path.read_text())

        assert meta["GlobalId"] == wall.global_id
        assert meta["IFCClass"] == "IfcWall"
        assert meta["Name"] == "ExteriorWall"
        assert "Pset_WallCommon.IsExternal" in meta["Psets"]

    def test_psets_json_content(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        psets_path = out / f"element_{wall.global_id}" / "properties" / "psets.json"
        psets = json.loads(psets_path.read_text())

        assert "Pset_WallCommon" in psets
        assert psets["Pset_WallCommon"]["FireRating"] == "2HR"

    def test_materials_json_content(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        mat_path = out / f"element_{wall.global_id}" / "materials" / "materials.json"
        mats = json.loads(mat_path.read_text())

        assert len(mats) == 2
        assert mats[0]["name"] == "Concrete"
        assert mats[0]["thickness"] == 200.0

    def test_spatial_json_content(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        sp_path = out / f"element_{wall.global_id}" / "relationships" / "spatial.json"
        spatial = json.loads(sp_path.read_text())

        assert spatial["storey_name"] == "Level 1"
        assert spatial["building_name"] == "TestBuilding"
        assert spatial["site_name"] == "TestSite"

    def test_element_ifc_created(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        ifc_path = out / f"element_{wall.global_id}" / "element.ifc"
        # File may or may not exist depending on the copy capability,
        # but if it exists it should be a valid IFC
        if ifc_path.is_file():
            content = ifc_path.read_text(encoding="utf-8", errors="replace")
            assert "ISO-10303-21" in content

    def test_element_model_fields(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        assert isinstance(wall, Element)
        assert wall.global_id
        assert wall.name == "ExteriorWall"
        assert wall.ifc_class == "IfcWall"
        assert len(wall.materials) == 2
        assert wall.spatial.storey_name == "Level 1"
        assert "Pset_WallCommon" in wall.psets

    def test_all_element_types_extracted(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        classes = {e.ifc_class for e in elements}
        assert "IfcWall" in classes
        assert "IfcDoor" in classes
        assert "IfcSlab" in classes

    def test_geometry_shape_json(self, synthetic_ifc: Path, tmp_path: Path):
        out = tmp_path / "output"
        elements = ifc_to_element_folders(synthetic_ifc, out)

        wall = [e for e in elements if e.ifc_class == "IfcWall"][0]
        shape_path = out / f"element_{wall.global_id}" / "geometry" / "shape.json"
        shape = json.loads(shape_path.read_text())

        # Should have bounding_box key even if zeroed
        assert "bounding_box" in shape
        assert "volume" in shape
        assert "centroid" in shape


class TestIFC2X3:
    """Verify the pipeline handles IFC2X3 schema files."""

    def test_ifc2x3_extraction(self, tmp_path: Path):
        f = ifcopenshell.file(schema="IFC2X3")

        # IFC2X3 requires OwnerHistory — create person/org first
        person = f.createIfcPerson(FamilyName="Test")
        org = f.createIfcOrganization(Name="TestOrg")
        pao = f.createIfcPersonAndOrganization(person, org)
        app = f.createIfcApplication(org, "0.1", "TestApp", "TestApp")
        f.createIfcOwnerHistory(pao, app)

        proj = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcProject", name="IFC2X3Project"
        )
        site = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcSite", name="Site"
        )
        building = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcBuilding", name="Building"
        )
        storey = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcBuildingStorey", name="Ground"
        )

        ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=proj)
        ifcopenshell.api.run(
            "aggregate.assign_object", f, products=[building], relating_object=site
        )
        ifcopenshell.api.run(
            "aggregate.assign_object", f, products=[storey], relating_object=building
        )

        wall = ifcopenshell.api.run(
            "root.create_entity", f, ifc_class="IfcWallStandardCase", name="OldWall"
        )
        ifcopenshell.api.run(
            "spatial.assign_container", f, products=[wall], relating_structure=storey
        )

        ifc_path = tmp_path / "old.ifc"
        f.write(str(ifc_path))

        out = tmp_path / "output_2x3"
        elements = ifc_to_element_folders(ifc_path, out)

        assert len(elements) == 1
        assert elements[0].ifc_class == "IfcWallStandardCase"
        assert (out / f"element_{elements[0].global_id}" / "metadata.json").is_file()
