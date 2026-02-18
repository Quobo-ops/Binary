"""Pydantic models for the collaboration layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Comment(BaseModel):
    """An element-level threaded comment."""

    id: str = Field(default_factory=_new_id)
    element_id: str
    user: str
    text: str
    reply_to: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)

    def to_yaml_frontmatter(self) -> str:
        """Render YAML front-matter for Markdown file."""
        lines = [
            "---",
            f"id: {self.id}",
            f"element_id: {self.element_id}",
            f"author: {self.user}",
            f"timestamp: {self.created_at.isoformat()}",
        ]
        if self.reply_to:
            lines.append(f"reply_to: {self.reply_to}")
        lines.append("---")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Render full Markdown comment file content."""
        return f"{self.to_yaml_frontmatter()}\n\n{self.text}\n"


class Task(BaseModel):
    """A task assignment for collaboration."""

    id: str = Field(default_factory=_new_id)
    title: str
    assignee: str
    element_id: str = ""
    status: str = "open"
    """Status: 'open', 'in_progress', 'review', 'done'."""

    priority: str = "normal"
    """Priority: 'low', 'normal', 'high', 'urgent'."""

    created_at: datetime = Field(default_factory=_utc_now)
    due_date: Optional[datetime] = None


class Review(BaseModel):
    """An element review request."""

    id: str = Field(default_factory=_new_id)
    element_id: str
    reviewer: str
    status: str = "pending"
    """Status: 'pending', 'approved', 'rejected'."""

    requested_at: datetime = Field(default_factory=_utc_now)
    resolved_at: Optional[datetime] = None
    comments: str = ""
    requested_by: str = ""


class ActivityEvent(BaseModel):
    """An event in the activity feed."""

    id: str = Field(default_factory=_new_id)
    type: str
    """Event type: 'comment', 'task_created', 'task_completed',
    'review_requested', 'review_approved', 'review_rejected',
    'element_generated', 'element_validated', 'regulatory_update'."""

    user: str = ""
    element_id: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)
    summary: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
