"""Project-level operations — initialise, extract IFC, bulk operations.

Orchestrates the full AEC OS pipeline: extraction (Item 01) ->
metadata generation (Item 03) -> version control (Item 04).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aecos.metadata.generator import generate_metadata
from aecos.models.element import Element
from aecos.templates.library import TemplateLibrary
from aecos.templates.tagging import TemplateTags
from aecos.vcs.commits import commit_all
from aecos.vcs.hooks import install_default_pre_commit
from aecos.vcs.repo import RepoManager

logger = logging.getLogger(__name__)

# Project configuration file
PROJECT_CONFIG = "aecos_project.json"


def init_project(
    path: str | Path,
    name: str = "AEC OS Project",
) -> Path:
    """Create an AEC OS project with git repo, template library, and config.

    Parameters
    ----------
    path:
        Directory for the new project.  Created if it does not exist.
    name:
        Human-readable project name.

    Returns the project root path.
    """
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Initialise git repo
    repo = RepoManager(root)
    repo.init_repo()

    # Install default pre-commit hook
    install_default_pre_commit(root)

    # Create project structure
    (root / "elements").mkdir(exist_ok=True)
    (root / "templates").mkdir(exist_ok=True)

    # Write project config
    config = {
        "name": name,
        "version": "0.1.0",
        "elements_dir": "elements",
        "templates_dir": "templates",
    }
    (root / PROJECT_CONFIG).write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    # Commit project structure
    commit_all(repo, message=f"chore: initialise project '{name}'")

    logger.info("Initialised project '%s' at %s", name, root)
    return root


def extract_ifc(
    project_root: Path,
    ifc_path: str | Path,
    *,
    repo: RepoManager | None = None,
    auto_commit: bool = True,
) -> list[Element]:
    """Run the full extraction pipeline on an IFC file.

    Orchestrates: extraction (Item 01) -> metadata (Item 03) ->
    auto-commit (Item 04).

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    ifc_path:
        Path to the IFC file to extract.
    repo:
        Optional repo manager for auto-commit.
    auto_commit:
        If *True* and *repo* is provided, commit after extraction.

    Returns the list of extracted :class:`Element` models.
    """
    from aecos.extraction.pipeline import ifc_to_element_folders

    output_dir = project_root / "elements"
    elements = ifc_to_element_folders(ifc_path, output_dir)

    if auto_commit and repo is not None and elements:
        try:
            commit_all(
                repo,
                message=f"feat: extract {len(elements)} elements from {Path(ifc_path).name}",
            )
        except Exception:
            logger.debug("Auto-commit after extraction failed", exc_info=True)

    return elements


def bulk_promote(
    project_root: Path,
    library: TemplateLibrary,
    element_ids: list[str],
    *,
    tags: TemplateTags | dict[str, Any] | None = None,
    repo: RepoManager | None = None,
    auto_commit: bool = True,
) -> list[Path]:
    """Promote multiple elements to templates in a single operation.

    Parameters
    ----------
    project_root:
        Root directory of the AEC OS project.
    library:
        The template library to promote into.
    element_ids:
        List of element GlobalIds to promote.
    tags:
        Optional tags applied to all promoted templates.
    repo:
        Optional repo manager for auto-commit.
    auto_commit:
        If *True* and *repo* is provided, commit after all promotions.

    Returns list of new template folder paths.
    """
    elem_dir = project_root / "elements"
    promoted: list[Path] = []

    for eid in element_ids:
        folder = elem_dir / f"element_{eid}"
        if not folder.is_dir():
            logger.warning("Element %s not found, skipping", eid)
            continue

        dest = library.promote_to_template(
            folder,
            tags=tags,
        )
        promoted.append(dest)
        logger.info("Promoted %s -> %s", eid, dest.name)

    if auto_commit and repo is not None and promoted:
        try:
            commit_all(
                repo,
                message=f"feat: promote {len(promoted)} elements to templates",
            )
        except Exception:
            logger.debug("Auto-commit after bulk promote failed", exc_info=True)

    return promoted
