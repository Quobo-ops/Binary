"""IFC file creation — wraps ifcopenshell when available.

When ifcopenshell is available, creates a real IFC4 file with proper
header and entity data.  When unavailable, writes a minimal stub .ifc
with a valid header but no geometry.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Runtime detection of ifcopenshell
_HAS_IFCOPENSHELL = False
try:
    import ifcopenshell  # noqa: F401
    import ifcopenshell.api  # noqa: F401

    _HAS_IFCOPENSHELL = True
except ImportError:
    pass


_IFC_STUB_TEMPLATE = """\
ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [DesignTransferView_V1.0]'),'2;1');
FILE_NAME('{filename}','2026-02-17',('AEC OS'),('AEC OS'),'aecos 0.5.0','aecos','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('{global_id}',$,'Generated Element',$,$,$,$,$,$);
ENDSEC;
END-ISO-10303-21;
"""


def write_ifc(
    folder: Path,
    global_id: str,
    ifc_class: str,
    name: str | None = None,
    psets: dict[str, dict[str, Any]] | None = None,
    materials: list[dict[str, Any]] | None = None,
) -> Path:
    """Write an .ifc file into *folder*.

    Returns the path to the written file.
    """
    ifc_path = folder / "element.ifc"

    if _HAS_IFCOPENSHELL:
        return _write_real_ifc(ifc_path, global_id, ifc_class, name, psets, materials)

    return _write_stub_ifc(ifc_path, global_id, ifc_class)


def _write_real_ifc(
    ifc_path: Path,
    global_id: str,
    ifc_class: str,
    name: str | None,
    psets: dict[str, dict[str, Any]] | None,
    materials: list[dict[str, Any]] | None,
) -> Path:
    """Create a real IFC file using ifcopenshell."""
    import ifcopenshell
    import ifcopenshell.api

    model = ifcopenshell.file(schema="IFC4")
    ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="Generated Element")

    # Create element
    try:
        element = ifcopenshell.api.run(
            "root.create_entity",
            model,
            ifc_class=ifc_class,
            name=name or ifc_class,
        )
    except Exception:
        # Some IFC classes may not be directly creatable; fall back to stub
        logger.debug("Could not create %s, falling back to stub", ifc_class, exc_info=True)
        return _write_stub_ifc(ifc_path, global_id, ifc_class)

    model.write(str(ifc_path))
    logger.info("Wrote real IFC to %s", ifc_path)
    return ifc_path


def _write_stub_ifc(ifc_path: Path, global_id: str, ifc_class: str) -> Path:
    """Write a minimal stub IFC file (valid header, no geometry)."""
    content = _IFC_STUB_TEMPLATE.format(
        filename=ifc_path.name,
        global_id=global_id,
    )
    ifc_path.write_text(content, encoding="utf-8")
    logger.info("Wrote stub IFC to %s", ifc_path)
    return ifc_path


def has_ifcopenshell() -> bool:
    """Return True if ifcopenshell is available at runtime."""
    return _HAS_IFCOPENSHELL
