"""Git hook management — install validation hooks for AEC OS repos.

Provides a default pre-commit hook that validates JSON files and checks
metadata.json schema, plus a generic installer for custom scripts.
"""

from __future__ import annotations

import json
import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# Default pre-commit hook: validate JSON files, check metadata.json has
# required keys (GlobalId, IFCClass).
_DEFAULT_PRE_COMMIT = """\
#!/usr/bin/env python3
\"\"\"AEC OS pre-commit hook: validate JSON files in the staging area.\"\"\"
import json
import subprocess
import sys

def staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]

def validate_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        return str(exc)
    # Schema check for metadata.json
    if path.endswith("metadata.json"):
        for key in ("GlobalId", "IFCClass"):
            if key not in data:
                return f"metadata.json missing required key: {key}"
    return None

errors = []
for f in staged_files():
    if f.endswith(".json"):
        err = validate_json(f)
        if err:
            errors.append(f"{f}: {err}")

if errors:
    print("Pre-commit validation failed:", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
"""


def install_hook(
    repo_path: str | Path,
    hook_type: str,
    script: str,
) -> Path:
    """Install a git hook script.

    Parameters
    ----------
    repo_path:
        Root of the git repository.
    hook_type:
        Hook name (e.g. ``pre-commit``, ``post-commit``).
    script:
        The hook script content (must include a shebang line).

    Returns the path to the installed hook file.
    """
    repo_path = Path(repo_path)
    hooks_dir = repo_path / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / hook_type
    hook_path.write_text(script, encoding="utf-8")

    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    logger.info("Installed %s hook at %s", hook_type, hook_path)
    return hook_path


def install_default_pre_commit(repo_path: str | Path) -> Path:
    """Install the default AEC OS pre-commit validation hook.

    The hook validates all staged JSON files and verifies metadata.json
    contains the required schema keys (GlobalId, IFCClass).

    Returns the path to the installed hook.
    """
    return install_hook(repo_path, "pre-commit", _DEFAULT_PRE_COMMIT)


def remove_hook(repo_path: str | Path, hook_type: str) -> bool:
    """Remove a git hook.  Returns *True* if the hook existed."""
    hook_path = Path(repo_path) / ".git" / "hooks" / hook_type
    if hook_path.is_file():
        hook_path.unlink()
        logger.info("Removed %s hook from %s", hook_type, repo_path)
        return True
    return False
