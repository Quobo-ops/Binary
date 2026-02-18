"""AEC-aware conflict detection and resolution for JSON, Markdown, and IFC."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConflictResult:
    """Result of a merge operation."""

    merged: Any
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    is_clean: bool = True

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


def merge_json(
    ancestor: dict[str, Any],
    ours: dict[str, Any],
    theirs: dict[str, Any],
) -> ConflictResult:
    """Property-level 3-way merge for JSON dicts.

    Non-overlapping changes merge automatically.
    Overlapping changes on the same key are flagged as conflicts.

    Parameters
    ----------
    ancestor:
        Common ancestor version.
    ours:
        Our version (local changes).
    theirs:
        Their version (remote changes).

    Returns
    -------
    ConflictResult
        Merged dict + list of unresolved conflicts.
    """
    merged = dict(ancestor)
    conflicts: list[dict[str, Any]] = []

    all_keys = set(ancestor.keys()) | set(ours.keys()) | set(theirs.keys())

    for key in all_keys:
        ancestor_val = ancestor.get(key, _SENTINEL)
        our_val = ours.get(key, _SENTINEL)
        their_val = theirs.get(key, _SENTINEL)

        our_changed = our_val != ancestor_val
        their_changed = their_val != ancestor_val

        if not our_changed and not their_changed:
            # No changes
            if ancestor_val is not _SENTINEL:
                merged[key] = ancestor_val
            continue

        if our_changed and not their_changed:
            # Only we changed
            if our_val is _SENTINEL:
                merged.pop(key, None)
            else:
                merged[key] = our_val
            continue

        if their_changed and not our_changed:
            # Only they changed
            if their_val is _SENTINEL:
                merged.pop(key, None)
            else:
                merged[key] = their_val
            continue

        # Both changed
        if our_val == their_val:
            # Same change — no conflict
            if our_val is _SENTINEL:
                merged.pop(key, None)
            else:
                merged[key] = our_val
            continue

        # Conflict: both changed differently
        # If both are dicts, recurse
        if (
            isinstance(our_val, dict)
            and isinstance(their_val, dict)
            and isinstance(ancestor_val, dict)
        ):
            sub_result = merge_json(ancestor_val, our_val, their_val)
            merged[key] = sub_result.merged
            conflicts.extend(
                {**c, "parent_key": f"{key}.{c.get('key', '')}"} for c in sub_result.conflicts
            )
            continue

        # Irreconcilable conflict
        merged[key] = our_val if our_val is not _SENTINEL else their_val
        conflicts.append({
            "key": key,
            "ancestor": ancestor_val if ancestor_val is not _SENTINEL else None,
            "ours": our_val if our_val is not _SENTINEL else None,
            "theirs": their_val if their_val is not _SENTINEL else None,
        })

    return ConflictResult(
        merged=merged,
        conflicts=conflicts,
        is_clean=len(conflicts) == 0,
    )


def merge_markdown(
    ancestor: str,
    ours: str,
    theirs: str,
) -> ConflictResult:
    """Section-level merge for Markdown files.

    Splits by ``## `` headers and merges non-overlapping sections.
    Overlapping sections keep both with conflict markers.

    Parameters
    ----------
    ancestor:
        Common ancestor content.
    ours:
        Our version.
    theirs:
        Their version.
    """
    ancestor_sections = _split_sections(ancestor)
    our_sections = _split_sections(ours)
    their_sections = _split_sections(theirs)

    all_headers = []
    seen = set()
    for h in list(ancestor_sections) + list(our_sections) + list(their_sections):
        if h not in seen:
            all_headers.append(h)
            seen.add(h)

    merged_parts: list[str] = []
    conflicts: list[dict[str, Any]] = []

    for header in all_headers:
        a_text = ancestor_sections.get(header, "")
        o_text = our_sections.get(header, "")
        t_text = their_sections.get(header, "")

        o_changed = o_text != a_text
        t_changed = t_text != a_text

        if not o_changed and not t_changed:
            merged_parts.append(a_text)
        elif o_changed and not t_changed:
            merged_parts.append(o_text)
        elif t_changed and not o_changed:
            merged_parts.append(t_text)
        elif o_text == t_text:
            merged_parts.append(o_text)
        else:
            # Conflict: keep both with markers
            conflict_text = (
                f"<<<<<<< OURS\n{o_text}\n=======\n{t_text}\n>>>>>>> THEIRS"
            )
            merged_parts.append(conflict_text)
            conflicts.append({
                "section": header,
                "ours": o_text,
                "theirs": t_text,
            })

    merged_text = "\n\n".join(merged_parts)

    return ConflictResult(
        merged=merged_text,
        conflicts=conflicts,
        is_clean=len(conflicts) == 0,
    )


def merge_ifc_guids(
    our_guids: set[str],
    their_guids: set[str],
) -> ConflictResult:
    """GUID-based IFC merge — different GUIDs never conflict.

    Simply combines both sets of GUIDs.
    """
    merged = our_guids | their_guids
    return ConflictResult(merged=merged, conflicts=[], is_clean=True)


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown into sections keyed by header.

    Returns an OrderedDict-style dict of header -> content.
    """
    sections: dict[str, str] = {}
    current_header = "_preamble"
    current_lines: list[str] = []

    for line in text.split("\n"):
        if re.match(r"^#{1,3}\s+", line):
            # Save previous section
            sections[current_header] = "\n".join(current_lines).strip()
            current_header = line.strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Save last section
    sections[current_header] = "\n".join(current_lines).strip()

    # Remove empty preamble
    if "_preamble" in sections and not sections["_preamble"]:
        del sections["_preamble"]

    return sections


class _SentinelType:
    """Sentinel for distinguishing missing keys from None values."""
    def __repr__(self) -> str:
        return "<MISSING>"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _SentinelType)

    def __hash__(self) -> int:
        return hash("_SENTINEL")


_SENTINEL = _SentinelType()
