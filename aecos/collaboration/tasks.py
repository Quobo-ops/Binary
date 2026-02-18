"""TaskManager — task assignment and status tracking."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aecos.collaboration.models import Task

logger = logging.getLogger(__name__)


class TaskManager:
    """Manage task assignments stored in .aecos/tasks.json.

    Tasks are project-level and git-versioned via the flat JSON file.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._tasks_path = project_root / ".aecos" / "tasks.json"
        self._tasks_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_tasks(self) -> list[Task]:
        """Load tasks from disk."""
        if not self._tasks_path.is_file():
            return []
        try:
            data = json.loads(self._tasks_path.read_text(encoding="utf-8"))
            return [Task.model_validate(t) for t in data]
        except (json.JSONDecodeError, OSError):
            return []

    def _save_tasks(self, tasks: list[Task]) -> None:
        """Persist tasks to disk."""
        data = [t.model_dump(mode="json") for t in tasks]
        self._tasks_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create_task(
        self,
        title: str,
        assignee: str,
        element_id: str = "",
        due_date: datetime | None = None,
        priority: str = "normal",
    ) -> Task:
        """Create a new task.

        Parameters
        ----------
        title:
            Task title/description.
        assignee:
            User assigned to the task.
        element_id:
            Optional element this task relates to.
        due_date:
            Optional due date.
        priority:
            'low', 'normal', 'high', or 'urgent'.
        """
        task = Task(
            title=title,
            assignee=assignee,
            element_id=element_id,
            due_date=due_date,
            priority=priority,
        )

        tasks = self._load_tasks()
        tasks.append(task)
        self._save_tasks(tasks)

        logger.info("Created task %s: %s (assigned to %s)", task.id, title, assignee)
        return task

    def update_task(self, task_id: str, status: str) -> Task | None:
        """Update a task's status.

        Parameters
        ----------
        task_id:
            Task identifier.
        status:
            New status: 'open', 'in_progress', 'review', 'done'.
        """
        tasks = self._load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.status = status
                self._save_tasks(tasks)
                logger.info("Updated task %s status to %s", task_id, status)
                return task
        return None

    def get_tasks(
        self,
        assignee: str | None = None,
        status: str | None = None,
        element_id: str | None = None,
    ) -> list[Task]:
        """Get tasks with optional filtering.

        Parameters
        ----------
        assignee:
            Filter by assignee.
        status:
            Filter by status.
        element_id:
            Filter by related element.
        """
        tasks = self._load_tasks()
        result: list[Task] = []

        for task in tasks:
            if assignee and task.assignee != assignee:
                continue
            if status and task.status != status:
                continue
            if element_id and task.element_id != element_id:
                continue
            result.append(task)

        return result

    def get_task(self, task_id: str) -> Task | None:
        """Get a single task by ID."""
        tasks = self._load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None
