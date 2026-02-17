"""Template CRUD operations with VCS integration.

Wraps :class:`TemplateLibrary` and adds automatic git commits for every
mutating operation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aecos.templates.library import TemplateLibrary
from aecos.templates.registry import RegistryEntry
from aecos.templates.tagging import TemplateTags
from aecos.vcs.commits import commit_all
from aecos.vcs.repo import RepoManager

logger = logging.getLogger(__name__)


def promote_to_template(
    library: TemplateLibrary,
    element_folder: str | Path,
    *,
    repo: RepoManager | None = None,
    tags: TemplateTags | dict[str, Any] | None = None,
    version: str = "1.0.0",
    author: str = "",
    description: str = "",
    template_id: str | None = None,
    auto_commit: bool = True,
) -> Path:
    """Promote an extracted element to a library template.

    Delegates to :meth:`TemplateLibrary.promote_to_template` and
    optionally commits the result.

    Returns the path to the new template folder.
    """
    dest = library.promote_to_template(
        element_folder,
        tags=tags,
        version=version,
        author=author,
        description=description,
        template_id=template_id,
    )

    if auto_commit and repo is not None:
        try:
            commit_all(repo, message=f"feat: promote element to template {dest.name}")
        except Exception:
            logger.debug("Auto-commit failed for promote", exc_info=True)

    return dest


def add_template(
    library: TemplateLibrary,
    template_id: str,
    source_folder: str | Path,
    *,
    repo: RepoManager | None = None,
    tags: TemplateTags | dict[str, Any] | None = None,
    version: str = "1.0.0",
    author: str = "",
    description: str = "",
    auto_commit: bool = True,
) -> Path:
    """Add a template to the library with optional auto-commit."""
    dest = library.add_template(
        template_id,
        source_folder,
        tags=tags,
        version=version,
        author=author,
        description=description,
    )

    if auto_commit and repo is not None:
        try:
            commit_all(repo, message=f"feat: add template {template_id}")
        except Exception:
            logger.debug("Auto-commit failed for add_template", exc_info=True)

    return dest


def remove_template(
    library: TemplateLibrary,
    template_id: str,
    *,
    repo: RepoManager | None = None,
    auto_commit: bool = True,
) -> bool:
    """Remove a template with optional auto-commit."""
    removed = library.remove_template(template_id)

    if removed and auto_commit and repo is not None:
        try:
            commit_all(repo, message=f"chore: remove template {template_id}")
        except Exception:
            logger.debug("Auto-commit failed for remove_template", exc_info=True)

    return removed


def search_templates(
    library: TemplateLibrary,
    query: dict[str, object],
) -> list[RegistryEntry]:
    """Search the template library by tags, type, or keyword."""
    return library.search(query)
