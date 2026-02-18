"""SystemPackager — bundles aecos for distribution."""

from __future__ import annotations

import json
import logging
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aecos.security.hasher import Hasher

logger = logging.getLogger(__name__)

_EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".aecos"}
_EXCLUDE_FILES = {".env", "audit.db", "analytics.db"}
_EXCLUDE_EXTENSIONS = {".pyc", ".pyo"}


class SystemPackager:
    """Bundle an AEC OS project for distribution."""

    def package(
        self,
        project_path: str | Path,
        output_path: str | Path,
        *,
        include_models: bool = False,
    ) -> Path:
        """Create a .tar.gz archive with manifest.

        Parameters
        ----------
        project_path:
            Root of the AEC OS project.
        output_path:
            Where to write the archive.
        include_models:
            If True, include fine-tuning model files.

        Returns the path to the created archive.
        """
        root = Path(project_path).resolve()
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        if not out.name.endswith(".tar.gz"):
            out = out.with_suffix(".tar.gz")

        manifest: dict[str, Any] = {
            "package_timestamp": datetime.now(timezone.utc).isoformat(),
            "source_root": str(root),
            "files": {},
        }

        with tarfile.open(out, "w:gz") as tar:
            for fpath in sorted(root.rglob("*")):
                if not fpath.is_file():
                    continue

                rel = fpath.relative_to(root)
                parts = rel.parts

                # Exclusions
                if any(d in _EXCLUDE_DIRS for d in parts):
                    continue
                if fpath.name in _EXCLUDE_FILES:
                    continue
                if fpath.suffix in _EXCLUDE_EXTENSIONS:
                    continue
                if not include_models and "fine_tuning" in parts and "models" in parts:
                    continue

                arcname = rel.as_posix()
                tar.add(fpath, arcname=arcname)
                manifest["files"][arcname] = Hasher.hash_file(fpath)

            # Write manifest into archive
            manifest_json = json.dumps(manifest, indent=2).encode("utf-8")
            import io
            info = tarfile.TarInfo(name="package_manifest.json")
            info.size = len(manifest_json)
            tar.addfile(info, io.BytesIO(manifest_json))

        # Also write manifest beside the archive
        manifest_path = out.parent / "package_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        logger.info("Package created: %s (%d files)", out, len(manifest["files"]))
        return out
