"""Commit helpers — atomic commits of element and template folders.

Each function stages only the target folder and creates a single commit,
ensuring that element-level history is clean and traceable.
"""

from __future__ import annotations

import logging
from pathlib import Path

from aecos.vcs.repo import RepoManager, _run_git

logger = logging.getLogger(__name__)


def commit_element(
    repo: RepoManager,
    element_folder: str | Path,
    message: str | None = None,
) -> str:
    """Stage and commit a single element folder atomically.

    Parameters
    ----------
    repo:
        The repository manager.
    element_folder:
        Path to the element folder (absolute or relative to repo root).
    message:
        Commit message.  Auto-generated from the folder name if *None*.

    Returns
    -------
    str
        The short commit hash.
    """
    element_folder = Path(element_folder)
    folder_name = element_folder.name

    if message is None:
        message = f"feat: add element {folder_name}"

    # Make path relative to repo root for git add
    try:
        rel_path = element_folder.resolve().relative_to(repo.path)
    except ValueError:
        rel_path = element_folder

    _run_git("add", "--", str(rel_path), cwd=repo.path)
    _run_git("commit", "-m", message, cwd=repo.path)

    result = _run_git("rev-parse", "--short", "HEAD", cwd=repo.path)
    sha = result.stdout.strip()

    logger.info("Committed element %s (%s)", folder_name, sha)
    return sha


def commit_template(
    repo: RepoManager,
    template_folder: str | Path,
    message: str | None = None,
) -> str:
    """Stage and commit a single template folder atomically.

    Parameters
    ----------
    repo:
        The repository manager.
    template_folder:
        Path to the template folder.
    message:
        Commit message.  Auto-generated from the folder name if *None*.

    Returns
    -------
    str
        The short commit hash.
    """
    template_folder = Path(template_folder)
    folder_name = template_folder.name

    if message is None:
        message = f"feat: add template {folder_name}"

    try:
        rel_path = template_folder.resolve().relative_to(repo.path)
    except ValueError:
        rel_path = template_folder

    _run_git("add", "--", str(rel_path), cwd=repo.path)
    _run_git("commit", "-m", message, cwd=repo.path)

    result = _run_git("rev-parse", "--short", "HEAD", cwd=repo.path)
    sha = result.stdout.strip()

    logger.info("Committed template %s (%s)", folder_name, sha)
    return sha


def commit_all(
    repo: RepoManager,
    message: str = "chore: update project files",
) -> str:
    """Stage all changes and create a single commit.

    Returns the short commit hash, or an empty string if the tree is
    already clean.
    """
    _run_git("add", "-A", cwd=repo.path)

    # Check if there is anything staged
    result = _run_git("diff", "--cached", "--quiet", cwd=repo.path, check=False)
    if result.returncode == 0:
        logger.debug("Nothing to commit")
        return ""

    _run_git("commit", "-m", message, cwd=repo.path)
    result = _run_git("rev-parse", "--short", "HEAD", cwd=repo.path)
    sha = result.stdout.strip()

    logger.info("Committed all changes (%s)", sha)
    return sha
