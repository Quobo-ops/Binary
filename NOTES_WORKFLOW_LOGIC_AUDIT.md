# Notes Workflow — If/Then Logic Audit

**Workflow chosen:** Metadata Generation Pipeline (the "Notes" workflow)

This is the most fully implemented workflow in the codebase. It generates four
markdown documents — README.md, COMPLIANCE.md, COST.md, and USAGE.md — for
every element or template folder. The `render_usage` function specifically
produces "Insertion notes" and a "Notes" section, making this the canonical
Notes workflow.

**Files covered (in execution order):**

| File | Role |
|---|---|
| `aecos/extraction/pipeline.py` | Entry point: IFC extraction triggers metadata generation |
| `aecos/metadata/generator.py` | Orchestrator: loads JSON, detects template vs element, calls renderers |
| `aecos/metadata/templates/readme.py` | Renders `README.md` |
| `aecos/metadata/templates/compliance.py` | Renders `COMPLIANCE.md` |
| `aecos/metadata/templates/cost.py` | Renders `COST.md` |
| `aecos/metadata/templates/usage.py` | Renders `USAGE.md` (contains "Notes" section) |
| `aecos/metadata/writer.py` | Writes markdown files to disk |
| `aecos/templates/library.py` | Template CRUD — calls `generate_metadata` on add/promote |
| `aecos/templates/tagging.py` | Tag matching logic used by template search |
| `aecos/templates/search.py` | Search filter with description + tag queries |
| `aecos/templates/registry.py` | Persistent JSON index of all templates |

---

## 1. Extraction Pipeline Entry (`pipeline.py`)

### IF/THEN #1 — `_safe_str()` (line 28-34)

```
IF value is None         → return None
IF value is entity_instance → return str(value)
ELSE                     → return str(value)
```

**Verdict: REDUNDANT.** Both the `isinstance` branch and the fallback do
`str(value)`. The `isinstance` check was likely intended to extract a specific
attribute (e.g. `.GlobalId` or `.Name`) but was never differentiated. Harmless
but should either be removed or given distinct behavior.

---

### IF/THEN #2 — `_write_single_element_ifc()` (line 37-66)

```
TRY   → create minimal IFC file containing only this element
CATCH → log debug, silently continue (no .ifc file produced)
```

**Verdict: CORRECT.** Best-effort geometry copy. Some elements have complex
references that can't be trivially isolated. Silent failure is acceptable since
the element folder still has all its JSON data.

---

### IF/THEN #3 — Metadata generation in `_process_element()` (line 124-129)

```
TRY   → generate_metadata(folder)
CATCH → log debug, silently continue
```

**Verdict: CORRECT.** An element folder can exist without its markdown files
if generation fails. This is a soft dependency — the raw JSON data is always
written first. The markdown is a convenience layer.

---

### IF/THEN #4 — Main loop fault tolerance (line 163-173)

```
FOR each building element:
    TRY   → _process_element(entity, ifc_file, output_dir)
    CATCH → log warning, skip this element, continue to next
```

**Verdict: CORRECT.** One bad element doesn't crash the entire extraction.
Fault isolation at the element level is the right granularity.

---

## 2. Metadata Generator (`generator.py`)

### IF/THEN #5 — `_load_json()` (line 29-37)

```
IF path is NOT a file           → return {}
TRY to parse JSON               → return parsed data
IF JSONDecodeError or OSError   → log debug, return {}
```

**Verdict: MINOR ISSUE.** Always returns `{}` on failure, but
`materials.json` is expected to be a `list`. This is handled downstream
(see #6), but a `default` parameter would be cleaner.

---

### IF/THEN #6 — Materials type guard (line 63-65)

```
IF materials_raw is a list → use as-is
ELSE                       → use empty list []
```

**Verdict: CORRECT.** Compensates for `_load_json()` returning `{}` when
`materials.json` is missing or corrupt. Also guards against a malformed
`materials.json` that contains a dict instead of a list.

---

### IF/THEN #7 — Template detection (line 69-73)

```
IF template_manifest.json exists as a file → is_template = True, load manifest
ELSE                                       → is_template = False, manifest = None
```

**Verdict: CORRECT.** Clean discrimination. The presence of
`template_manifest.json` is the sole signal distinguishing a template from a
raw element. Single source of truth.

---

## 3. README Renderer (`readme.py`)

### IF/THEN #8 — Name resolution (line 23)

```
IF metadata has "Name"     → use Name
ELSE IF has "GlobalId"     → use GlobalId
ELSE                       → "Unknown"
```

**Verdict: CORRECT.** Reasonable fallback chain. Name is human-friendly,
GlobalId is machine-unique, "Unknown" is the catch-all.

---

### IF/THEN #9 — Title rendering (line 31-34)

```
IF is_template → "# Template: {name}"
ELSE           → "# {name}"
```

**Verdict: CORRECT.** Templates are visually distinguished from raw elements.

---

### IF/THEN #10 — ObjectType in identity table (line 43-44)

```
IF object_type is truthy → include row in identity table
ELSE                     → omit row
```

**Verdict: CORRECT.** Optional field, correctly omitted when absent.

---

### IF/THEN #11 — Template version/author in identity table (line 45-49)

```
IF is_template AND manifest:
    IF manifest has "version" → include version row
    IF manifest has "author"  → include author row
```

**Verdict: CORRECT.** Only templates carry version/author metadata.
Double-guard ensures manifest is loaded before accessing its keys.

---

### IF/THEN #12 — Template description section (line 53-57)

```
IF is_template AND manifest AND manifest has "description"
    → render "## Description" section
```

**Verdict: CORRECT.** Triple guard. All three conditions must be true.
Description is only meaningful for curated templates.

---

### IF/THEN #13 — Properties section (line 60-68)

```
IF psets is truthy (non-empty dict) → render "## Properties" with all psets
ELSE                                → omit entire section
```

**Verdict: CORRECT.** No empty "## Properties" section cluttering the output.

---

### IF/THEN #14 — Materials section and thickness display (line 71-82)

```
IF materials is truthy (non-empty list) → render "## Materials" table
    FOR each material:
        IF thickness is not None → show numeric value
        ELSE                     → show "—" (em-dash)
```

**Verdict: CORRECT.** Not all materials have measurable thickness (e.g.
coatings, finishes). Em-dash is a clean placeholder.

---

### IF/THEN #15 — Spatial location section (line 85-98)

```
IF any of (site_name, building_name, storey_name) is truthy:
    → render "## Spatial Location"
    IF site_name     → "- Site: {site_name}"
    IF building_name → "- Building: {building_name}"
    IF storey_name   → "- Storey: {storey_name}"
ELSE → omit entire section
```

**Verdict: CORRECT.** Only renders if at least one field exists. Each
sub-field is independently optional.

---

### IF/THEN #16 — Template tags section (line 101-110)

```
IF is_template AND manifest AND manifest has "tags":
    collect from: material, region, compliance_codes, custom
    IF collected tag_parts is non-empty → render "## Tags"
```

**Verdict: CORRECT.** Two levels of filtering — must be a template with tags,
and the tags must contain at least one value.

---

## 4. Compliance Renderer (`compliance.py`)

### IF/THEN #17 — Compliance codes from manifest (line 30-36)

```
IF manifest AND manifest.tags.compliance_codes exists
    → render "## Applicable Codes" section listing each code
```

**Verdict: CORRECT.** Only templates carry compliance code tags. Raw elements
skip this section.

---

### IF/THEN #18 — Property sets listing (line 41-49)

```
IF psets is truthy → list all property sets with their properties
ELSE               → "No property sets extracted."
```

**Verdict: CORRECT.** Unlike the README renderer (which omits the section
entirely), the compliance renderer shows an explicit empty state. This is the
right call — for compliance purposes, the *absence* of property data is
important to communicate.

---

## 5. Cost Renderer (`cost.py`)

### IF/THEN #19 — Materials section (line 27-37)

```
IF materials is truthy → render materials table
    FOR each material:
        IF thickness is not None → show value
        ELSE                     → show "—"
ELSE → omit materials section entirely
```

**Verdict: CORRECT.** Same pattern as README. Consistent.

---

## 6. Usage Renderer (`usage.py`) — The "Notes" Generator

### IF/THEN #20 — Title (line 25-28)

```
IF is_template → "# Usage — Template: {name}"
ELSE           → "# Usage — {name}"
```

**Verdict: CORRECT.** Consistent with README title convention.

---

### IF/THEN #21 — Insertion notes (line 37-55)

```
IF is_template:
    → show template insertion API code:
      TemplateLibrary("path/to/library")
      library.get_template("{global_id}")
ELSE:
    → show how to promote to a reusable template:
      TemplateLibrary("path/to/library")
      library.promote_to_template("path/to/element_{global_id}")
```

**Verdict: CORRECT.** Contextually appropriate guidance. Templates get
"how to use" notes; raw elements get "how to promote" notes. Good UX.

---

### IF/THEN #22 — Original Location breadcrumb (line 59-73)

```
IF any of (site_name, building_name, storey_name) is truthy:
    → render "## Original Location"
    → join available fields with " > " separator
```

**Verdict: MINOR INCONSISTENCY.** README uses a bullet list for spatial data;
USAGE uses a breadcrumb with " > ". Both are valid, but the different
formatting for the same data could confuse readers who compare the two files.
Not a bug, but worth aligning in a future pass.

---

### IF/THEN #23 — Region notes (line 77-83)

```
IF is_template AND manifest:
    IF manifest.tags.region exists → render "## Region"
```

**Verdict: CORRECT.** Only templates have region data. Region is shown as a
comma-separated list.

---

### IF/THEN #24 — Static "Notes" section (line 85-90)

```
ALWAYS rendered (no condition):
    "## Notes"
    "- Validate compliance before inserting into production models"
    "- Check spatial coordination and clash detection after placement"
```

**Verdict: ACCEPTABLE but STATIC.** This section is always the same regardless
of element type, IFC class, or compliance status. For a V1 this is fine.
Future enhancement: conditionally include notes based on element type (e.g.
structural elements should mention load calculations; MEP elements should
mention service clearance zones).

---

## 7. Markdown Writer (`writer.py`)

### IF/THEN #25 — Directory creation (line 13)

```
ALWAYS → mkdir(parents=True, exist_ok=True) before writing
```

**Verdict: CORRECT.** Ensures parent directories exist. Idempotent.

---

## 8. Template Library (`library.py`)

### IF/THEN #26 — `add_template()` tag normalization (line 105-108)

```
IF tags is a dict      → validate into TemplateTags via Pydantic
ELSE IF tags is None   → create empty TemplateTags()
(implicit: if already TemplateTags, use as-is)
```

**Verdict: CORRECT.** Flexible input handling for the public API.

---

### IF/THEN #27 — `add_template()` destination overwrite (line 111-112)

```
IF destination folder already exists → shutil.rmtree(dest), then copytree
```

**Verdict: POTENTIAL ISSUE.** Silently deletes the existing template folder
with no warning, backup, or confirmation. In a multi-user environment, this
could destroy someone's work. The operation is logged at INFO level *after*
completion (line 147), but there is no pre-deletion warning. Should at least
log a WARNING before rmtree.

---

### IF/THEN #28 — `add_template()` metadata generation (line 138-145)

```
TRY   → generate_metadata(dest)
CATCH → log debug, silently continue
```

**Verdict: CORRECT.** Same fault-tolerant pattern as the extraction pipeline.

---

### IF/THEN #29 — `get_template()` registry/disk consistency (line 150-158)

```
IF entry not in registry  → return None
IF entry in registry BUT folder doesn't exist on disk → return None
ELSE                      → return folder path
```

**Verdict: CORRECT.** Handles stale registry entries (where the folder was
manually deleted) gracefully. Returns None rather than a path to a
nonexistent directory.

---

### IF/THEN #30 — `get_manifest()` (line 160-165)

```
IF get_template() returns None → return None
ELSE                           → read and return manifest dict
```

**Verdict: CORRECT.** Delegates existence check to `get_template()`.

---

### IF/THEN #31 — `update_template()` tag handling (line 197-200)

```
IF tags is a dict         → validate into TemplateTags
ELSE IF tags is TemplateTags → use directly
(implicit: if tags is None → preserve existing tags)
```

**Verdict: CORRECT.** Partial-update semantics. Only updates what you provide.

---

### IF/THEN #32 — `update_template()` optional fields (line 202-207)

```
IF version is not None     → update version
IF author is not None      → update author
IF description is not None → update description
```

**Verdict: CORRECT.** Clean partial-update pattern. `None` means "don't
change", not "set to empty".

---

### IF/THEN #33 — `remove_template()` (line 225-240)

```
IF template not in registry                    → return False
IF template in registry AND folder exists      → rmtree folder, save registry
IF template in registry AND folder NOT on disk → just remove from registry, save
```

**Verdict: CORRECT.** Handles all three states cleanly. Returns a boolean
for the caller to know whether there was anything to remove.

---

### IF/THEN #34 — `promote_to_template()` ID derivation (line 278-284)

```
IF template_id provided → use it
ELSE:
    IF metadata.json exists → use GlobalId (fallback: folder name)
    ELSE                    → use folder name
```

**Verdict: CORRECT.** Auto-derives a sensible ID. The
`meta.get("GlobalId", element_folder.name)` fallback handles the edge case
where metadata.json exists but lacks a GlobalId.

---

### IF/THEN #35 — `promote_to_template()` auto-populate ifc_class (line 287-296)

```
IF tags is None  → create empty TemplateTags
IF tags is dict  → validate into TemplateTags
IF tags.ifc_class is None:
    IF metadata.json exists → set ifc_class from metadata["IFCClass"]
```

**Verdict: CORRECT but INEFFICIENT.** Reads `metadata.json` a second time
(it was already read at line 280-282 for ID derivation). Should cache the
first read. Not a correctness bug, just wasted I/O.

---

## 9. Tag Matching (`tagging.py`)

### IF/THEN #36 — Null query values (line 40-41)

```
IF query value is None → skip this filter (matches everything)
```

**Verdict: CORRECT.** Allows partial queries.

---

### IF/THEN #37 — `ifc_class` matching (line 43-47)

```
IF query has "ifc_class":
    IF self.ifc_class is None → return False
    IF case-insensitive mismatch → return False
```

**Verdict: CORRECT.** Untagged templates don't match class filters.
Case-insensitive comparison handles "IfcWall" vs "ifcwall".

---

### IF/THEN #38 — `material` matching (line 49-53)

```
IF query has "material":
    IF NO queried material appears in template materials → return False
```

**Verdict: CORRECT.** ANY-match semantics — querying `["steel", "concrete"]`
matches a template that has either or both.

---

### IF/THEN #39 — `region` matching (line 55-59)

```
IF query has "region":
    IF NO queried region appears in template regions → return False
```

**Verdict: CORRECT.** Same ANY-match semantics as material.

---

### IF/THEN #40 — `compliance_codes` matching (line 61-65)

```
IF query has "compliance_codes":
    IF NO queried code appears in template codes → return False
```

**Verdict: CORRECT.** Same ANY-match pattern.

---

### IF/THEN #41 — Generic `tags` matching (line 67-76)

```
IF query has "tags":
    Collect ALL tags from: material + region + compliance_codes + custom
    IF NOT ALL queried tags appear in combined set → return False
```

**Verdict: SEMANTICALLY DIFFERENT FROM FIELD-SPECIFIC SEARCHES.** Individual
field filters (#38-40) use `any()` (match if at least one hit). The generic
`tags` filter uses `all()` (every queried tag must be present). This is
internally consistent and arguably correct — "find templates tagged with
both X and Y" — but the difference is not documented and could surprise API
consumers.

---

### IF/THEN #42 — `keyword` matching (line 78-91)

```
IF query has "keyword":
    Concatenate all tag fields into one string
    IF keyword NOT a substring of that blob → return False
```

**Verdict: CORRECT.** Broad text search across all tag data.

---

## 10. Search (`search.py`)

### IF/THEN #43 — Query key routing (line 29-33)

```
FOR each key in query:
    IF key == "description" AND value is not None → store as description filter
    ELSE                                          → pass to tag_query
```

**Verdict: CORRECT.** Separates the description filter (handled by search.py)
from tag filters (delegated to TemplateTags.matches).

---

### IF/THEN #44 — Tag-based filtering (line 38-39)

```
IF tag_query is non-empty AND tags don't match → skip entry
```

**Verdict: CORRECT.** An empty tag_query matches everything (no filters
applied).

---

### IF/THEN #45 — Description filtering (line 42-43)

```
IF description_kw set AND keyword NOT in entry description → skip entry
```

**Verdict: CORRECT.** Case-insensitive substring match on the description
field.

---

## 11. Registry (`registry.py`)

### IF/THEN #46 — Registry load (line 78-90)

```
IF registry file doesn't exist           → start with empty entries
IF file exists but corrupt (JSON/Key error) → log warning, start fresh
ELSE                                     → load entries from file
```

**Verdict: CORRECT.** Self-healing — corrupt state doesn't block startup.
The warning log is appropriate (unlike most silent debug logs in this
pipeline).

---

### IF/THEN #47 — Atomic save (line 92-109)

```
TRY → write to temp file, then atomic rename
IF any exception during write → delete temp file, re-raise
```

**Verdict: CORRECT.** Standard atomic write pattern. Prevents corruption
from partial writes or crashes during save.

---

## Summary of Issues Found

### Bugs / Correctness Issues

None. The business logic is internally consistent across all 47 conditional
branches.

### Code Quality Issues

| # | Severity | Location | Issue |
|---|----------|----------|-------|
| 1 | Low | `pipeline.py:28-34` | `_safe_str()` isinstance check is redundant — both branches do `str(value)` |
| 2 | Low | `generator.py:29-37` | `_load_json()` always returns `{}` on failure; a `default` parameter would be cleaner for list-typed files |
| 3 | Medium | `library.py:111-112` | `add_template()` silently deletes existing template folder via `rmtree` with no warning log or confirmation |
| 4 | Low | `usage.py` vs `readme.py` | Spatial location uses breadcrumb format in USAGE but bullet list in README — minor presentation inconsistency |
| 5 | Low | `tagging.py:67-76` | `tags` query uses `all()` while individual field queries use `any()` — semantic difference is undocumented |
| 6 | Low | `library.py:278-296` | `promote_to_template()` reads `metadata.json` twice — should cache the first read |

### Architectural Observations

- **Fault tolerance is consistent**: Every layer (pipeline, generator,
  library) wraps `generate_metadata()` in try/except and continues on failure.
  This is appropriate for a pipeline that processes many elements.

- **Template vs Element discrimination is clean**: A single file
  (`template_manifest.json`) is the sole signal. Every renderer checks
  `is_template` before rendering template-specific sections.

- **The static Notes section in USAGE.md is a V1 placeholder**: The same two
  bullet points appear for every element regardless of type. Future work
  should make these context-aware (e.g. structural elements mention load
  calculations, MEP elements mention service clearances).

- **The `add_comment()` pseudocode in `16_Collaboration_Layer.md` has two
  logic gaps**: (a) `Reply-to: {reply_to}` is written even when `reply_to`
  is `None`, producing "Reply-to: None"; (b) no input validation on `user`
  or `text` parameters.
