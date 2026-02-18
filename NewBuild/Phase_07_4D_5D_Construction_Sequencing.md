# Phase 7: 4D/5D Construction Sequencing Layer
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 8 (Parametric Generation), 9 (Clash Validation), 10 (Cost & Schedule), 11 (Visualization); Phases 2 (As-Built), 6 (Change Orders)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Extends the existing cost and schedule metadata with predecessor/successor logic, resource loading, and export hooks for Navisworks, Primavera P6, and Procore. This transforms element-level schedule stubs (Item 10) into a fully sequenced, resource-loaded construction model that supports 4D (time) and 5D (cost-over-time) visualization and analysis.

## Goal

Upgrade the per-element schedule data from isolated activity stubs into a linked, dependency-aware construction sequence. Enable critical-path analysis, resource leveling, and earned-value tracking — all computed locally from Git-stored Element data — with one-click export to the scheduling tools contractors already use.

## Core Capabilities

### 1. Predecessor/Successor Logic

Defines construction sequence relationships between elements:

```json
{
  "element_id": "W-EXT-01",
  "activity_id": "ACT-W-EXT-01-INSTALL",
  "predecessors": [
    {"activity": "ACT-FND-01-CURE", "type": "FS", "lag_days": 0},
    {"activity": "ACT-STL-01-ERECT", "type": "FS", "lag_days": 1}
  ],
  "successors": [
    {"activity": "ACT-ROOF-01-FRAME", "type": "FS", "lag_days": 0},
    {"activity": "ACT-W-EXT-01-FINISH", "type": "FS", "lag_days": 3}
  ],
  "relationship_types": "FS=Finish-to-Start, SS=Start-to-Start, FF=Finish-to-Finish, SF=Start-to-Finish"
}
```

### 2. Critical Path Method (CPM) Engine

Local computation of:

- **Forward pass** — Earliest start/finish for every activity
- **Backward pass** — Latest start/finish for every activity
- **Total float** — Schedule flexibility per activity
- **Free float** — Flexibility without affecting successors
- **Critical path** — Zero-float chain determining project duration

```
Project Schedule Summary:
  Total Activities: 247
  Critical Path Length: 142 days
  Critical Activities: 38 (15.4%)
  Total Float Range: 0–45 days
  Projected Completion: 2026-08-15
```

### 3. Resource Loading

Assigns labor, equipment, and material resources to activities:

```json
{
  "activity_id": "ACT-W-EXT-01-INSTALL",
  "resources": {
    "labor": [
      {"trade": "mason_journeyman", "count": 4, "hours_per_day": 8},
      {"trade": "laborer_general", "count": 2, "hours_per_day": 8}
    ],
    "equipment": [
      {"type": "scaffold", "days": 5},
      {"type": "mortar_mixer", "days": 5}
    ],
    "materials": [
      {"item": "8_inch_cmu", "quantity": 450, "unit": "sf"},
      {"item": "mortar_type_s", "quantity": 12, "unit": "bags"}
    ]
  }
}
```

### 4. Resource Leveling and Histograms

Detect and resolve resource overallocation:

```
Week 12 Resource Histogram:
  Carpenters:   ████████████████ 16/12 ⚠️ OVER-ALLOCATED
  Electricians: ████████░░░░░░░░  8/12 ✅
  Masons:       ████████████░░░░ 12/12 ✅ AT CAPACITY
  Laborers:     ██████░░░░░░░░░░  6/14 ✅

Recommendation: Delay ACT-INT-03-FRAME by 3 days (float available: 8 days)
```

### 5. 4D Visualization

Time-based construction sequence visualization:

- **Timeline slider** — Scrub through construction sequence
- **Color-coded phases** — Foundation (brown), structure (red), envelope (blue), interior (green)
- **Progress overlay** — Planned vs. actual installation dates
- **Clash-in-time detection** — Two crews in same space simultaneously

### 6. 5D Cost-Over-Time (Earned Value)

Cash flow and earned value analysis:

```markdown
## Earned Value Report — Week 12

| Metric | Value |
|--------|-------|
| Budget at Completion (BAC) | $487,500 |
| Planned Value (PV) | $195,000 |
| Earned Value (EV) | $182,500 |
| Actual Cost (AC) | $189,200 |
| Schedule Variance (SV) | -$12,500 |
| Cost Variance (CV) | -$6,700 |
| SPI | 0.94 |
| CPI | 0.96 |
| Estimate at Completion (EAC) | $507,813 |
```

### 7. Export Hooks

One-click export to industry scheduling tools:

| Target | Format | Content |
|--------|--------|---------|
| Navisworks | .nwc + .csv | 4D simulation file with element-to-activity mapping |
| Primavera P6 | .xer or .xml | Full schedule with WBS, activities, relationships, resources |
| Procore | CSV via API | Schedule activities, assignments, percent complete |
| MS Project | .xml | Compatible schedule export |
| Custom | JSON + CSV | Machine-readable for any downstream consumer |

## Architecture

### Module Structure
```
aecos/scheduling/
├── __init__.py
├── sequencer.py             # Predecessor/successor relationship manager
├── cpm_engine.py            # Critical Path Method calculator
├── resource_loader.py       # Resource assignment and loading
├── resource_leveler.py      # Over-allocation detection and resolution
├── earned_value.py          # 5D cost-over-time analysis
├── exporters/
│   ├── __init__.py
│   ├── navisworks.py        # Navisworks .nwc + .csv export
│   ├── primavera.py         # P6 .xer/.xml export
│   ├── procore.py           # Procore CSV export
│   ├── ms_project.py        # MS Project XML export
│   └── base.py              # Base exporter interface
└── templates/
    ├── schedule_report.md.j2
    ├── earned_value.md.j2
    └── resource_histogram.md.j2
```

### AecOS Facade Integration
```python
# Build project schedule from element data
os.build_schedule(project_id="XYZ")

# Run CPM analysis
os.analyze_critical_path(project_id="XYZ")

# Resource loading and leveling
os.load_resources(project_id="XYZ")
os.level_resources(project_id="XYZ", strategy="delay_non_critical")

# Earned value analysis
os.earned_value_report(project_id="XYZ", as_of_date="2026-05-15")

# Export to external tools
os.export_schedule(project_id="XYZ", format="primavera_xer")
os.export_schedule(project_id="XYZ", format="navisworks")
```

### Data Flow
```
Element Folders (Items 8, 10)
    ↓
Schedule Metadata (SCHEDULE.md, cost.json per element)
    ↓
Sequencer → Link activities with predecessors/successors
    ↓
CPM Engine → Forward/backward pass, float calculation
    ↓
Resource Loader → Assign crews, equipment, materials
    ↓
Resource Leveler → Resolve over-allocations
    ↓
Earned Value → Cost-over-time analysis
    ↓
Exporters → Navisworks, P6, Procore, MS Project
    ↓
AuditLogger (Item 17) → Signed Git Commit
```

## Deliverables

- [ ] `aecos/scheduling/` module with full 4D/5D pipeline
- [ ] Predecessor/successor relationship engine
- [ ] CPM calculator (forward pass, backward pass, float)
- [ ] Resource loading system with trade-specific assignments
- [ ] Resource leveling with multiple strategies
- [ ] Earned value analysis engine (SPI, CPI, EAC, ETC)
- [ ] Navisworks export (.nwc reference + .csv mapping)
- [ ] Primavera P6 export (.xer and .xml formats)
- [ ] Procore CSV export
- [ ] MS Project XML export
- [ ] CLI command: `aecos schedule build --project <id>`
- [ ] CLI command: `aecos schedule export --format <format>`
- [ ] CLI command: `aecos schedule earned-value --as-of <date>`

## Testing Strategy

```bash
# Unit tests for CPM and resource engines
pytest tests/test_scheduling.py

# Integration: Element data → Full schedule → Export
pytest tests/integration/test_scheduling_pipeline.py

# Export format validation
pytest tests/test_schedule_exports.py

# CPM accuracy benchmark (10-element to 500-element projects)
pytest tests/benchmark/test_cpm_performance.py
```

## Bible Compliance Checklist

- [x] Local-first: CPM, resource leveling, EV all computed locally
- [x] Git SoT: Schedule data lives in Element folders
- [x] Pure-file: JSON relationships, Markdown reports, CSV exports
- [x] Cryptographic audit: Schedule changes signed via AuditLogger
- [x] Revit compatible: Element IDs link schedule to IFC model
- [x] Legal/financial first: Earned value tied to actual cost data

---

**Dependency Chain:** Items 8, 9, 10, 11 + Phases 2, 6 → This Module
**Next Phase:** Phase 8 (Cross-Party Approval and Sign-Off Workflows)
