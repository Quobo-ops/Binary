"""RuleDiffer — compares old vs new rule sets and produces change sets."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aecos.compliance.rules import Rule

logger = logging.getLogger(__name__)


class RuleDiffResult(BaseModel):
    """Result of diffing two rule sets."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    added: list[Rule] = Field(default_factory=list)
    modified: list[tuple[Rule, Rule]] = Field(default_factory=list)
    """Each tuple is (old_rule, new_rule) for modified rules."""

    removed: list[Rule] = Field(default_factory=list)
    unchanged: list[Rule] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.removed)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.modified) + len(self.removed)

    def summary(self) -> str:
        return (
            f"Added: {len(self.added)}, Modified: {len(self.modified)}, "
            f"Removed: {len(self.removed)}, Unchanged: {len(self.unchanged)}"
        )


class RuleDiffer:
    """Compare old and new rule sets, producing a diff result.

    Rules are keyed by (code_name, section) for comparison.
    """

    @staticmethod
    def _rule_key(rule: Rule) -> tuple[str, str]:
        """Generate a unique key for a rule based on code and section."""
        return (rule.code_name, rule.section)

    def diff_rules(
        self,
        old_rules: list[Rule],
        new_rules: list[Rule],
    ) -> RuleDiffResult:
        """Compare old rules against new rules.

        Parameters
        ----------
        old_rules:
            The current set of rules in the compliance database.
        new_rules:
            The proposed new/updated rules.

        Returns
        -------
        RuleDiffResult
            Contains added, modified, removed, and unchanged rule lists.
        """
        old_map: dict[tuple[str, str], Rule] = {}
        for rule in old_rules:
            old_map[self._rule_key(rule)] = rule

        new_map: dict[tuple[str, str], Rule] = {}
        for rule in new_rules:
            new_map[self._rule_key(rule)] = rule

        added: list[Rule] = []
        modified: list[tuple[Rule, Rule]] = []
        removed: list[Rule] = []
        unchanged: list[Rule] = []

        # Find added and modified
        for key, new_rule in new_map.items():
            if key not in old_map:
                added.append(new_rule)
            else:
                old_rule = old_map[key]
                if self._rules_differ(old_rule, new_rule):
                    modified.append((old_rule, new_rule))
                else:
                    unchanged.append(new_rule)

        # Find removed
        for key, old_rule in old_map.items():
            if key not in new_map:
                removed.append(old_rule)

        result = RuleDiffResult(
            added=added,
            modified=modified,
            removed=removed,
            unchanged=unchanged,
        )

        logger.info("Rule diff: %s", result.summary())
        return result

    @staticmethod
    def _rules_differ(old: Rule, new: Rule) -> bool:
        """Check if two rules with the same key have different content."""
        return (
            old.title != new.title
            or old.check_type != new.check_type
            or old.property_path != new.property_path
            or str(old.check_value) != str(new.check_value)
            or old.ifc_classes != new.ifc_classes
            or old.region != new.region
            or old.citation != new.citation
        )
