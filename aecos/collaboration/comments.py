"""CommentStore — element-level threaded comments stored as Markdown files."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aecos.collaboration.models import Comment

logger = logging.getLogger(__name__)


class CommentStore:
    """Store and retrieve element-level threaded comments.

    Comments are stored as individual .md files in
    ``<element_folder>/comments/`` with YAML front-matter.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def _comments_dir(self, element_id: str) -> Path:
        """Get the comments directory for an element."""
        # Look in elements/ first, then templates/
        for prefix in ("element_", "template_"):
            for parent in ("elements", "templates"):
                d = self.project_root / parent / f"{prefix}{element_id}" / "comments"
                base = self.project_root / parent / f"{prefix}{element_id}"
                if base.is_dir():
                    d.mkdir(parents=True, exist_ok=True)
                    return d

        # Default to elements/ if no match found
        d = self.project_root / "elements" / f"element_{element_id}" / "comments"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def add_comment(
        self,
        element_id: str,
        user: str,
        text: str,
        reply_to: str | None = None,
    ) -> Comment:
        """Add a comment to an element.

        Parameters
        ----------
        element_id:
            The element's GlobalId.
        user:
            Author of the comment.
        text:
            Comment body text.
        reply_to:
            Optional comment ID this is a reply to.

        Returns
        -------
        Comment
        """
        comment = Comment(
            element_id=element_id,
            user=user,
            text=text,
            reply_to=reply_to,
        )

        comments_dir = self._comments_dir(element_id)
        timestamp = comment.created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{comment.user}_{comment.id}.md"
        filepath = comments_dir / filename

        filepath.write_text(comment.to_markdown(), encoding="utf-8")
        logger.info("Added comment %s to element %s", comment.id, element_id)
        return comment

    def get_comments(self, element_id: str) -> list[Comment]:
        """Get all comments for an element, threaded and chronological.

        Returns
        -------
        list[Comment]
            Comments sorted by creation timestamp.
        """
        comments_dir = self._comments_dir(element_id)
        if not comments_dir.is_dir():
            return []

        comments: list[Comment] = []
        for md_file in sorted(comments_dir.glob("*.md")):
            try:
                comment = self._parse_comment_file(md_file, element_id)
                if comment:
                    comments.append(comment)
            except Exception:
                logger.debug("Failed to parse comment file %s", md_file, exc_info=True)

        return comments

    @staticmethod
    def _parse_comment_file(filepath: Path, element_id: str) -> Comment | None:
        """Parse a comment Markdown file with YAML front-matter."""
        content = filepath.read_text(encoding="utf-8")

        # Split YAML front-matter from body
        match = re.match(r"^---\n(.*?)\n---\n\n?(.*)", content, re.DOTALL)
        if not match:
            return None

        yaml_section = match.group(1)
        body = match.group(2).strip()

        # Parse YAML front-matter manually (avoid PyYAML dependency)
        fields: dict[str, str] = {}
        for line in yaml_section.split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()

        return Comment(
            id=fields.get("id", ""),
            element_id=fields.get("element_id", element_id),
            user=fields.get("author", ""),
            text=body,
            reply_to=fields.get("reply_to") or None,
            created_at=datetime.fromisoformat(fields["timestamp"]) if "timestamp" in fields else datetime.now(timezone.utc),
        )
