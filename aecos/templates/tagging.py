"""Tag schema for AEC OS templates.

Tags categorise templates by IFC class, material, region, compliance codes,
and arbitrary user-defined labels.  The schema is intentionally flat and
JSON-serialisable so it can live inside ``template_manifest.json``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TemplateTags(BaseModel):
    """Structured tag set attached to every template.

    All fields are optional — a newly promoted element may only have
    ``ifc_class`` populated, with the rest filled in over time.
    """

    ifc_class: str | None = None
    material: list[str] = Field(default_factory=list)
    region: list[str] = Field(default_factory=list)
    compliance_codes: list[str] = Field(default_factory=list)
    custom: list[str] = Field(default_factory=list)

    def matches(self, query: dict[str, object]) -> bool:
        """Return *True* if this tag set satisfies every filter in *query*.

        Supported keys and match semantics:

        * ``ifc_class`` — exact (case-insensitive) match
        * ``material`` — at least one queried material present
        * ``region`` — at least one queried region present
        * ``compliance_codes`` — at least one queried code present
        * ``tags`` — list of strings; every tag must appear in
          *material*, *region*, *compliance_codes*, or *custom*
        * ``keyword`` — substring search across all string fields
        """
        for key, value in query.items():
            if value is None:
                continue

            if key == "ifc_class":
                if self.ifc_class is None:
                    return False
                if self.ifc_class.lower() != str(value).lower():
                    return False

            elif key == "material":
                needles = _as_list(value)
                lower_mats = [m.lower() for m in self.material]
                if not any(n.lower() in lower_mats for n in needles):
                    return False

            elif key == "region":
                needles = _as_list(value)
                lower_regions = [r.lower() for r in self.region]
                if not any(n.lower() in lower_regions for n in needles):
                    return False

            elif key == "compliance_codes":
                needles = _as_list(value)
                lower_codes = [c.lower() for c in self.compliance_codes]
                if not any(n.lower() in lower_codes for n in needles):
                    return False

            elif key == "tags":
                needles = _as_list(value)
                all_tags = (
                    [m.lower() for m in self.material]
                    + [r.lower() for r in self.region]
                    + [c.lower() for c in self.compliance_codes]
                    + [t.lower() for t in self.custom]
                )
                if not all(n.lower() in all_tags for n in needles):
                    return False

            elif key == "keyword":
                kw = str(value).lower()
                blob = " ".join(
                    filter(
                        None,
                        [self.ifc_class]
                        + self.material
                        + self.region
                        + self.compliance_codes
                        + self.custom,
                    )
                ).lower()
                if kw not in blob:
                    return False

        return True


def _as_list(value: object) -> list[str]:
    """Coerce a string or list to ``list[str]``."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]
