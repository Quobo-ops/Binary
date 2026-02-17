"""Search the template registry by tag, type, keyword, or similarity.

All searches run against the in-memory :class:`TemplateRegistry` — no
database, no NLP.  Filtering is delegated to
:meth:`TemplateTags.matches`.
"""

from __future__ import annotations

from aecos.templates.registry import RegistryEntry, TemplateRegistry


def search(
    registry: TemplateRegistry,
    query: dict[str, object],
) -> list[RegistryEntry]:
    """Return registry entries whose tags satisfy every filter in *query*.

    *query* may contain any of the keys accepted by
    :meth:`TemplateTags.matches` plus ``description`` for substring
    matching on the entry description.

    Returns a list of matching :class:`RegistryEntry` objects (possibly
    empty).
    """
    description_kw: str | None = None
    tag_query: dict[str, object] = {}

    for key, value in query.items():
        if key == "description" and value is not None:
            description_kw = str(value).lower()
        else:
            tag_query[key] = value

    results: list[RegistryEntry] = []
    for entry in registry.list_all():
        # Tag-based filtering
        if tag_query and not entry.tags.matches(tag_query):
            continue

        # Description substring filter
        if description_kw and description_kw not in entry.description.lower():
            continue

        results.append(entry)

    return results
