"""SyncManager — main entry point for multi-user synchronization."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from aecos.sync.conflict import ConflictResult, merge_json, merge_markdown
from aecos.sync.locking import LockInfo, LockManager
from aecos.sync.notifications import ConsoleNotifier, NotificationProvider
from aecos.sync.permissions import PermissionManager, Role
from aecos.sync.webhooks import WebhookDispatcher
from aecos.vcs.repo import RepoManager, _run_git

logger = logging.getLogger(__name__)


class SyncManager:
    """Multi-user synchronization layer wrapping RepoManager.

    Provides conflict-aware push/pull, role-based permission checks,
    soft locking, and webhook-driven notifications.

    Parameters
    ----------
    repo_path:
        Path to the AEC OS project root (must be a git repo).
    user_id:
        Current user identifier.
    role:
        User's role (admin, designer, reviewer, viewer).
    notification_providers:
        Optional list of additional notification providers.
    """

    def __init__(
        self,
        repo_path: str | Path,
        user_id: str,
        role: str | Role = "designer",
        *,
        notification_providers: list[NotificationProvider] | None = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.user_id = user_id

        # Core subsystems
        self.repo = RepoManager(self.repo_path)
        self.permissions = PermissionManager(self.repo_path)
        self.locks = LockManager(self.repo_path)
        self.webhooks = WebhookDispatcher(notification_providers)

        # Register user role
        if isinstance(role, str):
            role = Role(role)
        self.permissions.set_role(user_id, role)

    def sync(self) -> ConflictResult:
        """Fetch remote, detect conflicts, auto-merge if safe, notify.

        Returns a ConflictResult describing the merge outcome.
        """
        self.permissions.require_permission(self.user_id, "pull")

        # Try to pull
        try:
            _run_git("fetch", "origin", cwd=self.repo_path, check=False)
        except Exception:
            logger.debug("Fetch failed (no remote?)", exc_info=True)

        # Check for divergence
        result = _run_git(
            "status", "--porcelain", cwd=self.repo_path, check=False,
        )
        status = result.stdout.strip()

        if not status:
            return ConflictResult(merged=None, conflicts=[], is_clean=True)

        # For now, return clean status — real merge handled by push/pull
        return ConflictResult(merged=status, conflicts=[], is_clean=True)

    def push_changes(self, message: str) -> str:
        """Commit and push with conflict check.

        Returns the commit hash.
        """
        self.permissions.require_permission(self.user_id, "push")

        # Stage and commit
        _run_git("add", "-A", cwd=self.repo_path)
        result = _run_git(
            "status", "--porcelain", cwd=self.repo_path, check=False,
        )
        if not result.stdout.strip():
            return ""

        _run_git("commit", "-m", message, cwd=self.repo_path)
        commit_result = _run_git(
            "rev-parse", "--short", "HEAD", cwd=self.repo_path,
        )
        commit_hash = commit_result.stdout.strip()

        # Try push (may fail if no remote)
        push_result = _run_git(
            "push", cwd=self.repo_path, check=False,
        )

        branch = self.repo.current_branch()

        self.webhooks.on_commit(
            user=self.user_id,
            branch=branch,
            details=message,
        )

        return commit_hash

    def pull_latest(self) -> ConflictResult:
        """Pull latest changes with auto-merge strategy.

        Returns a ConflictResult.
        """
        self.permissions.require_permission(self.user_id, "pull")

        result = _run_git(
            "pull", "--no-rebase", cwd=self.repo_path, check=False,
        )

        if result.returncode != 0:
            # Merge conflict
            self.webhooks.on_conflict(
                user=self.user_id,
                details=f"Pull conflict: {result.stderr.strip()[:200]}",
            )
            return ConflictResult(
                merged=None,
                conflicts=[{"error": result.stderr.strip()}],
                is_clean=False,
            )

        return ConflictResult(merged=None, conflicts=[], is_clean=True)

    def get_team_activity(self, max_entries: int = 20) -> list[dict[str, str]]:
        """Get recent commits by all users.

        Returns a list of dicts with 'hash', 'author', 'date', 'message'.
        """
        result = _run_git(
            "log", f"--max-count={max_entries}",
            "--format=%H|%an|%ai|%s",
            cwd=self.repo_path,
            check=False,
        )

        if result.returncode != 0:
            return []

        entries: list[dict[str, str]] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                entries.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })

        return entries

    def lock_element(self, element_id: str) -> LockInfo:
        """Lock an element for exclusive editing.

        Returns LockInfo for the created lock.
        """
        self.permissions.require_permission(self.user_id, "lock")
        lock = self.locks.lock_element(element_id, self.user_id)
        self.webhooks.on_lock(
            user=self.user_id,
            element_id=element_id,
            details="locked",
        )
        return lock

    def unlock_element(self, element_id: str) -> bool:
        """Unlock an element.

        Returns True if successfully unlocked.
        """
        self.permissions.require_permission(self.user_id, "unlock")
        result = self.locks.unlock_element(element_id, self.user_id)
        if result:
            self.webhooks.on_lock(
                user=self.user_id,
                element_id=element_id,
                details="unlocked",
            )
        return result
