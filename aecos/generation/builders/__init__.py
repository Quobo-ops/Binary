"""Element builders — one per IFC class."""

from aecos.generation.builders.base import ElementBuilder
from aecos.generation.builders.wall import WallBuilder
from aecos.generation.builders.door import DoorBuilder
from aecos.generation.builders.window import WindowBuilder
from aecos.generation.builders.slab import SlabBuilder
from aecos.generation.builders.column import ColumnBuilder
from aecos.generation.builders.beam import BeamBuilder

BUILDER_REGISTRY: dict[str, type[ElementBuilder]] = {
    "IfcWall": WallBuilder,
    "IfcWallStandardCase": WallBuilder,
    "IfcDoor": DoorBuilder,
    "IfcWindow": WindowBuilder,
    "IfcSlab": SlabBuilder,
    "IfcColumn": ColumnBuilder,
    "IfcBeam": BeamBuilder,
}


def get_builder(ifc_class: str) -> ElementBuilder:
    """Return the appropriate builder instance for an IFC class."""
    builder_cls = BUILDER_REGISTRY.get(ifc_class)
    if builder_cls is None:
        # Default to wall builder as most generic
        builder_cls = WallBuilder
    return builder_cls()


__all__ = [
    "ElementBuilder",
    "WallBuilder",
    "DoorBuilder",
    "WindowBuilder",
    "SlabBuilder",
    "ColumnBuilder",
    "BeamBuilder",
    "BUILDER_REGISTRY",
    "get_builder",
]
