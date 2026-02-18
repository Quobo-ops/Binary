"""Tests for Item 16 — Collaboration Layer.

Covers: Comment, Task, Review, ActivityEvent models, CommentStore,
TaskManager, ReviewManager, ActivityFeed, CollaborationManager,
and bot providers (Console, Slack, Teams).

All tests run offline with zero network access.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aecos.collaboration.activity import ActivityFeed
from aecos.collaboration.comments import CommentStore
from aecos.collaboration.manager import CollaborationManager
from aecos.collaboration.models import ActivityEvent, Comment, Review, Task
from aecos.collaboration.providers.base import BotProvider
from aecos.collaboration.providers.console import ConsoleBotProvider
from aecos.collaboration.providers.slack import SlackBotProvider
from aecos.collaboration.providers.teams import TeamsBotProvider
from aecos.collaboration.reviews import ReviewManager
from aecos.collaboration.tasks import TaskManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a minimal project structure."""
    (tmp_path / "elements").mkdir()
    (tmp_path / ".aecos").mkdir()
    return tmp_path


@pytest.fixture
def comment_store(project: Path) -> CommentStore:
    return CommentStore(project)


@pytest.fixture
def task_manager(project: Path) -> TaskManager:
    return TaskManager(project)


@pytest.fixture
def review_manager(project: Path) -> ReviewManager:
    return ReviewManager(project)


@pytest.fixture
def activity_feed(project: Path) -> ActivityFeed:
    return ActivityFeed(project)


@pytest.fixture
def collab_manager(project: Path) -> CollaborationManager:
    return CollaborationManager(project)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestCommentModel:
    def test_defaults(self) -> None:
        c = Comment(element_id="E1", user="alice", text="Hello")
        assert c.id != ""
        assert c.element_id == "E1"
        assert c.user == "alice"
        assert c.reply_to is None
        assert c.created_at is not None

    def test_yaml_frontmatter(self) -> None:
        c = Comment(element_id="E1", user="alice", text="Hello")
        fm = c.to_yaml_frontmatter()
        assert "---" in fm
        assert "author: alice" in fm
        assert "element_id: E1" in fm

    def test_to_markdown(self) -> None:
        c = Comment(element_id="E1", user="alice", text="Hello world")
        md = c.to_markdown()
        assert "---" in md
        assert "Hello world" in md

    def test_reply_to_in_frontmatter(self) -> None:
        c = Comment(element_id="E1", user="bob", text="Reply", reply_to="abc123")
        fm = c.to_yaml_frontmatter()
        assert "reply_to: abc123" in fm


class TestTaskModel:
    def test_defaults(self) -> None:
        t = Task(title="Fix wall", assignee="alice")
        assert t.id != ""
        assert t.status == "open"
        assert t.priority == "normal"
        assert t.element_id == ""

    def test_custom_priority(self) -> None:
        t = Task(title="Urgent fix", assignee="bob", priority="urgent")
        assert t.priority == "urgent"


class TestReviewModel:
    def test_defaults(self) -> None:
        r = Review(element_id="E1", reviewer="charlie")
        assert r.id != ""
        assert r.status == "pending"
        assert r.resolved_at is None

    def test_requested_by(self) -> None:
        r = Review(element_id="E1", reviewer="charlie", requested_by="alice")
        assert r.requested_by == "alice"


class TestActivityEventModel:
    def test_defaults(self) -> None:
        e = ActivityEvent(type="comment", user="alice", summary="Test")
        assert e.id != ""
        assert e.timestamp is not None
        assert e.details == {}


# ---------------------------------------------------------------------------
# CommentStore
# ---------------------------------------------------------------------------


class TestCommentStore:
    def test_add_comment(self, comment_store: CommentStore) -> None:
        c = comment_store.add_comment("E1", "alice", "Hello")
        assert isinstance(c, Comment)
        assert c.element_id == "E1"
        assert c.user == "alice"

    def test_get_comments_empty(self, comment_store: CommentStore) -> None:
        comments = comment_store.get_comments("NONEXIST")
        assert comments == []

    def test_get_comments_round_trip(self, comment_store: CommentStore) -> None:
        comment_store.add_comment("E1", "alice", "First comment")
        comment_store.add_comment("E1", "bob", "Second comment")
        comments = comment_store.get_comments("E1")
        assert len(comments) == 2
        texts = [c.text for c in comments]
        assert "First comment" in texts
        assert "Second comment" in texts

    def test_comment_stored_as_md(self, comment_store: CommentStore, project: Path) -> None:
        comment_store.add_comment("E1", "alice", "Test content")
        # Find the comment file
        comments_dir = project / "elements" / "element_E1" / "comments"
        md_files = list(comments_dir.glob("*.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text()
        assert "---" in content
        assert "Test content" in content

    def test_threaded_reply(self, comment_store: CommentStore) -> None:
        parent = comment_store.add_comment("E1", "alice", "Initial question")
        reply = comment_store.add_comment("E1", "bob", "Reply", reply_to=parent.id)
        assert reply.reply_to == parent.id

        comments = comment_store.get_comments("E1")
        assert len(comments) == 2
        reply_comment = [c for c in comments if c.reply_to is not None][0]
        assert reply_comment.reply_to == parent.id


# ---------------------------------------------------------------------------
# TaskManager
# ---------------------------------------------------------------------------


class TestTaskManager:
    def test_create_task(self, task_manager: TaskManager) -> None:
        task = task_manager.create_task("Fix wall height", "alice")
        assert isinstance(task, Task)
        assert task.title == "Fix wall height"
        assert task.assignee == "alice"
        assert task.status == "open"

    def test_update_task(self, task_manager: TaskManager) -> None:
        task = task_manager.create_task("Fix wall", "alice")
        updated = task_manager.update_task(task.id, "done")
        assert updated is not None
        assert updated.status == "done"

    def test_update_nonexistent_task(self, task_manager: TaskManager) -> None:
        result = task_manager.update_task("nonexistent", "done")
        assert result is None

    def test_get_tasks_all(self, task_manager: TaskManager) -> None:
        task_manager.create_task("Task 1", "alice")
        task_manager.create_task("Task 2", "bob")
        tasks = task_manager.get_tasks()
        assert len(tasks) == 2

    def test_filter_by_assignee(self, task_manager: TaskManager) -> None:
        task_manager.create_task("Task 1", "alice")
        task_manager.create_task("Task 2", "bob")
        alice_tasks = task_manager.get_tasks(assignee="alice")
        assert len(alice_tasks) == 1
        assert alice_tasks[0].assignee == "alice"

    def test_filter_by_status(self, task_manager: TaskManager) -> None:
        t1 = task_manager.create_task("Task 1", "alice")
        task_manager.create_task("Task 2", "bob")
        task_manager.update_task(t1.id, "done")
        done_tasks = task_manager.get_tasks(status="done")
        assert len(done_tasks) == 1

    def test_filter_by_element(self, task_manager: TaskManager) -> None:
        task_manager.create_task("Task 1", "alice", element_id="E1")
        task_manager.create_task("Task 2", "bob", element_id="E2")
        e1_tasks = task_manager.get_tasks(element_id="E1")
        assert len(e1_tasks) == 1

    def test_get_task_by_id(self, task_manager: TaskManager) -> None:
        task = task_manager.create_task("Test", "alice")
        retrieved = task_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    def test_persistence(self, project: Path) -> None:
        """Tasks survive across TaskManager instances."""
        mgr1 = TaskManager(project)
        mgr1.create_task("Persistent task", "alice")

        mgr2 = TaskManager(project)
        tasks = mgr2.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Persistent task"


# ---------------------------------------------------------------------------
# ReviewManager
# ---------------------------------------------------------------------------


class TestReviewManager:
    def test_request_review(self, review_manager: ReviewManager) -> None:
        review = review_manager.request_review("E1", "charlie")
        assert isinstance(review, Review)
        assert review.element_id == "E1"
        assert review.reviewer == "charlie"
        assert review.status == "pending"

    def test_approve_review(self, review_manager: ReviewManager) -> None:
        review = review_manager.request_review("E1", "charlie")
        approved = review_manager.approve(review.id, "charlie", "Looks good")
        assert approved is not None
        assert approved.status == "approved"
        assert approved.resolved_at is not None

    def test_reject_review(self, review_manager: ReviewManager) -> None:
        review = review_manager.request_review("E1", "charlie")
        rejected = review_manager.reject(review.id, "charlie", "Needs more work")
        assert rejected is not None
        assert rejected.status == "rejected"
        assert rejected.comments == "Needs more work"

    def test_approve_nonexistent(self, review_manager: ReviewManager) -> None:
        result = review_manager.approve("nonexistent", "charlie")
        assert result is None

    def test_reject_nonexistent(self, review_manager: ReviewManager) -> None:
        result = review_manager.reject("nonexistent", "charlie", "reason")
        assert result is None

    def test_get_pending_reviews(self, review_manager: ReviewManager) -> None:
        review_manager.request_review("E1", "charlie")
        review_manager.request_review("E2", "alice")
        pending = review_manager.get_pending_reviews()
        assert len(pending) == 2

    def test_filter_pending_by_reviewer(self, review_manager: ReviewManager) -> None:
        review_manager.request_review("E1", "charlie")
        review_manager.request_review("E2", "alice")
        charlie_pending = review_manager.get_pending_reviews(reviewer="charlie")
        assert len(charlie_pending) == 1
        assert charlie_pending[0].reviewer == "charlie"

    def test_approved_not_pending(self, review_manager: ReviewManager) -> None:
        review = review_manager.request_review("E1", "charlie")
        review_manager.approve(review.id, "charlie")
        pending = review_manager.get_pending_reviews()
        assert len(pending) == 0

    def test_persistence(self, project: Path) -> None:
        """Reviews survive across ReviewManager instances."""
        mgr1 = ReviewManager(project)
        mgr1.request_review("E1", "charlie")

        mgr2 = ReviewManager(project)
        pending = mgr2.get_pending_reviews()
        assert len(pending) == 1


# ---------------------------------------------------------------------------
# ActivityFeed
# ---------------------------------------------------------------------------


class TestActivityFeed:
    def test_record_event(self, activity_feed: ActivityFeed) -> None:
        event = ActivityEvent(type="comment", user="alice", summary="Test")
        activity_feed.record_event(event)
        feed = activity_feed.get_feed()
        assert len(feed) == 1
        assert feed[0].type == "comment"

    def test_multiple_events(self, activity_feed: ActivityFeed) -> None:
        for i in range(5):
            activity_feed.record_event(
                ActivityEvent(type="comment", user="alice", summary=f"Event {i}")
            )
        feed = activity_feed.get_feed()
        assert len(feed) == 5

    def test_filter_by_user(self, activity_feed: ActivityFeed) -> None:
        activity_feed.record_event(ActivityEvent(type="comment", user="alice", summary="A"))
        activity_feed.record_event(ActivityEvent(type="comment", user="bob", summary="B"))
        feed = activity_feed.get_feed(user="alice")
        assert len(feed) == 1
        assert feed[0].user == "alice"

    def test_filter_by_element(self, activity_feed: ActivityFeed) -> None:
        activity_feed.record_event(ActivityEvent(type="comment", element_id="E1", summary="A"))
        activity_feed.record_event(ActivityEvent(type="comment", element_id="E2", summary="B"))
        feed = activity_feed.get_feed(element_id="E1")
        assert len(feed) == 1

    def test_limit(self, activity_feed: ActivityFeed) -> None:
        for i in range(10):
            activity_feed.record_event(
                ActivityEvent(type="comment", user="alice", summary=f"Event {i}")
            )
        feed = activity_feed.get_feed(limit=3)
        assert len(feed) == 3

    def test_jsonl_format(self, activity_feed: ActivityFeed, project: Path) -> None:
        """Activity feed stored as JSONL."""
        activity_feed.record_event(ActivityEvent(type="comment", summary="Test"))
        feed_path = project / ".aecos" / "activity.jsonl"
        assert feed_path.is_file()
        lines = feed_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["type"] == "comment"

    def test_empty_feed(self, activity_feed: ActivityFeed) -> None:
        feed = activity_feed.get_feed()
        assert feed == []


# ---------------------------------------------------------------------------
# Bot Providers
# ---------------------------------------------------------------------------


class TestConsoleBotProvider:
    def test_is_bot_provider(self) -> None:
        bot = ConsoleBotProvider()
        assert isinstance(bot, BotProvider)

    def test_name(self) -> None:
        bot = ConsoleBotProvider()
        assert bot.name == "console"

    def test_is_available(self) -> None:
        bot = ConsoleBotProvider()
        assert bot.is_available() is True

    def test_send_message(self) -> None:
        bot = ConsoleBotProvider()
        assert bot.send_message("Hello") is True

    def test_handle_command_no_facade(self) -> None:
        bot = ConsoleBotProvider()
        result = bot.handle_command("test command", user="alice")
        assert isinstance(result, str)
        assert "alice" in result

    def test_handle_command_with_facade(self) -> None:
        """When facade is provided, commands are routed through NL parser."""
        # Minimal mock
        class MockFacade:
            def parse(self, text):
                from aecos.nlp.schema import ParametricSpec
                return ParametricSpec(
                    ifc_class="IfcWall",
                    intent="create",
                    confidence=0.8,
                )
        bot = ConsoleBotProvider(aecos_facade=MockFacade())
        result = bot.handle_command("add a concrete wall", user="alice")
        assert "IfcWall" in result
        assert "alice" in result


class TestSlackBotProvider:
    def test_is_bot_provider(self) -> None:
        bot = SlackBotProvider()
        assert isinstance(bot, BotProvider)

    def test_name(self) -> None:
        bot = SlackBotProvider()
        assert bot.name == "slack"

    def test_fallback_without_sdk(self) -> None:
        """Without slack-bolt installed, falls back to console."""
        bot = SlackBotProvider()
        # In test environment, slack-bolt is not installed
        result = bot.handle_command("test", user="alice")
        assert isinstance(result, str)


class TestTeamsBotProvider:
    def test_is_bot_provider(self) -> None:
        bot = TeamsBotProvider()
        assert isinstance(bot, BotProvider)

    def test_name(self) -> None:
        bot = TeamsBotProvider()
        assert bot.name == "teams"

    def test_fallback_without_sdk(self) -> None:
        """Without botbuilder-core installed, falls back to console."""
        bot = TeamsBotProvider()
        result = bot.handle_command("test", user="alice")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# CollaborationManager — integration
# ---------------------------------------------------------------------------


class TestCollaborationManager:
    def test_add_comment(self, collab_manager: CollaborationManager) -> None:
        comment = collab_manager.add_comment("E1", "alice", "Hello")
        assert isinstance(comment, Comment)

    def test_add_comment_logs_activity(self, collab_manager: CollaborationManager) -> None:
        collab_manager.add_comment("E1", "alice", "Hello")
        feed = collab_manager.get_activity_feed()
        assert len(feed) >= 1
        types = [e.type for e in feed]
        assert "comment" in types

    def test_create_task(self, collab_manager: CollaborationManager) -> None:
        task = collab_manager.create_task("Fix issue", "alice")
        assert isinstance(task, Task)
        assert task.status == "open"

    def test_create_task_logs_activity(self, collab_manager: CollaborationManager) -> None:
        collab_manager.create_task("Fix issue", "alice")
        feed = collab_manager.get_activity_feed()
        types = [e.type for e in feed]
        assert "task_created" in types

    def test_update_task_done_logs_completion(self, collab_manager: CollaborationManager) -> None:
        task = collab_manager.create_task("Fix issue", "alice")
        collab_manager.update_task(task.id, "done")
        feed = collab_manager.get_activity_feed()
        types = [e.type for e in feed]
        assert "task_completed" in types

    def test_get_tasks(self, collab_manager: CollaborationManager) -> None:
        collab_manager.create_task("Task 1", "alice")
        collab_manager.create_task("Task 2", "bob")
        tasks = collab_manager.get_tasks()
        assert len(tasks) == 2

    def test_request_review(self, collab_manager: CollaborationManager) -> None:
        review = collab_manager.request_review("E1", "charlie")
        assert isinstance(review, Review)
        assert review.status == "pending"

    def test_request_review_logs_activity(self, collab_manager: CollaborationManager) -> None:
        collab_manager.request_review("E1", "charlie")
        feed = collab_manager.get_activity_feed()
        types = [e.type for e in feed]
        assert "review_requested" in types

    def test_approve_review(self, collab_manager: CollaborationManager) -> None:
        review = collab_manager.request_review("E1", "charlie")
        approved = collab_manager.approve_review(review.id, "charlie")
        assert approved is not None
        assert approved.status == "approved"

    def test_approve_review_logs_activity(self, collab_manager: CollaborationManager) -> None:
        review = collab_manager.request_review("E1", "charlie")
        collab_manager.approve_review(review.id, "charlie")
        feed = collab_manager.get_activity_feed()
        types = [e.type for e in feed]
        assert "review_approved" in types

    def test_reject_review(self, collab_manager: CollaborationManager) -> None:
        review = collab_manager.request_review("E1", "charlie")
        rejected = collab_manager.reject_review(review.id, "charlie", "Not ready")
        assert rejected is not None
        assert rejected.status == "rejected"

    def test_reject_review_logs_activity(self, collab_manager: CollaborationManager) -> None:
        review = collab_manager.request_review("E1", "charlie")
        collab_manager.reject_review(review.id, "charlie", "Not ready")
        feed = collab_manager.get_activity_feed()
        types = [e.type for e in feed]
        assert "review_rejected" in types

    def test_get_pending_reviews(self, collab_manager: CollaborationManager) -> None:
        collab_manager.request_review("E1", "charlie")
        collab_manager.request_review("E2", "alice")
        pending = collab_manager.get_pending_reviews()
        assert len(pending) == 2

    def test_execute_command(self, collab_manager: CollaborationManager) -> None:
        result = collab_manager.execute_command("test command", user="alice")
        assert isinstance(result, str)

    def test_execute_command_logs_activity(self, collab_manager: CollaborationManager) -> None:
        collab_manager.execute_command("test command", user="alice")
        feed = collab_manager.get_activity_feed()
        types = [e.type for e in feed]
        assert "element_generated" in types

    def test_get_activity_feed(self, collab_manager: CollaborationManager) -> None:
        collab_manager.add_comment("E1", "alice", "Comment")
        collab_manager.create_task("Task", "bob")
        feed = collab_manager.get_activity_feed()
        assert len(feed) >= 2

    def test_activity_feed_ordered_newest_first(
        self, collab_manager: CollaborationManager
    ) -> None:
        collab_manager.add_comment("E1", "alice", "First")
        collab_manager.create_task("Second", "bob")
        feed = collab_manager.get_activity_feed()
        if len(feed) >= 2:
            assert feed[0].timestamp >= feed[1].timestamp
