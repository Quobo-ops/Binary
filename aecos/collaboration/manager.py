"""CollaborationManager — main entry point for the collaboration layer."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from aecos.collaboration.activity import ActivityFeed
from aecos.collaboration.comments import CommentStore
from aecos.collaboration.models import ActivityEvent, Comment, Review, Task
from aecos.collaboration.providers.base import BotProvider
from aecos.collaboration.providers.console import ConsoleBotProvider
from aecos.collaboration.reviews import ReviewManager
from aecos.collaboration.tasks import TaskManager

logger = logging.getLogger(__name__)


class CollaborationManager:
    """Orchestrates comments, tasks, reviews, and the activity feed.

    Routes bot commands to the appropriate AecOS facade methods and
    dispatches notifications on all events.
    """

    def __init__(
        self,
        project_root: Path,
        aecos_facade: Any = None,
        bot_provider: BotProvider | None = None,
    ) -> None:
        self.project_root = project_root
        self._facade = aecos_facade

        self.comments = CommentStore(project_root)
        self.tasks = TaskManager(project_root)
        self.reviews = ReviewManager(project_root)
        self.activity = ActivityFeed(project_root)

        self.bot = bot_provider or ConsoleBotProvider(aecos_facade)

    # -- Comments -------------------------------------------------------------

    def add_comment(
        self,
        element_id: str,
        user: str,
        text: str,
        reply_to: str | None = None,
    ) -> Comment:
        """Add a comment to an element and log the event."""
        comment = self.comments.add_comment(element_id, user, text, reply_to)

        self.activity.record_event(ActivityEvent(
            type="comment",
            user=user,
            element_id=element_id,
            summary=f"{user} commented on {element_id}",
            details={"comment_id": comment.id, "reply_to": reply_to},
        ))

        return comment

    def get_comments(self, element_id: str) -> list[Comment]:
        """Get all comments for an element."""
        return self.comments.get_comments(element_id)

    # -- Tasks ----------------------------------------------------------------

    def create_task(
        self,
        title: str,
        assignee: str,
        element_id: str = "",
        due_date: datetime | None = None,
        priority: str = "normal",
    ) -> Task:
        """Create a task and log the event."""
        task = self.tasks.create_task(title, assignee, element_id, due_date, priority)

        self.activity.record_event(ActivityEvent(
            type="task_created",
            user=assignee,
            element_id=element_id,
            summary=f"Task created: {title} (assigned to {assignee})",
            details={"task_id": task.id, "priority": priority},
        ))

        return task

    def update_task(self, task_id: str, status: str) -> Task | None:
        """Update task status and log completion events."""
        task = self.tasks.update_task(task_id, status)
        if task and status == "done":
            self.activity.record_event(ActivityEvent(
                type="task_completed",
                user=task.assignee,
                element_id=task.element_id,
                summary=f"Task completed: {task.title}",
                details={"task_id": task.id},
            ))
        return task

    def get_tasks(
        self,
        assignee: str | None = None,
        status: str | None = None,
        element_id: str | None = None,
    ) -> list[Task]:
        """Get tasks with optional filtering."""
        return self.tasks.get_tasks(assignee, status, element_id)

    # -- Reviews --------------------------------------------------------------

    def request_review(
        self,
        element_id: str,
        reviewer: str,
        notes: str | None = None,
        requested_by: str = "",
    ) -> Review:
        """Request a review and log the event."""
        review = self.reviews.request_review(element_id, reviewer, notes, requested_by)

        self.activity.record_event(ActivityEvent(
            type="review_requested",
            user=requested_by or reviewer,
            element_id=element_id,
            summary=f"Review requested from {reviewer} for {element_id}",
            details={"review_id": review.id},
        ))

        return review

    def approve_review(
        self,
        review_id: str,
        reviewer: str,
        comments: str | None = None,
    ) -> Review | None:
        """Approve a review and log the event."""
        review = self.reviews.approve(review_id, reviewer, comments)
        if review:
            self.activity.record_event(ActivityEvent(
                type="review_approved",
                user=reviewer,
                element_id=review.element_id,
                summary=f"{reviewer} approved review for {review.element_id}",
                details={"review_id": review.id},
            ))
        return review

    def reject_review(
        self,
        review_id: str,
        reviewer: str,
        reason: str,
    ) -> Review | None:
        """Reject a review and log the event."""
        review = self.reviews.reject(review_id, reviewer, reason)
        if review:
            self.activity.record_event(ActivityEvent(
                type="review_rejected",
                user=reviewer,
                element_id=review.element_id,
                summary=f"{reviewer} rejected review for {review.element_id}: {reason}",
                details={"review_id": review.id, "reason": reason},
            ))
        return review

    def get_pending_reviews(self, reviewer: str | None = None) -> list[Review]:
        """Get pending reviews."""
        return self.reviews.get_pending_reviews(reviewer)

    # -- Activity Feed --------------------------------------------------------

    def get_activity_feed(
        self,
        since: datetime | None = None,
        user: str | None = None,
        element_id: str | None = None,
        limit: int = 50,
    ) -> list[ActivityEvent]:
        """Get the activity feed with optional filtering."""
        return self.activity.get_feed(since, user, element_id, limit=limit)

    # -- Bot Commands ---------------------------------------------------------

    def execute_command(self, text: str, user: str = "") -> str:
        """Execute a natural-language command via the bot provider.

        Parameters
        ----------
        text:
            Natural language command.
        user:
            User who sent the command.

        Returns
        -------
        str
            Formatted response text.
        """
        response = self.bot.handle_command(text, user=user)

        self.activity.record_event(ActivityEvent(
            type="element_generated",
            user=user,
            summary=f"Command executed: {text[:80]}",
            details={"command": text, "response_preview": response[:200]},
        ))

        return response
