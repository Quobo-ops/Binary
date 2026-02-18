"""Installer — sets up aecos on a fresh machine."""

from __future__ import annotations

import json
import logging
import tarfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aecos.security.hasher import Hasher

logger = logging.getLogger(__name__)


class InstallResult(BaseModel):
    """Result of an installation attempt."""

    success: bool = False
    version: str = ""
    installed_path: str = ""
    warnings: list[str] = Field(default_factory=list)


class Installer:
    """Verify and install AEC OS packages."""

    def verify_package(self, archive_path: str | Path) -> bool:
        """Validate the archive manifest hashes.

        Returns True if all file hashes match the manifest.
        """
        archive = Path(archive_path)
        if not archive.is_file():
            return False

        try:
            with tarfile.open(archive, "r:gz") as tar:
                # Extract manifest
                try:
                    mf = tar.extractfile("package_manifest.json")
                    if mf is None:
                        return False
                    manifest = json.loads(mf.read())
                except (KeyError, json.JSONDecodeError):
                    return False

                files_map: dict[str, str] = manifest.get("files", {})

                for fname, expected_hash in files_map.items():
                    try:
                        member = tar.getmember(fname)
                    except KeyError:
                        logger.warning("Missing file in archive: %s", fname)
                        return False

                    ef = tar.extractfile(member)
                    if ef is None:
                        return False

                    import hashlib
                    h = hashlib.sha256()
                    while True:
                        chunk = ef.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)

                    if h.hexdigest() != expected_hash:
                        logger.warning("Hash mismatch for %s", fname)
                        return False

        except (tarfile.TarError, OSError) as exc:
            logger.error("Failed to verify package: %s", exc)
            return False

        return True

    def install(
        self,
        archive_path: str | Path,
        target_path: str | Path,
    ) -> InstallResult:
        """Extract and install the package.

        Parameters
        ----------
        archive_path:
            Path to .tar.gz archive.
        target_path:
            Installation directory.
        """
        archive = Path(archive_path)
        target = Path(target_path)
        warnings: list[str] = []

        if not self.verify_package(archive):
            return InstallResult(
                success=False,
                warnings=["Package verification failed"],
            )

        target.mkdir(parents=True, exist_ok=True)

        try:
            with tarfile.open(archive, "r:gz") as tar:
                # Filter to avoid path traversal
                members = []
                for m in tar.getmembers():
                    if m.name.startswith("/") or ".." in m.name:
                        warnings.append(f"Skipped suspicious path: {m.name}")
                        continue
                    members.append(m)
                tar.extractall(target, members=members)
        except (tarfile.TarError, OSError) as exc:
            return InstallResult(
                success=False,
                warnings=[f"Extraction failed: {exc}"],
            )

        # Read version from pyproject.toml if present
        version = ""
        pyproject = target / "pyproject.toml"
        if pyproject.is_file():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version"):
                    version = line.split("=", 1)[-1].strip().strip('"').strip("'")
                    break

        return InstallResult(
            success=True,
            version=version,
            installed_path=str(target),
            warnings=warnings,
        )
