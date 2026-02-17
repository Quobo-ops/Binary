"""Tests for the Version Control Backbone (Item 04).

All tests use tmp_path fixtures with real git repos (subprocess git).
Covers repo init, commit, branch, history, hooks, and diff.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aecos.vcs.branching import (
    create_branch,
    delete_branch,
    list_branches,
    merge_branch,
    switch_branch,
)
from aecos.vcs.commits import commit_all, commit_element, commit_template
from aecos.vcs.history import LogEntry, diff_element, get_element_history
from aecos.vcs.hooks import (
    install_default_pre_commit,
    install_hook,
    remove_hook,
)
from aecos.vcs.repo import GitError, RepoManager


# ---------------------------------------------------------------------------
# Helper: configure git user for tmp repos
# ---------------------------------------------------------------------------


def _configure_git_user(path: Path) -> None:
    """Set git user.name, user.email, and disable GPG signing in a temp repo."""
    subprocess.run(["git", "config", "user.email", "test@aecos.dev"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "AEC OS Test"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, capture_output=True)


def _init_git_repo(path: Path) -> None:
    """Create a git repo at *path* with one initial commit, signing disabled."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    _configure_git_user(path)
    (path / "init.txt").write_text("init")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True)


def _make_element_folder(root: Path, global_id: str = "ABC123") -> Path:
    """Create a minimal element folder matching Item 01 output format."""
    folder = root / f"element_{global_id}"
    folder.mkdir(parents=True, exist_ok=True)

    metadata = {
        "GlobalId": global_id,
        "Name": "TestWall",
        "IFCClass": "IfcWall",
        "ObjectType": "Standard Wall",
        "Tag": None,
        "Psets": {"Pset_WallCommon.IsExternal": True},
    }
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2))

    props_dir = folder / "properties"
    props_dir.mkdir()
    (props_dir / "psets.json").write_text(json.dumps({"Pset_WallCommon": {"IsExternal": True}}, indent=2))

    mat_dir = folder / "materials"
    mat_dir.mkdir()
    (mat_dir / "materials.json").write_text(json.dumps([{"name": "Concrete", "thickness": 200.0}], indent=2))

    geo_dir = folder / "geometry"
    geo_dir.mkdir()
    (geo_dir / "shape.json").write_text(json.dumps({"bounding_box": {}, "volume": None, "centroid": None}, indent=2))

    rel_dir = folder / "relationships"
    rel_dir.mkdir()
    (rel_dir / "spatial.json").write_text(json.dumps({"storey_name": "Level 1"}, indent=2))

    return folder


# ---------------------------------------------------------------------------
# RepoManager tests
# ---------------------------------------------------------------------------


class TestRepoManager:
    def test_init_repo(self, tmp_path: Path):
        repo = RepoManager(tmp_path / "myrepo")
        result = repo.init_repo()
        assert result == (tmp_path / "myrepo").resolve()
        assert (tmp_path / "myrepo" / ".gitignore").is_file()
        assert (tmp_path / "myrepo" / ".gitattributes").is_file()
        assert repo.is_repo()

    def test_is_repo_false_before_init(self, tmp_path: Path):
        repo = RepoManager(tmp_path / "repo")
        assert not repo.is_repo()

    def test_is_repo_true_after_git_init(self, tmp_path: Path):
        repo = RepoManager(tmp_path / "repo")
        (tmp_path / "repo").mkdir()
        subprocess.run(["git", "init"], cwd=tmp_path / "repo", capture_output=True)
        assert repo.is_repo()

    def test_status_clean_after_init(self, tmp_path: Path):
        repo = RepoManager(tmp_path / "repo")
        repo.init_repo()
        assert repo.is_clean()

    def test_status_dirty_with_changes(self, tmp_path: Path):
        repo = RepoManager(tmp_path / "repo")
        repo.init_repo()

        (tmp_path / "repo" / "test.txt").write_text("changed")
        assert not repo.is_clean()
        assert "test.txt" in repo.status()

    def test_current_branch(self, tmp_path: Path):
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, capture_output=True)
        _configure_git_user(repo_path)
        (repo_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, capture_output=True)

        repo = RepoManager(repo_path)
        assert repo.current_branch() == "main"

    def test_stage_and_commit(self, tmp_path: Path):
        repo = RepoManager(tmp_path / "repo")
        repo.init_repo()

        (tmp_path / "repo" / "file.txt").write_text("content")
        repo.stage("file.txt")
        sha = repo.commit("test commit")
        assert len(sha) >= 7
        assert repo.is_clean()


# ---------------------------------------------------------------------------
# Commit helpers tests
# ---------------------------------------------------------------------------


class TestCommitHelpers:
    @pytest.fixture()
    def git_repo(self, tmp_path: Path) -> RepoManager:
        """Create an initialised git repo with one commit."""
        repo = RepoManager(tmp_path / "repo")
        repo.init_repo()
        return repo

    def test_commit_element(self, git_repo: RepoManager):
        folder = _make_element_folder(git_repo.path, "ELEM01")
        sha = commit_element(git_repo, folder)
        assert len(sha) >= 7
        assert git_repo.is_clean()

    def test_commit_element_auto_message(self, git_repo: RepoManager):
        folder = _make_element_folder(git_repo.path, "ELEM02")
        commit_element(git_repo, folder)

        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=git_repo.path, capture_output=True, text=True,
        )
        assert "element_ELEM02" in result.stdout

    def test_commit_element_custom_message(self, git_repo: RepoManager):
        folder = _make_element_folder(git_repo.path, "ELEM03")
        commit_element(git_repo, folder, message="custom msg")

        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=git_repo.path, capture_output=True, text=True,
        )
        assert "custom msg" in result.stdout

    def test_commit_template(self, git_repo: RepoManager):
        folder = git_repo.path / "template_T1"
        folder.mkdir()
        (folder / "manifest.json").write_text('{"id": "T1"}')
        sha = commit_template(git_repo, folder)
        assert len(sha) >= 7

    def test_commit_all(self, git_repo: RepoManager):
        (git_repo.path / "new_file.txt").write_text("data")
        sha = commit_all(git_repo, "commit all changes")
        assert len(sha) >= 7
        assert git_repo.is_clean()

    def test_commit_all_clean_tree(self, git_repo: RepoManager):
        sha = commit_all(git_repo, "nothing to commit")
        assert sha == ""


# ---------------------------------------------------------------------------
# Branching tests
# ---------------------------------------------------------------------------


class TestBranching:
    @pytest.fixture()
    def git_repo(self, tmp_path: Path) -> RepoManager:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_path, capture_output=True)
        _configure_git_user(repo_path)
        (repo_path / "init.txt").write_text("init")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, capture_output=True)
        return RepoManager(repo_path)

    def test_create_branch(self, git_repo: RepoManager):
        create_branch(git_repo, "feature/new-wall")
        assert git_repo.current_branch() == "feature/new-wall"

    def test_create_branch_from_base(self, git_repo: RepoManager):
        create_branch(git_repo, "feature/test", base="main")
        assert git_repo.current_branch() == "feature/test"

    def test_switch_branch(self, git_repo: RepoManager):
        create_branch(git_repo, "develop")
        switch_branch(git_repo, "main")
        assert git_repo.current_branch() == "main"
        switch_branch(git_repo, "develop")
        assert git_repo.current_branch() == "develop"

    def test_list_branches(self, git_repo: RepoManager):
        create_branch(git_repo, "develop")
        switch_branch(git_repo, "main")
        create_branch(git_repo, "feature/x")
        switch_branch(git_repo, "main")

        branches = list_branches(git_repo)
        assert "main" in branches
        assert "develop" in branches
        assert "feature/x" in branches

    def test_merge_branch(self, git_repo: RepoManager):
        create_branch(git_repo, "feature/merge-test")

        (git_repo.path / "feature.txt").write_text("feature work")
        subprocess.run(["git", "add", "."], cwd=git_repo.path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feature work"],
            cwd=git_repo.path, capture_output=True,
        )

        sha = merge_branch(git_repo, "feature/merge-test", "main")
        assert len(sha) >= 7
        assert git_repo.current_branch() == "main"
        assert (git_repo.path / "feature.txt").is_file()

    def test_delete_branch(self, git_repo: RepoManager):
        create_branch(git_repo, "temp-branch")
        switch_branch(git_repo, "main")
        delete_branch(git_repo, "temp-branch")
        assert "temp-branch" not in list_branches(git_repo)


# ---------------------------------------------------------------------------
# History tests
# ---------------------------------------------------------------------------


class TestHistory:
    @pytest.fixture()
    def git_repo(self, tmp_path: Path) -> RepoManager:
        repo = RepoManager(tmp_path / "repo")
        repo.init_repo()
        return repo

    def test_get_element_history(self, git_repo: RepoManager):
        folder = _make_element_folder(git_repo.path, "HIST01")
        commit_element(git_repo, folder, message="first commit")

        (folder / "metadata.json").write_text(
            json.dumps({"GlobalId": "HIST01", "Name": "Updated", "IFCClass": "IfcWall"}, indent=2)
        )
        commit_element(git_repo, folder, message="update element")

        history = get_element_history(git_repo, folder)
        assert len(history) == 2
        assert isinstance(history[0], LogEntry)
        assert history[0].message == "update element"
        assert history[1].message == "first commit"

    def test_element_history_filtered(self, git_repo: RepoManager):
        """History for one element excludes commits to other elements."""
        folder_a = _make_element_folder(git_repo.path, "A001")
        commit_element(git_repo, folder_a, message="commit A")

        folder_b = _make_element_folder(git_repo.path, "B001")
        commit_element(git_repo, folder_b, message="commit B")

        history_a = get_element_history(git_repo, folder_a)
        assert len(history_a) == 1
        assert history_a[0].message == "commit A"

    def test_diff_element(self, git_repo: RepoManager):
        folder = _make_element_folder(git_repo.path, "DIFF01")
        commit_element(git_repo, folder, message="initial")

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo.path, capture_output=True, text=True,
        )
        rev1 = result.stdout.strip()

        (folder / "metadata.json").write_text(
            json.dumps({"GlobalId": "DIFF01", "Name": "Changed", "IFCClass": "IfcWall"}, indent=2)
        )
        commit_element(git_repo, folder, message="modify")

        diff = diff_element(git_repo, folder, rev1)
        assert "Changed" in diff
        assert "TestWall" in diff

    def test_empty_history(self, git_repo: RepoManager):
        folder = git_repo.path / "element_NOHISTORY"
        folder.mkdir()
        history = get_element_history(git_repo, folder)
        assert history == []


# ---------------------------------------------------------------------------
# Hook tests
# ---------------------------------------------------------------------------


class TestHooks:
    @pytest.fixture()
    def git_repo(self, tmp_path: Path) -> Path:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        _configure_git_user(repo_path)
        (repo_path / "init.txt").write_text("init")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_path, capture_output=True)
        return repo_path

    def test_install_hook(self, git_repo: Path):
        script = "#!/bin/sh\necho 'hook ran'\n"
        hook_path = install_hook(git_repo, "post-commit", script)
        assert hook_path.is_file()
        assert "hook ran" in hook_path.read_text()

    def test_hook_is_executable(self, git_repo: Path):
        import stat

        script = "#!/bin/sh\necho 'test'\n"
        hook_path = install_hook(git_repo, "pre-push", script)
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IEXEC

    def test_install_default_pre_commit(self, git_repo: Path):
        hook_path = install_default_pre_commit(git_repo)
        assert hook_path.is_file()
        content = hook_path.read_text()
        assert "validate_json" in content
        assert "metadata.json" in content

    def test_pre_commit_validates_json(self, git_repo: Path):
        """Default pre-commit hook rejects invalid JSON."""
        install_default_pre_commit(git_repo)

        (git_repo / "bad.json").write_text("{invalid json")
        subprocess.run(["git", "add", "bad.json"], cwd=git_repo, capture_output=True)

        result = subprocess.run(
            ["git", "commit", "-m", "bad json"],
            cwd=git_repo, capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_pre_commit_validates_metadata_schema(self, git_repo: Path):
        """Default pre-commit hook rejects metadata.json missing required keys."""
        install_default_pre_commit(git_repo)

        elem_dir = git_repo / "element_X"
        elem_dir.mkdir()
        (elem_dir / "metadata.json").write_text('{"Name": "test"}')
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)

        result = subprocess.run(
            ["git", "commit", "-m", "bad metadata"],
            cwd=git_repo, capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_pre_commit_passes_valid_json(self, git_repo: Path):
        """Default pre-commit hook accepts valid JSON and metadata."""
        install_default_pre_commit(git_repo)

        elem_dir = git_repo / "element_Y"
        elem_dir.mkdir()
        (elem_dir / "metadata.json").write_text(
            json.dumps({"GlobalId": "Y", "IFCClass": "IfcWall", "Name": "Wall"})
        )
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)

        result = subprocess.run(
            ["git", "commit", "-m", "valid metadata"],
            cwd=git_repo, capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_remove_hook(self, git_repo: Path):
        install_hook(git_repo, "pre-commit", "#!/bin/sh\n")
        assert remove_hook(git_repo, "pre-commit") is True
        assert not (git_repo / ".git" / "hooks" / "pre-commit").is_file()

    def test_remove_hook_missing(self, git_repo: Path):
        assert remove_hook(git_repo, "nonexistent") is False
