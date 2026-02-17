"""History and log queries — element-level git log, diff, and blame.

All queries are scoped to specific folders so that each element or
template has a clean, self-contained history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from aecos.vcs.repo import RepoManager, _run_git

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """A single entry from ``git log``."""

    sha: str
    author: str
    date: str
    message: str


def get_element_history(
    repo: RepoManager,
    element_folder: str | Path,
    max_count: int = 50,
) -> list[LogEntry]:
    """Return the commit history for a specific element folder.

    Parameters
    ----------
    repo:
        The repository manager.
    element_folder:
        Path to the element folder (absolute or relative to repo root).
    max_count:
        Maximum number of log entries to return.

    Returns a list of :class:`LogEntry` objects, newest first.
    """
    element_folder = Path(element_folder)
    try:
        rel_path = element_folder.resolve().relative_to(repo.path)
    except ValueError:
        rel_path = element_folder

    # Use a delimiter unlikely to appear in commit messages
    sep = "---AECOS_SEP---"
    fmt = f"%H{sep}%an{sep}%ai{sep}%s"

    result = _run_git(
        "log",
        f"--max-count={max_count}",
        f"--format={fmt}",
        "--",
        str(rel_path),
        cwd=repo.path,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    entries: list[LogEntry] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(sep)
        if len(parts) >= 4:
            entries.append(
                LogEntry(
                    sha=parts[0],
                    author=parts[1],
                    date=parts[2],
                    message=parts[3],
                )
            )
    return entries


def diff_element(
    repo: RepoManager,
    element_folder: str | Path,
    rev1: str,
    rev2: str = "HEAD",
) -> str:
    """Return the diff for an element folder between two revisions.

    Parameters
    ----------
    repo:
        The repository manager.
    element_folder:
        Path to the element folder.
    rev1, rev2:
        Git revision identifiers (commit SHA, branch name, tag, etc.).

    Returns the diff output as a string.
    """
    element_folder = Path(element_folder)
    try:
        rel_path = element_folder.resolve().relative_to(repo.path)
    except ValueError:
        rel_path = element_folder

    result = _run_git(
        "diff",
        f"{rev1}..{rev2}",
        "--",
        str(rel_path),
        cwd=repo.path,
        check=False,
    )
    return result.stdout


def get_file_log(
    repo: RepoManager,
    file_path: str | Path,
    max_count: int = 20,
) -> list[LogEntry]:
    """Return the commit history for a single file."""
    file_path = Path(file_path)
    try:
        rel_path = file_path.resolve().relative_to(repo.path)
    except ValueError:
        rel_path = file_path

    sep = "---AECOS_SEP---"
    fmt = f"%H{sep}%an{sep}%ai{sep}%s"

    result = _run_git(
        "log",
        f"--max-count={max_count}",
        f"--format={fmt}",
        "--",
        str(rel_path),
        cwd=repo.path,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    entries: list[LogEntry] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(sep)
        if len(parts) >= 4:
            entries.append(
                LogEntry(
                    sha=parts[0],
                    author=parts[1],
                    date=parts[2],
                    message=parts[3],
                )
            )
    return entries
