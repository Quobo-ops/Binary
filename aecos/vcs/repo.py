"""RepoManager — initialise, configure, and query a git repository.

All git operations use :func:`subprocess.run`; no GitPython dependency.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# AEC OS .gitignore defaults
_DEFAULT_GITIGNORE = """\
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.pytest_cache/

# AEC OS temporaries
*.log
*.tmp

# Large binary outputs (use LFS for tracked IFC)
*.obj
*.stl
*.fbx

# OS files
.DS_Store
Thumbs.db
"""

# .gitattributes for IFC/JSON/MD line-ending and LFS tracking
_DEFAULT_GITATTRIBUTES = """\
# Ensure consistent line endings for text artifacts
*.json text eol=lf
*.md text eol=lf
*.py text eol=lf

# IFC files tracked via Git LFS when available
*.ifc filter=lfs diff=lfs merge=lfs -text
"""


class GitError(Exception):
    """Raised when a git subprocess returns a non-zero exit code."""


def _run_git(
    *args: str,
    cwd: str | Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a git command via subprocess and return the result.

    Parameters
    ----------
    *args:
        Arguments passed after ``git``.
    cwd:
        Working directory for the command.
    check:
        If *True*, raise :class:`GitError` on non-zero exit.
    """
    cmd = ["git", *args]
    logger.debug("git %s (cwd=%s)", " ".join(args), cwd)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result


class RepoManager:
    """Manage a git repository for AEC OS projects.

    Parameters
    ----------
    path:
        Root directory of the repository.  Can be an existing repo or a
        path to initialise.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()

    # -- Initialisation -------------------------------------------------------

    def init_repo(self) -> Path:
        """Initialise a git repository with AEC OS defaults.

        Creates ``.gitignore`` and ``.gitattributes`` tailored for
        IFC/JSON/Markdown workflows, then makes an initial commit.

        Returns the repo root path.
        """
        self.path.mkdir(parents=True, exist_ok=True)
        _run_git("init", cwd=self.path)

        # Ensure local git config has user identity for commits
        _run_git("config", "user.email", "aecos@localhost", cwd=self.path, check=False)
        _run_git("config", "user.name", "AEC OS", cwd=self.path, check=False)
        _run_git("config", "commit.gpgsign", "false", cwd=self.path, check=False)

        # Write default configuration files
        gi = self.path / ".gitignore"
        if not gi.exists():
            gi.write_text(_DEFAULT_GITIGNORE, encoding="utf-8")

        ga = self.path / ".gitattributes"
        if not ga.exists():
            ga.write_text(_DEFAULT_GITATTRIBUTES, encoding="utf-8")

        # Stage and create initial commit
        _run_git("add", ".gitignore", ".gitattributes", cwd=self.path)
        _run_git(
            "commit", "-m", "chore: initialise AEC OS repository",
            cwd=self.path,
        )

        logger.info("Initialised AEC OS repo at %s", self.path)
        return self.path

    def clone(self, url: str, dest: str | Path | None = None) -> Path:
        """Clone a remote repository.

        Parameters
        ----------
        url:
            Remote URL to clone.
        dest:
            Optional destination directory.  Defaults to a subdirectory
            of *self.path* derived from the URL.

        Returns the path to the cloned repository.
        """
        if dest is None:
            dest = self.path / url.rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
        dest = Path(dest)
        _run_git("clone", url, str(dest))
        logger.info("Cloned %s -> %s", url, dest)
        return dest

    # -- Status / info --------------------------------------------------------

    def is_repo(self) -> bool:
        """Return *True* if *self.path* is inside a git repository."""
        if not self.path.is_dir():
            return False
        result = _run_git(
            "rev-parse", "--is-inside-work-tree",
            cwd=self.path,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def status(self) -> str:
        """Return the output of ``git status --porcelain``."""
        result = _run_git("status", "--porcelain", cwd=self.path)
        return result.stdout

    def is_clean(self) -> bool:
        """Return *True* if the working tree has no uncommitted changes."""
        return self.status().strip() == ""

    def current_branch(self) -> str:
        """Return the name of the current branch."""
        result = _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.path)
        return result.stdout.strip()

    # -- Stage / commit -------------------------------------------------------

    def stage(self, *paths: str | Path) -> None:
        """Stage one or more paths for commit."""
        str_paths = [str(p) for p in paths]
        _run_git("add", "--", *str_paths, cwd=self.path)

    def commit(self, message: str) -> str:
        """Create a commit with the given message.

        Returns the short commit hash.
        """
        _run_git("commit", "-m", message, cwd=self.path)
        result = _run_git("rev-parse", "--short", "HEAD", cwd=self.path)
        return result.stdout.strip()
