"""Tests for Item 11 — Visualization Bridge."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aecos.visualization.bridge import ExportResult, VisualizationBridge
from aecos.visualization.exporters.base import Exporter
from aecos.visualization.exporters.gltf import GLTFExporter
from aecos.visualization.exporters.json3d import JSON3DExporter
from aecos.visualization.exporters.obj import OBJExporter
from aecos.visualization.exporters.speckle import SpeckleExporter
from aecos.visualization.report import render_visualization_report
from aecos.visualization.scene import (
    MATERIAL_COLORS,
    Camera,
    MeshData,
    Scene,
    _build_box,
    _build_cylinder,
    _get_material_color,
)
from aecos.visualization.viewer import generate_viewer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_element_folder(
    tmp_path: Path,
    ifc_class: str = "IfcWall",
    name: str = "Test Wall",
    global_id: str = "abc123",
    thickness_mm: float = 200.0,
    height_mm: float = 3000.0,
    length_mm: float = 5000.0,
    material: str = "Concrete",
) -> Path:
    """Create a minimal element folder for testing."""
    t = thickness_mm / 1000
    h = height_mm / 1000
    l = length_mm / 1000

    folder = tmp_path / f"element_{global_id}"
    folder.mkdir()

    # metadata.json
    (folder / "metadata.json").write_text(json.dumps({
        "GlobalId": global_id,
        "Name": name,
        "IFCClass": ifc_class,
        "ObjectType": None,
        "Tag": None,
    }), encoding="utf-8")

    # geometry/shape.json
    geo_dir = folder / "geometry"
    geo_dir.mkdir()
    (geo_dir / "shape.json").write_text(json.dumps({
        "bounding_box": {
            "min_x": 0.0, "min_y": 0.0, "min_z": 0.0,
            "max_x": l, "max_y": t, "max_z": h,
        },
        "volume": round(l * t * h, 6),
        "centroid": [l / 2, t / 2, h / 2],
    }), encoding="utf-8")

    # materials/materials.json
    mat_dir = folder / "materials"
    mat_dir.mkdir()
    (mat_dir / "materials.json").write_text(json.dumps([
        {"name": material, "thickness": thickness_mm, "category": "wall", "fraction": None},
    ]), encoding="utf-8")

    # relationships/spatial.json
    rel_dir = folder / "relationships"
    rel_dir.mkdir()
    (rel_dir / "spatial.json").write_text(json.dumps({
        "site_name": "Default Site",
        "building_name": "Building A",
        "storey_name": "Level 1",
    }), encoding="utf-8")

    # properties/psets.json
    props_dir = folder / "properties"
    props_dir.mkdir()
    (props_dir / "psets.json").write_text(json.dumps({
        "Dimensions": {
            "thickness_mm": thickness_mm,
            "height_mm": height_mm,
            "length_mm": length_mm,
        }
    }), encoding="utf-8")

    return folder


# ---------------------------------------------------------------------------
# Scene & Geometry tests
# ---------------------------------------------------------------------------


class TestScene:
    def test_scene_from_element_folder(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        assert scene.element_id == "abc123"
        assert scene.ifc_class == "IfcWall"
        assert len(scene.meshes) == 1

    def test_scene_to_dict(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)
        d = scene.to_dict()

        assert "meshes" in d
        assert "camera" in d
        assert d["element_id"] == "abc123"

    def test_scene_to_json(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)
        j = scene.to_json()
        parsed = json.loads(j)
        assert "meshes" in parsed


class TestWallGeometry:
    def test_wall_box_has_8_vertices(self, tmp_path: Path):
        """Export wall to JSON3D -> verify mesh has 8 vertices (box)."""
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        assert len(scene.meshes) == 1
        mesh = scene.meshes[0]
        assert len(mesh.vertices) == 8

    def test_wall_box_has_12_faces(self, tmp_path: Path):
        """Box should have 12 triangular faces (2 per side)."""
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)
        mesh = scene.meshes[0]
        assert len(mesh.faces) == 12

    def test_wall_dimensions_correct(self, tmp_path: Path):
        """Verify bounding box matches input dimensions."""
        folder = _make_element_folder(
            tmp_path, thickness_mm=150.0, height_mm=4000.0, length_mm=6000.0,
        )
        scene = Scene.from_element_folder(folder)
        mesh = scene.meshes[0]

        xs = [v[0] for v in mesh.vertices]
        ys = [v[1] for v in mesh.vertices]
        zs = [v[2] for v in mesh.vertices]

        assert pytest.approx(max(xs) - min(xs), rel=0.01) == 6.0  # length
        assert pytest.approx(max(ys) - min(ys), rel=0.01) == 0.15  # thickness
        assert pytest.approx(max(zs) - min(zs), rel=0.01) == 4.0  # height


class TestDoorGeometry:
    def test_door_geometry(self, tmp_path: Path):
        folder = _make_element_folder(
            tmp_path, ifc_class="IfcDoor", name="Test Door",
            thickness_mm=100.0, height_mm=2100.0, length_mm=900.0,
        )
        scene = Scene.from_element_folder(folder)
        assert len(scene.meshes) == 1
        assert len(scene.meshes[0].vertices) == 8


class TestWindowGeometry:
    def test_window_geometry(self, tmp_path: Path):
        folder = _make_element_folder(
            tmp_path, ifc_class="IfcWindow", name="Test Window",
            thickness_mm=100.0, height_mm=1500.0, length_mm=1200.0,
            material="Glass",
        )
        scene = Scene.from_element_folder(folder)
        assert len(scene.meshes) == 1
        assert len(scene.meshes[0].vertices) == 8


class TestSlabGeometry:
    def test_slab_geometry(self, tmp_path: Path):
        folder = _make_element_folder(
            tmp_path, ifc_class="IfcSlab", name="Test Slab",
            thickness_mm=200.0, height_mm=200.0, length_mm=10000.0,
        )
        scene = Scene.from_element_folder(folder)
        assert len(scene.meshes) == 1
        assert len(scene.meshes[0].vertices) == 8


class TestColumnGeometry:
    def test_column_cylinder(self, tmp_path: Path):
        """Column should generate a cylinder with more than 8 vertices."""
        folder = _make_element_folder(
            tmp_path, ifc_class="IfcColumn", name="Test Column",
            thickness_mm=400.0, height_mm=4000.0, length_mm=400.0,
            material="Steel",
        )
        scene = Scene.from_element_folder(folder)
        assert len(scene.meshes) == 1
        # Cylinder has 16 * 2 (circle verts) + 2 (centers) = 34
        assert len(scene.meshes[0].vertices) > 8


class TestBeamGeometry:
    def test_beam_geometry(self, tmp_path: Path):
        folder = _make_element_folder(
            tmp_path, ifc_class="IfcBeam", name="Test Beam",
            thickness_mm=300.0, height_mm=600.0, length_mm=8000.0,
            material="Steel",
        )
        scene = Scene.from_element_folder(folder)
        assert len(scene.meshes) == 1
        assert len(scene.meshes[0].vertices) == 8


# ---------------------------------------------------------------------------
# Material color mapping
# ---------------------------------------------------------------------------


class TestMaterialColors:
    def test_concrete_gray(self):
        materials = [{"name": "Concrete", "thickness": 200}]
        color = _get_material_color(materials)
        assert color == MATERIAL_COLORS["concrete"]

    def test_steel_silver(self):
        materials = [{"name": "Steel", "thickness": 10}]
        color = _get_material_color(materials)
        assert color == MATERIAL_COLORS["steel"]

    def test_glass_lightblue(self):
        materials = [{"name": "Glass", "thickness": 6}]
        color = _get_material_color(materials)
        assert color == MATERIAL_COLORS["glass"]

    def test_wood_brown(self):
        materials = [{"name": "Wood", "thickness": 50}]
        color = _get_material_color(materials)
        assert color == MATERIAL_COLORS["wood"]

    def test_unknown_material_default(self):
        materials = [{"name": "UnknownMaterial", "thickness": 10}]
        color = _get_material_color(materials)
        assert color == "#CCCCCC"


# ---------------------------------------------------------------------------
# Exporter tests
# ---------------------------------------------------------------------------


class TestJSON3DExporter:
    def test_export_creates_file(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        exporter = JSON3DExporter()
        output_dir = tmp_path / "export"
        result = exporter.export(scene, output_dir)

        assert result.success
        assert result.file_path is not None
        assert result.file_path.is_file()
        assert result.format == "json3d"

    def test_export_valid_json(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        exporter = JSON3DExporter()
        output_dir = tmp_path / "export"
        result = exporter.export(scene, output_dir)

        data = json.loads(result.file_path.read_text(encoding="utf-8"))
        assert "meshes" in data
        assert len(data["meshes"]) == 1
        assert "vertices" in data["meshes"][0]
        assert "faces" in data["meshes"][0]


class TestOBJExporter:
    def test_export_creates_files(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        exporter = OBJExporter()
        output_dir = tmp_path / "export"
        result = exporter.export(scene, output_dir)

        assert result.success
        assert result.file_path is not None
        assert result.file_path.is_file()
        assert result.format == "obj"

        # MTL file should also exist
        mtl_path = result.file_path.parent / "model.mtl"
        assert mtl_path.is_file()

    def test_obj_has_vertices_and_faces(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        exporter = OBJExporter()
        output_dir = tmp_path / "export"
        result = exporter.export(scene, output_dir)

        obj_content = result.file_path.read_text(encoding="utf-8")
        assert "v " in obj_content
        assert "f " in obj_content


class TestGLTFExporter:
    def test_gltf_fallback_to_json3d(self, tmp_path: Path):
        """GLTF export without pygltflib -> graceful fallback to JSON3D."""
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        exporter = GLTFExporter()
        output_dir = tmp_path / "export"
        result = exporter.export(scene, output_dir)

        # Should succeed (via fallback)
        assert result.success
        assert result.file_path is not None
        assert result.file_path.is_file()
        # Should mention fallback
        assert "json3d" in result.message.lower() or result.format in ("json3d", "gltf")


class TestSpeckleExporter:
    def test_speckle_without_library(self, tmp_path: Path):
        """Speckle export without specklepy -> graceful fallback, no crash."""
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        exporter = SpeckleExporter()  # No token, no specklepy
        output_dir = tmp_path / "export"
        result = exporter.export(scene, output_dir)

        assert not result.success
        assert result.file_path is None
        assert "unavailable" in result.message.lower()


# ---------------------------------------------------------------------------
# Viewer tests
# ---------------------------------------------------------------------------


class TestHTMLViewer:
    def test_viewer_generation(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        output_path = tmp_path / "viewer.html"
        result = generate_viewer(scene, output_path)

        assert result.is_file()

    def test_viewer_contains_threejs(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        output_path = tmp_path / "viewer.html"
        generate_viewer(scene, output_path)

        content = output_path.read_text(encoding="utf-8")
        assert "three" in content.lower()
        assert "OrbitControls" in content


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------


class TestVisualizationReport:
    def test_report_content(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)

        # Create a fake export result
        scene_path = folder / "visualization" / "scene.json"
        scene_path.parent.mkdir(parents=True, exist_ok=True)
        scene_path.write_text("{}", encoding="utf-8")

        results = [
            ExportResult(
                file_path=scene_path,
                format="json3d",
                success=True,
            ),
        ]

        md = render_visualization_report(
            element_id="abc123",
            ifc_class="IfcWall",
            export_results=results,
            element_folder=folder,
        )

        assert "JSON3D" in md
        assert "abc123" in md
        assert "scene.json" in md or "visualization" in md


# ---------------------------------------------------------------------------
# Bridge (integration) tests
# ---------------------------------------------------------------------------


class TestVisualizationBridge:
    def test_export_json3d(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        bridge = VisualizationBridge()
        result = bridge.export(folder, format="json3d")

        assert result.success
        assert result.file_path is not None
        assert result.file_path.is_file()

    def test_export_obj(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        bridge = VisualizationBridge()
        result = bridge.export(folder, format="obj")

        assert result.success
        assert result.file_path is not None
        assert result.file_path.is_file()

    def test_generate_viewer(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        bridge = VisualizationBridge()
        viewer_path = bridge.generate_viewer(folder)

        assert viewer_path.is_file()
        assert "html" in viewer_path.suffix.lower()

    def test_export_all(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        bridge = VisualizationBridge()
        results = bridge.export_all(folder)

        assert len(results) >= 2
        # Check VISUALIZATION.md was generated
        viz_md = folder / "VISUALIZATION.md"
        assert viz_md.is_file()
        content = viz_md.read_text(encoding="utf-8")
        assert "Visualization" in content


# ---------------------------------------------------------------------------
# Camera tests
# ---------------------------------------------------------------------------


class TestCamera:
    def test_isometric_camera(self, tmp_path: Path):
        folder = _make_element_folder(tmp_path)
        scene = Scene.from_element_folder(folder)

        cam = scene.camera
        assert cam.position != (0, 0, 0)
        assert cam.fov > 0
