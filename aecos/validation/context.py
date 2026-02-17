"""Context model loading — load existing project elements for clash detection."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_element_data(element_folder: str | Path) -> dict[str, Any]:
    """Load all JSON data from an element folder into a single dict.

    Returns dict with keys: metadata, psets, materials, geometry, spatial.
    """
    folder = Path(element_folder)
    data: dict[str, Any] = {
        "metadata": {},
        "psets": {},
        "materials": [],
        "geometry": {},
        "spatial": {},
    }

    data["metadata"] = _load_json(folder / "metadata.json")
    data["psets"] = _load_json(folder / "properties" / "psets.json")

    mat_raw = _load_json(folder / "materials" / "materials.json")
    data["materials"] = mat_raw if isinstance(mat_raw, list) else []

    data["geometry"] = _load_json(folder / "geometry" / "shape.json")
    data["spatial"] = _load_json(folder / "relationships" / "spatial.json")

    return data


def load_context_elements(folders: list[str | Path]) -> list[dict[str, Any]]:
    """Load multiple element folders as context for validation."""
    elements = []
    for f in folders:
        try:
            elements.append(load_element_data(f))
        except Exception:
            logger.debug("Could not load context element %s", f, exc_info=True)
    return elements


def _load_json(path: Path) -> Any:
    """Load a JSON file, returning an empty dict/list on failure."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
