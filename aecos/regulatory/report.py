"""UpdateReport — model and Markdown generation for regulatory updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class UpdateReport(BaseModel):
    """Report of a regulatory update application."""

    code_name: str = ""
    old_version: str = ""
    new_version: str = ""
    changes_summary: str = ""
    rules_added: int = 0
    rules_modified: int = 0
    rules_removed: int = 0
    affected_templates_count: int = 0
    affected_elements_count: int = 0
    git_tag: str = ""
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_markdown(self) -> str:
        """Generate REGULATORY_UPDATE.md content."""
        lines: list[str] = [
            "# Regulatory Update Report",
            "",
            f"**Code:** {self.code_name}",
            f"**Old Version:** {self.old_version}",
            f"**New Version:** {self.new_version}",
            f"**Applied At:** {self.applied_at.isoformat()}",
            "",
        ]

        if self.git_tag:
            lines.append(f"**Git Tag:** `{self.git_tag}`")
            lines.append("")

        lines.extend([
            "## Changes Summary",
            "",
            self.changes_summary or "No changes summary provided.",
            "",
            "## Rule Changes",
            "",
            f"| Change Type | Count |",
            f"|-------------|-------|",
            f"| Added       | {self.rules_added} |",
            f"| Modified    | {self.rules_modified} |",
            f"| Removed     | {self.rules_removed} |",
            "",
            "## Impact Assessment",
            "",
            f"- **Affected Templates:** {self.affected_templates_count}",
            f"- **Affected Elements:** {self.affected_elements_count}",
            "",
        ])

        if self.affected_templates_count > 0 or self.affected_elements_count > 0:
            lines.extend([
                "## Action Required",
                "",
                "- Re-validate affected elements against updated rules",
                "- Review templates for compliance with new requirements",
                "- Update fine-tuning dataset if rules changed materially",
                "",
            ])

        return "\n".join(lines)
