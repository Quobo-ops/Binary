"""Data Extraction Pipeline — Item 01 of the AEC OS roadmap."""

try:
    from aecos.extraction.pipeline import ifc_to_element_folders
except ImportError:
    # ifcopenshell not available — provide a stub
    def ifc_to_element_folders(*args, **kwargs):  # type: ignore[misc]
        raise ImportError(
            "ifcopenshell is required for IFC extraction. "
            "Install it with: pip install ifcopenshell"
        )

__all__ = ["ifc_to_element_folders"]
