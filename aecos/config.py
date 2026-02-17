"""Global configuration: paths, constants, settings."""

from pathlib import Path

# Default output directory for extracted element folders
DEFAULT_OUTPUT_DIR = Path("output")

# Supported IFC schemas
SUPPORTED_SCHEMAS = ("IFC2X3", "IFC4")

# IFC classes treated as extractable building elements.
# Using the base class captures all subtypes (IfcWall, IfcDoor, IfcSlab, etc.)
ELEMENT_BASE_CLASS = "IfcBuildingElement"

# Maximum recursion depth when serialising IFC entity references
MAX_ENTITY_DEPTH = 5

# Sub-folder names inside each element folder
GEOMETRY_DIR = "geometry"
PROPERTIES_DIR = "properties"
MATERIALS_DIR = "materials"
RELATIONSHIPS_DIR = "relationships"
