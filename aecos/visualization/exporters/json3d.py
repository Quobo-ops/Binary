"""JSON3D exporter — always available, zero external dependencies."""

from __future__ import annotations

import json
from pathlib import Path

from aecos.visualization.exporters.base import ExportResult, Exporter
from aecos.visualization.scene import Scene


class JSON3DExporter(Exporter):
    """Export scene as a JSON scene graph.

    Format: ``{meshes: [{vertices, faces, color, transform}], camera: {...}}``

    Always available — pure Python dict to json.dumps.
    """

    @property
    def format_name(self) -> str:
        return "json3d"

    def export(self, scene: Scene, output_dir: Path) -> ExportResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "scene.json"

        data = scene.to_dict()
        output_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8",
        )

        return ExportResult(
            file_path=output_path,
            format=self.format_name,
            message="JSON3D scene exported successfully.",
        )
