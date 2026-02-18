"""Tests for Item 12 — Multi-User Sync."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from aecos.sync.conflict import ConflictResult, merge_json, merge_markdown, merge_ifc_guids
from aecos.sync.locking import LockInfo, LockManager
from aecos.sync.manager import SyncManager
from aecos.sync.notifications import ConsoleNotifier, SlackNotifier
from aecos.sync.permissions import PermissionError, PermissionManager, Role
from aecos.sync.webhooks import WebhookDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_git_user(repo_path: Path) -> None:
    """Configure git user in a temp repo for test commits."""
    subprocess.run(
        ["git", "config", "user.email", "test@aecos.test"],
        cwd=repo_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path, capture_output=True,
    )


def _init_git_repo(path: Path) -> Path:
    """Create a minimal git repository."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    _configure_git_user(path)

    # Initial commit
    (path / "README.md").write_text("# Test Project\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path, capture_output=True,
    )
    return path


def _make_element_folder(project_root: Path, element_id: str = "test001") -> Path:
    """Create a minimal element folder."""
    folder = project_root / "elements" / f"element_{element_id}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metadata.json").write_text(json.dumps({
        "GlobalId": element_id,
        "Name": "Test Element",
        "IFCClass": "IfcWall",
    }), encoding="utf-8")
    return folder


# ---------------------------------------------------------------------------
# JSON 3-way merge
# ---------------------------------------------------------------------------


class TestJSONMerge:
    def test_non_overlapping_changes_clean_merge(self):
        """Non-overlapping changes merge automatically."""
        ancestor = {"a": 1, "b": 2}
        ours = {"a": 10, "b": 2}       # changed a
        theirs = {"a": 1, "b": 20}     # changed b

        result = merge_json(ancestor, ours, theirs)

        assert result.is_clean
        assert result.merged == {"a": 10, "b": 20}
        assert len(result.conflicts) == 0

    def test_overlapping_changes_conflict(self):
        """Overlapping changes on same key flagged as conflict."""
        ancestor = {"a": 1, "b": 2}
        ours = {"a": 10, "b": 2}       # changed a to 10
        theirs = {"a": 99, "b": 2}     # changed a to 99

        result = merge_json(ancestor, ours, theirs)

        assert not result.is_clean
        assert len(result.conflicts) == 1
        assert result.conflicts[0]["key"] == "a"
        assert result.conflicts[0]["ours"] == 10
        assert result.conflicts[0]["theirs"] == 99

    def test_both_add_same_value(self):
        """Both sides add same key with same value -> no conflict."""
        ancestor = {"a": 1}
        ours = {"a": 1, "b": 2}
        theirs = {"a": 1, "b": 2}

        result = merge_json(ancestor, ours, theirs)
        assert result.is_clean
        assert result.merged == {"a": 1, "b": 2}

    def test_one_side_deletes_key(self):
        """One side deletes key, other doesn't change -> deleted."""
        ancestor = {"a": 1, "b": 2}
        ours = {"b": 2}  # deleted a
        theirs = {"a": 1, "b": 2}  # no change

        result = merge_json(ancestor, ours, theirs)
        assert result.is_clean
        assert "a" not in result.merged

    def test_nested_dict_merge(self):
        """Nested dicts are recursively merged."""
        ancestor = {"outer": {"a": 1, "b": 2}}
        ours = {"outer": {"a": 10, "b": 2}}
        theirs = {"outer": {"a": 1, "b": 20}}

        result = merge_json(ancestor, ours, theirs)
        assert result.is_clean
        assert result.merged["outer"] == {"a": 10, "b": 20}


# ---------------------------------------------------------------------------
# Markdown section merge
# ---------------------------------------------------------------------------


class TestMarkdownMerge:
    def test_different_sections_clean_merge(self):
        ancestor = "## A\nOriginal A\n\n## B\nOriginal B"
        ours = "## A\nModified A\n\n## B\nOriginal B"
        theirs = "## A\nOriginal A\n\n## B\nModified B"

        result = merge_markdown(ancestor, ours, theirs)
        assert result.is_clean
        assert "Modified A" in result.merged
        assert "Modified B" in result.merged

    def test_same_section_conflict(self):
        ancestor = "## A\nOriginal"
        ours = "## A\nOur version"
        theirs = "## A\nTheir version"

        result = merge_markdown(ancestor, ours, theirs)
        assert not result.is_clean
        assert len(result.conflicts) == 1
        assert "OURS" in result.merged
        assert "THEIRS" in result.merged


# ---------------------------------------------------------------------------
# IFC GUID merge
# ---------------------------------------------------------------------------


class TestIFCGUIDMerge:
    def test_guid_merge(self):
        ours = {"guid1", "guid2"}
        theirs = {"guid2", "guid3"}
        result = merge_ifc_guids(ours, theirs)
        assert result.is_clean
        assert result.merged == {"guid1", "guid2", "guid3"}


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


class TestPermissions:
    def test_designer_can_create(self, tmp_path: Path):
        pm = PermissionManager(tmp_path)
        pm.set_role("alice", Role.DESIGNER)
        assert pm.check_permission("alice", "create") is True

    def test_reviewer_cannot_modify(self, tmp_path: Path):
        pm = PermissionManager(tmp_path)
        pm.set_role("bob", Role.REVIEWER)
        assert pm.check_permission("bob", "modify") is False

    def test_viewer_read_only(self, tmp_path: Path):
        pm = PermissionManager(tmp_path)
        pm.set_role("carol", Role.VIEWER)
        assert pm.check_permission("carol", "read") is True
        assert pm.check_permission("carol", "create") is False
        assert pm.check_permission("carol", "delete") is False

    def test_admin_full_access(self, tmp_path: Path):
        pm = PermissionManager(tmp_path)
        pm.set_role("admin", Role.ADMIN)
        for action in ["create", "modify", "delete", "approve", "read", "push", "pull"]:
            assert pm.check_permission("admin", action) is True

    def test_require_permission_raises(self, tmp_path: Path):
        pm = PermissionManager(tmp_path)
        pm.set_role("viewer", Role.VIEWER)
        with pytest.raises(PermissionError):
            pm.require_permission("viewer", "create")

    def test_default_role_is_viewer(self, tmp_path: Path):
        pm = PermissionManager(tmp_path)
        role = pm.get_role("unknown_user")
        assert role == Role.VIEWER

    def test_persistence(self, tmp_path: Path):
        pm1 = PermissionManager(tmp_path)
        pm1.set_role("alice", Role.ADMIN)

        pm2 = PermissionManager(tmp_path)
        assert pm2.get_role("alice") == Role.ADMIN


# ---------------------------------------------------------------------------
# Soft locking
# ---------------------------------------------------------------------------


class TestLocking:
    def test_lock_and_is_locked(self, tmp_path: Path):
        (tmp_path / "elements" / "element_test1").mkdir(parents=True)
        lm = LockManager(tmp_path)
        lock = lm.lock_element("test1", "alice")

        assert lock.element_id == "test1"
        assert lock.user_id == "alice"

        result = lm.is_locked("test1")
        assert result is not None
        assert result.user_id == "alice"

    def test_unlock(self, tmp_path: Path):
        (tmp_path / "elements" / "element_test1").mkdir(parents=True)
        lm = LockManager(tmp_path)
        lm.lock_element("test1", "alice")
        lm.unlock_element("test1", "alice")

        assert lm.is_locked("test1") is None

    def test_lock_by_another_user_raises(self, tmp_path: Path):
        (tmp_path / "elements" / "element_test1").mkdir(parents=True)
        lm = LockManager(tmp_path)
        lm.lock_element("test1", "alice")

        with pytest.raises(RuntimeError, match="locked by"):
            lm.lock_element("test1", "bob")

    def test_stale_lock_expiry(self, tmp_path: Path):
        """Lock with past timestamp -> auto-expired."""
        (tmp_path / "elements" / "element_test1").mkdir(parents=True)
        lm = LockManager(tmp_path, timeout=1)  # 1 second timeout

        lock = lm.lock_element("test1", "alice")

        # Manually set timestamp to the past
        lock_path = tmp_path / "elements" / "element_test1" / ".lock"
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        data["timestamp"] = time.time() - 100  # 100 seconds ago
        data["timeout"] = 1
        lock_path.write_text(json.dumps(data), encoding="utf-8")

        # Should be expired now
        result = lm.is_locked("test1")
        assert result is None

    def test_not_locked_returns_none(self, tmp_path: Path):
        lm = LockManager(tmp_path)
        assert lm.is_locked("nonexistent") is None


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class TestNotifications:
    def test_console_notifier(self):
        notifier = ConsoleNotifier()
        assert notifier.is_available() is True

        event = {
            "type": "commit",
            "user": "alice",
            "element_id": "test1",
            "branch": "main",
            "timestamp": time.time(),
            "details": "Added wall",
        }
        assert notifier.notify(event) is True
        assert len(notifier.log) == 1
        assert notifier.log[0]["type"] == "commit"

    def test_slack_notifier_unavailable(self):
        """SlackNotifier without webhook URL is not available."""
        notifier = SlackNotifier()
        assert notifier.is_available() is False


class TestWebhookDispatcher:
    def test_dispatch_events(self):
        dispatcher = WebhookDispatcher()
        dispatcher.on_commit(user="alice", element_id="wall1", details="test")
        dispatcher.on_conflict(user="bob", details="conflict detected")
        dispatcher.on_lock(user="alice", element_id="wall1", details="locked")

        log = dispatcher.console.log
        assert len(log) == 3
        assert log[0]["type"] == "commit"
        assert log[1]["type"] == "conflict"
        assert log[2]["type"] == "lock"


# ---------------------------------------------------------------------------
# SyncManager integration tests
# ---------------------------------------------------------------------------


class TestSyncManager:
    def test_push_with_git_repo(self, tmp_path: Path):
        """SyncManager push with real git repo."""
        project_root = _init_git_repo(tmp_path / "project")
        (project_root / "elements").mkdir(exist_ok=True)

        mgr = SyncManager(project_root, "alice", "designer")

        # Create a file to commit
        (project_root / "test.txt").write_text("hello", encoding="utf-8")
        commit_hash = mgr.push_changes("test commit")

        assert commit_hash != ""

    def test_sync_clean_repo(self, tmp_path: Path):
        """Sync on clean repo returns clean result."""
        project_root = _init_git_repo(tmp_path / "project")
        (project_root / "elements").mkdir(exist_ok=True)

        mgr = SyncManager(project_root, "alice", "designer")
        result = mgr.sync()
        assert result.is_clean

    def test_team_activity(self, tmp_path: Path):
        """Team activity returns recent commits."""
        project_root = _init_git_repo(tmp_path / "project")
        (project_root / "elements").mkdir(exist_ok=True)

        mgr = SyncManager(project_root, "alice", "designer")
        activity = mgr.get_team_activity()

        assert len(activity) >= 1
        assert "hash" in activity[0]
        assert "author" in activity[0]
        assert "message" in activity[0]

    def test_lock_and_unlock_via_manager(self, tmp_path: Path):
        project_root = _init_git_repo(tmp_path / "project")
        _make_element_folder(project_root, "elem1")

        mgr = SyncManager(project_root, "alice", "designer")
        lock = mgr.lock_element("elem1")
        assert lock.user_id == "alice"

        mgr.unlock_element("elem1")
        assert mgr.locks.is_locked("elem1") is None

    def test_viewer_cannot_push(self, tmp_path: Path):
        """Viewer role cannot push changes."""
        project_root = _init_git_repo(tmp_path / "project")
        (project_root / "elements").mkdir(exist_ok=True)

        mgr = SyncManager(project_root, "viewer1", "viewer")
        with pytest.raises(PermissionError):
            mgr.push_changes("should fail")

    def test_pull_latest(self, tmp_path: Path):
        """Pull latest on a repo without remote returns clean."""
        project_root = _init_git_repo(tmp_path / "project")
        (project_root / "elements").mkdir(exist_ok=True)

        mgr = SyncManager(project_root, "alice", "designer")
        result = mgr.pull_latest()
        # Without a remote, pull may fail but should not crash
        assert isinstance(result, ConflictResult)
