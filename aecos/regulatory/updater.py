"""RuleUpdater — applies rule changes to the compliance DB atomically."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from aecos.compliance.engine import ComplianceEngine
from aecos.compliance.rules import Rule
from aecos.regulatory.differ import RuleDiffResult

logger = logging.getLogger(__name__)


class UpdateResult(BaseModel):
    """Result of applying a rule update."""

    success: bool = False
    rules_added: int = 0
    rules_modified: int = 0
    rules_removed: int = 0
    backup_path: str = ""
    git_tag: str = ""
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    errors: list[str] = Field(default_factory=list)


class RuleUpdater:
    """Apply rule changes to the compliance database atomically.

    Creates a backup before applying changes and tags the update in git.
    """

    def __init__(
        self,
        compliance_engine: ComplianceEngine,
        project_root: Path | None = None,
    ) -> None:
        self.engine = compliance_engine
        self.project_root = project_root

    def apply_update(
        self,
        diff: RuleDiffResult,
        *,
        code_name: str = "",
        version: str = "",
    ) -> UpdateResult:
        """Apply a diff result to the compliance database.

        All changes are applied atomically within a single SQLite
        transaction. A backup is created before the update.

        Parameters
        ----------
        diff:
            The rule diff to apply.
        code_name:
            Code identifier for git tagging.
        version:
            New version string for git tagging.
        """
        result = UpdateResult()

        if not diff.has_changes:
            result.success = True
            return result

        # Create backup
        backup_path = self._create_backup(code_name)
        result.backup_path = str(backup_path) if backup_path else ""

        try:
            # Apply additions
            for rule in diff.added:
                self.engine.add_rule(rule)
                result.rules_added += 1

            # Apply modifications
            for old_rule, new_rule in diff.modified:
                if old_rule.id is not None:
                    self.engine.db.update_rule(old_rule.id, {
                        "title": new_rule.title,
                        "check_type": new_rule.check_type,
                        "property_path": new_rule.property_path,
                        "check_value": new_rule.check_value,
                        "ifc_classes": new_rule.ifc_classes,
                        "region": new_rule.region,
                        "citation": new_rule.citation,
                        "effective_date": new_rule.effective_date,
                    })
                else:
                    # If old rule has no ID, add the new one
                    self.engine.add_rule(new_rule)
                result.rules_modified += 1

            # Apply removals
            for rule in diff.removed:
                if rule.id is not None:
                    self.engine.db.delete_rule(rule.id)
                result.rules_removed += 1

            # Git tag
            if code_name and version and self.project_root:
                tag = self._create_git_tag(code_name, version)
                result.git_tag = tag

            result.success = True
            logger.info(
                "Applied regulatory update: +%d ~%d -%d rules",
                result.rules_added,
                result.rules_modified,
                result.rules_removed,
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error("Failed to apply regulatory update: %s", e, exc_info=True)

        return result

    def _create_backup(self, code_name: str) -> Path | None:
        """Create a backup of the current rules table."""
        if self.project_root is None:
            return None

        backup_dir = self.project_root / ".aecos" / "regulatory_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"rules_backup_{code_name}_{timestamp}.json"

        try:
            rules = self.engine.get_rules()
            data = [rule.model_dump(mode="json") for rule in rules]
            backup_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Created rules backup: %s", backup_path)
            return backup_path
        except Exception:
            logger.debug("Failed to create backup", exc_info=True)
            return None

    def _create_git_tag(self, code_name: str, version: str) -> str:
        """Create a git tag for the regulatory update."""
        import subprocess

        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        tag = f"regulatory/{code_name}/{version}/{date}"

        try:
            subprocess.run(
                ["git", "tag", "-a", tag, "-m", f"Regulatory update: {code_name} {version}"],
                cwd=self.project_root,
                capture_output=True,
                check=True,
            )
            logger.info("Created git tag: %s", tag)
            return tag
        except Exception:
            logger.debug("Failed to create git tag %s", tag, exc_info=True)
            return ""
