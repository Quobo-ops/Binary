"""glTF/GLB exporter — optional, requires pygltflib."""

from __future__ import annotations

import logging
from pathlib import Path

from aecos.visualization.exporters.base import ExportResult, Exporter
from aecos.visualization.exporters.json3d import JSON3DExporter
from aecos.visualization.scene import Scene

logger = logging.getLogger(__name__)


class GLTFExporter(Exporter):
    """Export scene as glTF 2.0 / GLB binary.

    Falls back to JSON3D export when pygltflib is unavailable.
    """

    @property
    def format_name(self) -> str:
        return "gltf"

    def is_available(self) -> bool:
        try:
            import pygltflib  # noqa: F401
            return True
        except ImportError:
            return False

    def export(self, scene: Scene, output_dir: Path) -> ExportResult:
        if not self.is_available():
            logger.warning(
                "pygltflib not available, falling back to JSON3D export."
            )
            fallback = JSON3DExporter()
            result = fallback.export(scene, output_dir)
            result.message = (
                "pygltflib not available; exported as JSON3D instead."
            )
            return result

        try:
            return self._export_glb(scene, output_dir)
        except Exception as exc:
            logger.warning("glTF export failed: %s; falling back to JSON3D", exc)
            fallback = JSON3DExporter()
            result = fallback.export(scene, output_dir)
            result.message = f"glTF export failed ({exc}); exported as JSON3D instead."
            return result

    def _export_glb(self, scene: Scene, output_dir: Path) -> ExportResult:
        """Perform actual glTF export using pygltflib."""
        import struct

        import pygltflib

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "model.glb"

        gltf = pygltflib.GLTF2(
            scene=0,
            scenes=[pygltflib.Scene(nodes=list(range(len(scene.meshes))))],
            nodes=[],
            meshes=[],
            accessors=[],
            bufferViews=[],
            buffers=[],
            materials=[],
        )

        binary_blob = bytearray()

        for i, mesh_data in enumerate(scene.meshes):
            r, g, b = _hex_to_rgb_float(mesh_data.color)
            mat_idx = len(gltf.materials)
            gltf.materials.append(
                pygltflib.Material(
                    pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                        baseColorFactor=[r, g, b, 1.0],
                        metallicFactor=0.1,
                        roughnessFactor=0.8,
                    ),
                    name=f"material_{i}",
                )
            )

            # Vertices
            vertex_data = bytearray()
            min_pos = [float("inf")] * 3
            max_pos = [float("-inf")] * 3
            for vx, vy, vz in mesh_data.vertices:
                vertex_data.extend(struct.pack("<fff", vx, vy, vz))
                min_pos = [min(min_pos[0], vx), min(min_pos[1], vy), min(min_pos[2], vz)]
                max_pos = [max(max_pos[0], vx), max(max_pos[1], vy), max(max_pos[2], vz)]

            vert_offset = len(binary_blob)
            binary_blob.extend(vertex_data)
            # Pad to 4-byte alignment
            while len(binary_blob) % 4 != 0:
                binary_blob.append(0)

            vert_bv_idx = len(gltf.bufferViews)
            gltf.bufferViews.append(
                pygltflib.BufferView(
                    buffer=0,
                    byteOffset=vert_offset,
                    byteLength=len(vertex_data),
                    target=pygltflib.ARRAY_BUFFER,
                )
            )

            vert_acc_idx = len(gltf.accessors)
            gltf.accessors.append(
                pygltflib.Accessor(
                    bufferView=vert_bv_idx,
                    componentType=pygltflib.FLOAT,
                    count=len(mesh_data.vertices),
                    type=pygltflib.VEC3,
                    max=max_pos,
                    min=min_pos,
                )
            )

            # Indices
            index_data = bytearray()
            for f0, f1, f2 in mesh_data.faces:
                index_data.extend(struct.pack("<HHH", f0, f1, f2))

            idx_offset = len(binary_blob)
            binary_blob.extend(index_data)
            while len(binary_blob) % 4 != 0:
                binary_blob.append(0)

            idx_bv_idx = len(gltf.bufferViews)
            gltf.bufferViews.append(
                pygltflib.BufferView(
                    buffer=0,
                    byteOffset=idx_offset,
                    byteLength=len(index_data),
                    target=pygltflib.ELEMENT_ARRAY_BUFFER,
                )
            )

            idx_acc_idx = len(gltf.accessors)
            gltf.accessors.append(
                pygltflib.Accessor(
                    bufferView=idx_bv_idx,
                    componentType=pygltflib.UNSIGNED_SHORT,
                    count=len(mesh_data.faces) * 3,
                    type=pygltflib.SCALAR,
                    max=[max(max(f) for f in mesh_data.faces)],
                    min=[0],
                )
            )

            gltf.nodes.append(pygltflib.Node(mesh=i, name=mesh_data.name or f"mesh_{i}"))
            gltf.meshes.append(
                pygltflib.Mesh(
                    primitives=[
                        pygltflib.Primitive(
                            attributes=pygltflib.Attributes(POSITION=vert_acc_idx),
                            indices=idx_acc_idx,
                            material=mat_idx,
                        )
                    ],
                    name=mesh_data.name or f"mesh_{i}",
                )
            )

        gltf.buffers = [pygltflib.Buffer(byteLength=len(binary_blob))]
        gltf.set_binary_blob(bytes(binary_blob))

        gltf.save(str(output_path))

        return ExportResult(
            file_path=output_path,
            format=self.format_name,
            message="glTF GLB exported successfully.",
        )


def _hex_to_rgb_float(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (0.8, 0.8, 0.8)
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)
