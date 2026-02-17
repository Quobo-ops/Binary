"""Extract property sets (Psets) from IFC elements."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.util.element

logger = logging.getLogger(__name__)


def extract_psets(element: ifcopenshell.entity_instance) -> dict[str, dict[str, Any]]:
    """Return all property sets for *element*, keyed by Pset name.

    Each value is a flat dict of property-name -> property-value.
    Values that are IFC entity references are converted to their string
    representation so the output is always JSON-serialisable.
    """
    try:
        raw = ifcopenshell.util.element.get_psets(element)
    except Exception:
        logger.debug("Pset extraction failed for %s", element.GlobalId, exc_info=True)
        return {}

    cleaned: dict[str, dict[str, Any]] = {}
    for pset_name, props in raw.items():
        clean_props: dict[str, Any] = {}
        for k, v in props.items():
            if k == "id":
                # Internal ifcopenshell id — skip to keep output clean
                continue
            if isinstance(v, ifcopenshell.entity_instance):
                clean_props[k] = str(v)
            else:
                clean_props[k] = v
        cleaned[pset_name] = clean_props
    return cleaned


def flatten_psets(psets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Flatten nested Pset dicts into a single dict for ``metadata.json``.

    Keys are prefixed with the Pset name: ``"Pset_WallCommon.IsExternal"``
    """
    flat: dict[str, Any] = {}
    for pset_name, props in psets.items():
        for k, v in props.items():
            flat[f"{pset_name}.{k}"] = v
    return flat


def write_psets(psets: dict[str, dict[str, Any]], folder: Path) -> None:
    """Persist property sets as ``properties/psets.json``."""
    props_dir = folder / "properties"
    props_dir.mkdir(parents=True, exist_ok=True)
    (props_dir / "psets.json").write_text(
        json.dumps(psets, indent=2, default=str),
        encoding="utf-8",
    )
