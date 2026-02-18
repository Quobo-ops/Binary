"""Abstract Exporter interface for all visualization export formats."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aecos.visualization.scene import Scene


@dataclass
class ExportResult:
    """Result of a visualization export operation."""

    file_path: Path | None
    format: str
    preview_url: str | None = None
    success: bool = True
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path) if self.file_path else None,
            "format": self.format,
            "preview_url": self.preview_url,
            "success": self.success,
            "message": self.message,
        }


class Exporter(abc.ABC):
    """Base class for all visualization exporters."""

    @property
    @abc.abstractmethod
    def format_name(self) -> str:
        """Short format identifier (e.g., 'json3d', 'obj', 'gltf')."""

    @abc.abstractmethod
    def export(self, scene: Scene, output_dir: Path) -> ExportResult:
        """Export the scene to the target format.

        Parameters
        ----------
        scene:
            The 3D scene to export.
        output_dir:
            Directory in which to write the output file(s).

        Returns
        -------
        ExportResult
            Result containing file path and status.
        """

    def is_available(self) -> bool:
        """Return True if this exporter's dependencies are satisfied."""
        return True
