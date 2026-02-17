"""Write/update Markdown files inside element or template folders."""

from __future__ import annotations

from pathlib import Path


def write_markdown(folder: Path, filename: str, content: str) -> Path:
    """Write *content* to ``<folder>/<filename>``, creating dirs if needed.

    Returns the path to the written file.
    """
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return path
