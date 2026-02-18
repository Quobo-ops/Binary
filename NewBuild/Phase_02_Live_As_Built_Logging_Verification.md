# Phase 2: Live As-Built Logging and Verification
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 1 (Extraction), 3 (Metadata), 4 (VCS), 6 (NLParser), 7 (Compliance), 10 (Cost), 17 (Security & Audit); Phase 1 (Procurement)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Enables field teams to record as-built conditions via natural language or mobile interface, automatically producing designed-versus-as-built diffs and updating the immutable Git thread with full audit signatures. Every field observation becomes a first-class, versioned, traceable entry in the Element folder — closing the gap between design intent and constructed reality.

## Goal

Allow field teams to log as-built conditions and generate formal change-order packages via single voice/text command while preserving the Git thread. A superintendent walks up to an installed element, speaks or types what they see, and the system records the delta, flags deviations, and optionally triggers a change-order workflow.

## Core Capabilities

### 1. Natural-Language Field Logging

Extends the NLParser (Item 6) with field-observation vocabulary:

**Example Commands:**
```
"Field verify door D-101 installed as right-hand reverse with closer added"
"Wall W-EXT-01 poured at 7.5 inches instead of 8 inches"
"Add 2×4 blocking at 48" o.c. for storefront glazing at grid B-4"
"Beam B-201 deflection measured at 3/8 inch under load"
"Slab S-102 finished 1/4 inch high at column C-5"
```

### 2. Designed vs. As-Built Diff Engine

Automatically generates structured comparison between design intent and field reality:

```
┌──────────────┬───────────────────┬───────────────────┐
│ Property     │ Designed          │ As-Built          │
├──────────────┼───────────────────┼───────────────────┤
│ Thickness    │ 8.000 in          │ 7.500 in          │
│ Hand         │ Left-Hand         │ Right-Hand Rev.   │
│ Hardware     │ Lever only        │ Lever + Closer    │
│ Elevation    │ 100'-0"           │ 100'-0.25"        │
└──────────────┴───────────────────┴───────────────────┘
Status: DEVIATION DETECTED — Requires review
```

### 3. Tolerance Checking

Configurable tolerance thresholds per element type and property:

- **Dimensional:** ±1/8" for finish work, ±1/4" for rough framing, ±1/2" for sitework
- **Angular:** ±0.5° for plumb/level
- **Positional:** ±1/4" for anchor bolts, ±1" for slab edges
- **Performance:** Binary pass/fail for fire rating, acoustic, thermal

Deviations within tolerance are logged as informational; deviations outside tolerance trigger automatic review flags.

### 4. Compliance Re-Validation

Every as-built entry is re-checked through the Compliance Engine (Item 7):

- Does the as-built condition still meet code?
- If not, what remediation is required?
- Auto-generates compliance deviation report with code citations

### 5. Cost Impact Assessment

Deviations that affect material or labor are automatically priced through the Cost Engine (Item 10):

- Additional material cost (e.g., added closer hardware)
- Credit for under-spec material (e.g., thinner wall)
- Labor delta for rework or field modifications

## Architecture

### Module Structure
```
aecos/field/
├── __init__.py
├── as_built_logger.py       # Core logging engine
├── diff_engine.py           # Designed vs. as-built comparison
├── tolerance_checker.py     # Configurable tolerance validation
├── deviation_reporter.py    # Deviation flagging and reporting
├── field_context.py         # Field-specific NLParser context
└── templates/
    ├── as_built_entry.md.j2
    ├── deviation_report.md.j2
    └── tolerances_default.json
```

### AecOS Facade Integration
```python
# New facade methods
os.log_as_built(element_id="D-101", observation="installed right-hand reverse with closer added")
os.diff_as_built(element_id="D-101")  # returns designed vs. as-built comparison
os.check_deviation(element_id="W-EXT-01")  # returns tolerance check results
os.field_status(element_id="W-EXT-01")  # returns current field status
```

### Data Flow
```
Field Observation (voice/text)
    ↓
NLParser (Item 6) + Field Context
    ↓
As-Built Entry (JSON in Element folder)
    ↓
Diff Engine → Designed vs. As-Built comparison
    ↓
Tolerance Checker → Within/Outside tolerance
    ↓
Compliance Engine (Item 7) → Re-validation
    ↓
Cost Engine (Item 10) → Impact calculation
    ↓
AuditLogger (Item 17) → Signed Git Commit
```

### Element Folder Output
```
Elements/D-101/
├── ... (existing files)
├── as_built/
│   ├── AB-001_entry.json           # Structured observation
│   ├── AB-001_diff.md              # Side-by-side comparison
│   ├── AB-001_compliance.md        # Re-validation result
│   ├── AB-001_cost_impact.json     # Cost delta if applicable
│   ├── AB-001_audit.json           # Signed audit entry
│   └── FIELD_STATUS.md             # Current aggregate status
```

### FIELD_STATUS.md Format
```markdown
# Field Status: D-101 (Door)
**Last Updated:** 2026-03-15 14:32 CST
**Status:** 🟡 DEVIATION — Under Review

## Summary
| Check         | Result    |
|---------------|-----------|
| Installed     | ✅ Yes    |
| As-Designed   | ⚠️ Deviated |
| Code Compliant| ✅ Yes    |
| Cost Impact   | +$245.00  |

## Deviations
1. Hand changed: LH → RH-Reverse (within project flexibility)
2. Hardware added: Door closer (owner-requested addition)

## Approvals Required
- [ ] Designer sign-off on hand change
- [ ] Cost approval for added hardware
```

## Change-Order Integration (Bridge to Phase 6)

When a deviation exceeds tolerance or triggers cost/schedule impact, the system prepares change-order draft data:

- Deviation summary with photographic evidence links
- Cost and schedule impact (from Cost Engine)
- Compliance status (from Compliance Engine)
- Recommendation: accept as-is, remediate, or formal change order

This data feeds directly into Phase 6 (Automated Change-Order Generation).

## Deliverables

- [ ] `aecos/field/` module with as-built logging pipeline
- [ ] Diff engine for designed vs. as-built comparison
- [ ] Configurable tolerance system per element type
- [ ] Compliance re-validation integration
- [ ] Cost impact auto-calculation for deviations
- [ ] FIELD_STATUS.md generator per Element folder
- [ ] Field-specific NLParser context vector
- [ ] CLI command: `aecos field-log <element-id> "<observation>"`
- [ ] CLI command: `aecos field-diff <element-id>`

## Testing Strategy

```bash
# Unit tests for diff engine and tolerance checking
pytest tests/test_field.py

# Integration: Field log → Diff → Compliance → Cost
pytest tests/integration/test_field_pipeline.py

# Scenario tests: 30 common field deviations
pytest tests/scenarios/test_field_deviations.py
```

## Bible Compliance Checklist

- [x] Local-first: All diff and tolerance checks run locally
- [x] Git SoT: As-built entries committed to Element folder
- [x] Pure-file: JSON entries, Markdown diffs and status files
- [x] Cryptographic audit: Every field observation signed via AuditLogger
- [x] Revit compatible: As-built data exportable to updated IFC
- [x] Legal/financial first: Compliance re-check mandatory on every deviation

---

**Dependency Chain:** Phase 1 (Procurement) + Items 6, 7, 10, 17 → This Module
**Next Phase:** Phase 3 (Intelligent Digital Twin Handover Package)
