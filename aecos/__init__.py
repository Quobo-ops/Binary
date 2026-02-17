"""AEC OS — AI-assisted operating system for architecture, engineering, and construction."""

__version__ = "0.2.0"

from aecos.extraction.pipeline import ifc_to_element_folders
from aecos.metadata.generator import generate_metadata
from aecos.templates.library import TemplateLibrary
from aecos.templates.tagging import TemplateTags

__all__ = [
    "__version__",
    "ifc_to_element_folders",
    "generate_metadata",
    "TemplateLibrary",
    "TemplateTags",
]
