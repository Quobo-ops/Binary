"""Speckle exporter — optional, graceful fallback when specklepy unavailable."""

from __future__ import annotations

import logging
from pathlib import Path

from aecos.visualization.exporters.base import ExportResult, Exporter
from aecos.visualization.scene import Scene

logger = logging.getLogger(__name__)


class SpeckleExporter(Exporter):
    """Export scene to a Speckle server.

    Requires ``specklepy`` and valid credentials.
    Gracefully returns a failure result when unavailable — never crashes.
    """

    def __init__(
        self,
        server_url: str = "https://speckle.xyz",
        token: str | None = None,
    ) -> None:
        self._server_url = server_url
        self._token = token

    @property
    def format_name(self) -> str:
        return "speckle"

    def is_available(self) -> bool:
        if not self._token:
            return False
        try:
            import specklepy  # noqa: F401
            return True
        except ImportError:
            return False

    def export(self, scene: Scene, output_dir: Path) -> ExportResult:
        if not self.is_available():
            logger.warning(
                "Speckle export unavailable (missing specklepy or token). "
                "Skipping."
            )
            return ExportResult(
                file_path=None,
                format=self.format_name,
                success=False,
                message="Speckle unavailable: missing specklepy package or token.",
            )

        try:
            return self._push_to_speckle(scene)
        except Exception as exc:
            logger.warning("Speckle export failed: %s", exc)
            return ExportResult(
                file_path=None,
                format=self.format_name,
                success=False,
                message=f"Speckle export failed: {exc}",
            )

    def _push_to_speckle(self, scene: Scene) -> ExportResult:
        """Perform actual Speckle push."""
        from specklepy.api.client import SpeckleClient
        from specklepy.objects import Base

        client = SpeckleClient(host=self._server_url)
        client.authenticate_with_token(self._token)

        stream_name = f"AECOS_{scene.element_id or 'export'}"
        stream = client.stream.create(name=stream_name)

        obj = Base()
        obj["name"] = scene.element_id
        obj["ifc_class"] = scene.ifc_class
        obj["meshes"] = [m.to_dict() for m in scene.meshes]

        from specklepy.api import operations
        from specklepy.transports.server import ServerTransport

        transport = ServerTransport(client=client, stream_id=stream.id)
        obj_id = operations.send(base=obj, transports=[transport])

        client.commit.create(
            stream_id=stream.id,
            object_id=obj_id,
            message=f"AEC OS export: {scene.element_id}",
            branch_name="main",
        )

        url = f"{self._server_url}/streams/{stream.id}"

        return ExportResult(
            file_path=None,
            format=self.format_name,
            preview_url=url,
            message=f"Pushed to Speckle: {url}",
        )
