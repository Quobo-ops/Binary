"""OBJ exporter — Wavefront .obj + .mtl, zero external dependencies."""

from __future__ import annotations

from pathlib import Path

from aecos.visualization.exporters.base import ExportResult, Exporter
from aecos.visualization.scene import Scene


class OBJExporter(Exporter):
    """Export scene as Wavefront OBJ + MTL files.

    Pure Python string formatting, no libraries needed.
    """

    @property
    def format_name(self) -> str:
        return "obj"

    def export(self, scene: Scene, output_dir: Path) -> ExportResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        obj_path = output_dir / "model.obj"
        mtl_path = output_dir / "model.mtl"

        mtl_lines: list[str] = []
        obj_lines: list[str] = [f"mtllib {mtl_path.name}"]

        vertex_offset = 0

        for i, mesh in enumerate(scene.meshes):
            mat_name = f"material_{i}"

            # MTL entry
            r, g, b = _hex_to_rgb(mesh.color)
            mtl_lines.append(f"newmtl {mat_name}")
            mtl_lines.append(f"Kd {r:.4f} {g:.4f} {b:.4f}")
            mtl_lines.append(f"Ka {r * 0.3:.4f} {g * 0.3:.4f} {b * 0.3:.4f}")
            mtl_lines.append("Ks 0.1000 0.1000 0.1000")
            mtl_lines.append("Ns 50.0")
            mtl_lines.append("d 1.0")
            mtl_lines.append("")

            # OBJ group
            obj_lines.append(f"o {mesh.name or f'mesh_{i}'}")
            obj_lines.append(f"usemtl {mat_name}")

            for vx, vy, vz in mesh.vertices:
                obj_lines.append(f"v {vx:.6f} {vy:.6f} {vz:.6f}")

            for f0, f1, f2 in mesh.faces:
                # OBJ faces are 1-indexed
                obj_lines.append(
                    f"f {f0 + 1 + vertex_offset} "
                    f"{f1 + 1 + vertex_offset} "
                    f"{f2 + 1 + vertex_offset}"
                )

            vertex_offset += len(mesh.vertices)

        mtl_path.write_text("\n".join(mtl_lines) + "\n", encoding="utf-8")
        obj_path.write_text("\n".join(obj_lines) + "\n", encoding="utf-8")

        return ExportResult(
            file_path=obj_path,
            format=self.format_name,
            message="OBJ exported successfully.",
        )


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color string to (r, g, b) floats in 0-1 range."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (0.8, 0.8, 0.8)
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)
