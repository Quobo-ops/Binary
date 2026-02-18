"""VisualizationBridge — main entry point for 3D export and preview."""

from __future__ import annotations

import logging
from pathlib import Path

from aecos.metadata.writer import write_markdown
from aecos.visualization.exporters.base import ExportResult, Exporter
from aecos.visualization.exporters.gltf import GLTFExporter
from aecos.visualization.exporters.json3d import JSON3DExporter
from aecos.visualization.exporters.obj import OBJExporter
from aecos.visualization.exporters.speckle import SpeckleExporter
from aecos.visualization.report import render_visualization_report
from aecos.visualization.scene import Scene
from aecos.visualization.viewer import generate_viewer

logger = logging.getLogger(__name__)

# Re-export ExportResult for convenience
__all__ = ["ExportResult", "VisualizationBridge"]

_EXPORTERS: dict[str, type[Exporter]] = {
    "json3d": JSON3DExporter,
    "obj": OBJExporter,
    "gltf": GLTFExporter,
    "speckle": SpeckleExporter,
}


class VisualizationBridge:
    """Main entry point for visualization exports.

    Parameters
    ----------
    speckle_url:
        Optional Speckle server URL.
    speckle_token:
        Optional Speckle authentication token.
    """

    def __init__(
        self,
        *,
        speckle_url: str = "https://speckle.xyz",
        speckle_token: str | None = None,
    ) -> None:
        self._speckle_url = speckle_url
        self._speckle_token = speckle_token

    def export(
        self,
        element_folder: str | Path,
        format: str = "json3d",
    ) -> ExportResult:
        """Export an element to the specified 3D format.

        Parameters
        ----------
        element_folder:
            Path to the element folder.
        format:
            Export format: ``json3d``, ``obj``, ``gltf``, or ``speckle``.

        Returns
        -------
        ExportResult
            Result containing file path / URL and status.
        """
        folder = Path(element_folder)

        scene = Scene.from_element_folder(folder)

        output_dir = folder / "visualization"

        exporter = self._get_exporter(format)
        return exporter.export(scene, output_dir)

    def export_all(
        self,
        element_folder: str | Path,
        formats: list[str] | None = None,
    ) -> list[ExportResult]:
        """Export to multiple formats and generate VISUALIZATION.md.

        Parameters
        ----------
        element_folder:
            Path to the element folder.
        formats:
            List of format names. Defaults to ``["json3d", "obj"]``.

        Returns
        -------
        list[ExportResult]
            Results from all export attempts.
        """
        if formats is None:
            formats = ["json3d", "obj"]

        folder = Path(element_folder)
        scene = Scene.from_element_folder(folder)
        output_dir = folder / "visualization"

        results: list[ExportResult] = []
        for fmt in formats:
            exporter = self._get_exporter(fmt)
            result = exporter.export(scene, output_dir)
            results.append(result)

        # Generate viewer
        viewer_path = self.generate_viewer(element_folder)

        # Generate VISUALIZATION.md
        self._write_report(folder, scene, results, viewer_path)

        return results

    def generate_viewer(self, element_folder: str | Path) -> Path:
        """Generate an interactive HTML viewer for the element.

        Parameters
        ----------
        element_folder:
            Path to the element folder.

        Returns
        -------
        Path
            Path to the generated HTML file.
        """
        folder = Path(element_folder)
        scene = Scene.from_element_folder(folder)
        output_path = folder / "visualization" / "viewer.html"
        return generate_viewer(scene, output_path)

    def _get_exporter(self, format: str) -> Exporter:
        """Instantiate the appropriate exporter."""
        if format == "speckle":
            return SpeckleExporter(
                server_url=self._speckle_url,
                token=self._speckle_token,
            )

        exporter_cls = _EXPORTERS.get(format)
        if exporter_cls is None:
            logger.warning("Unknown format '%s', using json3d", format)
            exporter_cls = JSON3DExporter

        return exporter_cls()

    def _write_report(
        self,
        element_folder: Path,
        scene: Scene,
        results: list[ExportResult],
        viewer_path: Path | None,
    ) -> Path:
        """Write VISUALIZATION.md into the element folder."""
        md_content = render_visualization_report(
            element_id=scene.element_id,
            ifc_class=scene.ifc_class,
            export_results=results,
            viewer_path=viewer_path,
            element_folder=element_folder,
        )
        return write_markdown(element_folder, "VISUALIZATION.md", md_content)
