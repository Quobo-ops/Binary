"""Branching strategy — create, switch, merge, and list branches.

Implements a simplified Gitflow variant optimised for AEC OS:
  - main: production-ready templates and tools
  - develop: integration branch
  - feature/*: short-lived feature branches
  - hotfix/*: urgent fixes
  - release/*: preparation for tagged releases
"""

from __future__ import annotations

import logging
from pathlib import Path

from aecos.vcs.repo import RepoManager, GitError, _run_git

logger = logging.getLogger(__name__)


def create_branch(
    repo: RepoManager,
    name: str,
    base: str | None = None,
) -> str:
    """Create a new branch and switch to it.

    Parameters
    ----------
    repo:
        The repository manager.
    name:
        Branch name (e.g. ``feature/add-steel-beam``).
    base:
        Base branch or commit.  Defaults to the current HEAD.

    Returns the name of the created branch.
    """
    args = ["checkout", "-b", name]
    if base is not None:
        args.append(base)

    _run_git(*args, cwd=repo.path)
    logger.info("Created and switched to branch '%s'", name)
    return name


def switch_branch(repo: RepoManager, name: str) -> str:
    """Switch to an existing branch.

    Returns the branch name.
    """
    _run_git("checkout", name, cwd=repo.path)
    logger.info("Switched to branch '%s'", name)
    return name


def merge_branch(
    repo: RepoManager,
    source: str,
    target: str | None = None,
    *,
    message: str | None = None,
) -> str:
    """Merge *source* into *target* (or the current branch).

    Parameters
    ----------
    source:
        Branch to merge from.
    target:
        Branch to merge into.  If *None*, merges into the current branch.
    message:
        Custom merge commit message.

    Returns the short hash of the resulting merge commit.
    """
    if target is not None:
        _run_git("checkout", target, cwd=repo.path)

    args = ["merge", source, "--no-ff"]
    if message:
        args += ["-m", message]

    _run_git(*args, cwd=repo.path)

    result = _run_git("rev-parse", "--short", "HEAD", cwd=repo.path)
    sha = result.stdout.strip()
    logger.info("Merged '%s' -> '%s' (%s)", source, target or "HEAD", sha)
    return sha


def list_branches(repo: RepoManager) -> list[str]:
    """Return the list of local branch names."""
    result = _run_git("branch", "--list", "--format=%(refname:short)", cwd=repo.path)
    return [b.strip() for b in result.stdout.splitlines() if b.strip()]


def delete_branch(repo: RepoManager, name: str) -> None:
    """Delete a local branch (must not be the current branch)."""
    _run_git("branch", "-d", name, cwd=repo.path)
    logger.info("Deleted branch '%s'", name)
