"""Scene model — element positions, materials, camera for 3D visualization."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Material color mapping (AEC standard)
MATERIAL_COLORS: dict[str, str] = {
    "concrete": "#808080",      # gray
    "steel": "#C0C0C0",         # silver
    "glass": "#ADD8E6",         # lightblue
    "wood": "#8B4513",          # brown
    "brick": "#B22222",         # firebrick
    "aluminum": "#A9A9A9",      # darkgray
    "stone": "#696969",         # dimgray
    "copper": "#B87333",        # copper
    "gypsum": "#F5F5DC",        # beige
    "insulation": "#FFD700",    # gold
    "plaster": "#FAEBD7",       # antiquewhite
    "timber": "#DEB887",        # burlywood
    "masonry": "#CD853F",       # peru
}

DEFAULT_COLOR = "#CCCCCC"


@dataclass
class MeshData:
    """A single mesh primitive with vertices, faces, and transform."""

    vertices: list[tuple[float, float, float]]
    faces: list[tuple[int, int, int]]
    color: str = DEFAULT_COLOR
    name: str = ""
    transform: list[float] = field(default_factory=lambda: [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1,
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vertices": [list(v) for v in self.vertices],
            "faces": [list(f) for f in self.faces],
            "color": self.color,
            "transform": self.transform,
        }


@dataclass
class Camera:
    """Camera settings for the scene."""

    position: tuple[float, float, float] = (10.0, 10.0, 10.0)
    target: tuple[float, float, float] = (0.0, 0.0, 0.0)
    up: tuple[float, float, float] = (0.0, 0.0, 1.0)
    fov: float = 45.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": list(self.position),
            "target": list(self.target),
            "up": list(self.up),
            "fov": self.fov,
        }


@dataclass
class Scene:
    """3D scene containing meshes and camera configuration."""

    meshes: list[MeshData] = field(default_factory=list)
    camera: Camera = field(default_factory=Camera)
    element_id: str = ""
    ifc_class: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "ifc_class": self.ifc_class,
            "meshes": [m.to_dict() for m in self.meshes],
            "camera": self.camera.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_element_folder(cls, element_folder: str | Path) -> Scene:
        """Build a Scene from an element folder's metadata.

        Reads geometry/shape.json, materials/materials.json, and metadata.json
        to construct bounding-box 3D representations.
        """
        folder = Path(element_folder)

        metadata = _load_json(folder / "metadata.json")
        geometry = _load_json(folder / "geometry" / "shape.json")
        materials_data = _load_json(folder / "materials" / "materials.json")
        spatial = _load_json(folder / "relationships" / "spatial.json")

        element_id = metadata.get("GlobalId", "")
        ifc_class = metadata.get("IFCClass", "")

        # Determine color from material
        color = _get_material_color(materials_data)

        # Build mesh from bounding box
        mesh = _build_mesh_from_geometry(geometry, ifc_class, color, element_id)

        # Compute camera position
        camera = _compute_isometric_camera(geometry)

        return cls(
            meshes=[mesh] if mesh else [],
            camera=camera,
            element_id=element_id,
            ifc_class=ifc_class,
        )


def _load_json(path: Path) -> Any:
    """Load a JSON file, returning empty dict/list on failure."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _get_material_color(materials_data: Any) -> str:
    """Resolve material color from materials list."""
    if not isinstance(materials_data, list) or not materials_data:
        return DEFAULT_COLOR

    primary_material = materials_data[0].get("name", "").lower()
    for keyword, color in MATERIAL_COLORS.items():
        if keyword in primary_material:
            return color
    return DEFAULT_COLOR


def _build_mesh_from_geometry(
    geometry: dict[str, Any],
    ifc_class: str,
    color: str,
    name: str,
) -> MeshData | None:
    """Build a mesh primitive from geometry/shape.json data."""
    bb = geometry.get("bounding_box")
    if not bb:
        return None

    min_x = float(bb.get("min_x", 0))
    min_y = float(bb.get("min_y", 0))
    min_z = float(bb.get("min_z", 0))
    max_x = float(bb.get("max_x", 1))
    max_y = float(bb.get("max_y", 1))
    max_z = float(bb.get("max_z", 1))

    ifc_lower = ifc_class.lower()

    if "column" in ifc_lower:
        return _build_cylinder(min_x, min_y, min_z, max_x, max_y, max_z, color, name)

    # Default: box for walls, slabs, doors, windows, beams, etc.
    return _build_box(min_x, min_y, min_z, max_x, max_y, max_z, color, name)


def _build_box(
    min_x: float, min_y: float, min_z: float,
    max_x: float, max_y: float, max_z: float,
    color: str, name: str,
) -> MeshData:
    """Generate a box mesh from bounding box coordinates.

    8 vertices, 12 triangular faces (2 per side).
    """
    vertices = [
        (min_x, min_y, min_z),  # 0
        (max_x, min_y, min_z),  # 1
        (max_x, max_y, min_z),  # 2
        (min_x, max_y, min_z),  # 3
        (min_x, min_y, max_z),  # 4
        (max_x, min_y, max_z),  # 5
        (max_x, max_y, max_z),  # 6
        (min_x, max_y, max_z),  # 7
    ]

    faces = [
        # Bottom
        (0, 1, 2), (0, 2, 3),
        # Top
        (4, 6, 5), (4, 7, 6),
        # Front
        (0, 5, 1), (0, 4, 5),
        # Back
        (2, 7, 3), (2, 6, 7),
        # Left
        (0, 3, 7), (0, 7, 4),
        # Right
        (1, 5, 6), (1, 6, 2),
    ]

    return MeshData(vertices=vertices, faces=faces, color=color, name=name)


def _build_cylinder(
    min_x: float, min_y: float, min_z: float,
    max_x: float, max_y: float, max_z: float,
    color: str, name: str,
    segments: int = 16,
) -> MeshData:
    """Generate a cylinder mesh approximation for columns.

    Uses the bounding box center XY as the axis and full Z extent as height.
    """
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    rx = (max_x - min_x) / 2
    ry = (max_y - min_y) / 2
    r = (rx + ry) / 2  # average radius

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []

    # Bottom circle vertices
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        vertices.append((round(x, 6), round(y, 6), min_z))

    # Top circle vertices
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        vertices.append((round(x, 6), round(y, 6), max_z))

    # Bottom center
    bottom_center = len(vertices)
    vertices.append((cx, cy, min_z))

    # Top center
    top_center = len(vertices)
    vertices.append((cx, cy, max_z))

    # Side faces
    for i in range(segments):
        next_i = (i + 1) % segments
        b0 = i
        b1 = next_i
        t0 = i + segments
        t1 = next_i + segments
        faces.append((b0, b1, t1))
        faces.append((b0, t1, t0))

    # Bottom cap
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append((bottom_center, next_i, i))

    # Top cap
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append((top_center, i + segments, next_i + segments))

    return MeshData(vertices=vertices, faces=faces, color=color, name=name)


def _compute_isometric_camera(geometry: dict[str, Any]) -> Camera:
    """Compute an isometric camera position framing the element."""
    bb = geometry.get("bounding_box")
    if not bb:
        return Camera()

    min_x = float(bb.get("min_x", 0))
    min_y = float(bb.get("min_y", 0))
    min_z = float(bb.get("min_z", 0))
    max_x = float(bb.get("max_x", 1))
    max_y = float(bb.get("max_y", 1))
    max_z = float(bb.get("max_z", 1))

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    cz = (min_z + max_z) / 2

    # Distance based on diagonal
    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    diagonal = math.sqrt(dx * dx + dy * dy + dz * dz)
    distance = max(diagonal * 1.5, 2.0)

    # Isometric offset
    offset = distance / math.sqrt(3)

    return Camera(
        position=(
            round(cx + offset, 4),
            round(cy + offset, 4),
            round(cz + offset, 4),
        ),
        target=(round(cx, 4), round(cy, 4), round(cz, 4)),
    )
