"""RollbackManager — version snapshots and restoration."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RollbackManager:
    """Create, list, and restore project snapshots.

    Uses git tags for code state and file copies for databases/config.

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    """

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self._snapshots_dir = self.project_root / ".aecos" / "snapshots"

    def create_snapshot(self, label: str) -> dict[str, Any]:
        """Create a snapshot with the given label.

        Returns snapshot metadata dict.
        """
        ts = datetime.now(timezone.utc).isoformat()
        snap_dir = self._snapshots_dir / label
        snap_dir.mkdir(parents=True, exist_ok=True)

        # 1. Git tag
        git_tag = f"snapshot/{label}"
        try:
            subprocess.run(
                ["git", "tag", "-f", git_tag],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.debug("Git tag creation failed", exc_info=True)

        # 2. Backup databases and config
        for name in ("audit.db", "analytics.db"):
            src = self.project_root / name
            if src.is_file():
                shutil.copy2(src, snap_dir / name)

        config_dir = self.project_root / ".aecos"
        for name in ("config.json", "permissions.json"):
            src = config_dir / name
            if src.is_file():
                shutil.copy2(src, snap_dir / name)

        # 3. Write metadata
        metadata: dict[str, Any] = {
            "label": label,
            "timestamp": ts,
            "git_tag": git_tag,
        }
        (snap_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8",
        )

        return metadata

    def list_snapshots(self) -> list[dict[str, Any]]:
        """Return all snapshots sorted by timestamp."""
        snapshots: list[dict[str, Any]] = []
        if not self._snapshots_dir.is_dir():
            return snapshots

        for snap_dir in sorted(self._snapshots_dir.iterdir()):
            meta_path = snap_dir / "metadata.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    snapshots.append(meta)
                except (json.JSONDecodeError, OSError):
                    pass

        return snapshots

    def rollback(self, label: str) -> bool:
        """Restore to a snapshot.

        Returns True if successful.
        """
        snap_dir = self._snapshots_dir / label
        meta_path = snap_dir / "metadata.json"

        if not meta_path.is_file():
            logger.error("Snapshot not found: %s", label)
            return False

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        # 1. Git checkout to tag
        git_tag = meta.get("git_tag", "")
        if git_tag:
            try:
                subprocess.run(
                    ["git", "checkout", git_tag],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.debug("Git checkout failed", exc_info=True)

        # 2. Restore databases
        for name in ("audit.db", "analytics.db"):
            src = snap_dir / name
            if src.is_file():
                shutil.copy2(src, self.project_root / name)

        # 3. Restore config
        config_dir = self.project_root / ".aecos"
        config_dir.mkdir(parents=True, exist_ok=True)
        for name in ("config.json", "permissions.json"):
            src = snap_dir / name
            if src.is_file():
                shutil.copy2(src, config_dir / name)

        logger.info("Rolled back to snapshot: %s", label)
        return True
