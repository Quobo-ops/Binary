# Phase 14: Embodied Carbon and Sustainability Analysis Engine
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 7 (Compliance), 8 (Generation), 10 (Cost); Phases 1 (Procurement), 13 (Catalog)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Provides automated life-cycle assessment, embodied-carbon calculations, and green-code compliance checks on every Element and substitution proposal. As sustainability reporting becomes mandatory in more jurisdictions and clients increasingly demand carbon-conscious design, this module makes environmental impact as visible and actionable as cost and compliance.

## Goal

Make embodied carbon and sustainability metrics a first-class data layer alongside cost and compliance for every Element. Automatically calculate environmental impact, compare alternatives, check green-code compliance, and produce reports that meet emerging regulatory requirements and client ESG commitments.

## Core Capabilities

### 1. Embodied Carbon Calculation

Per-element carbon footprint using Environmental Product Declaration (EPD) data:

```markdown
## Embodied Carbon: W-EXT-01 (8" ICF Wall, 450 sf)

### Lifecycle Stage Breakdown (EN 15978)
| Stage | Description | kgCO2e | % of Total |
|-------|-------------|--------|------------|
| A1 | Raw material supply | 2,340 | 42% |
| A2 | Transport to factory | 180 | 3% |
| A3 | Manufacturing | 1,120 | 20% |
| A4 | Transport to site | 95 | 2% |
| A5 | Construction/installation | 340 | 6% |
| B1-B7 | Use phase (50 yr) | 890 | 16% |
| C1-C4 | End of life | 420 | 8% |
| D | Reuse/recycling credit | -185 | -3% |
| **Total** | **Cradle-to-grave** | **5,200** | **100%** |

**Carbon Intensity:** 11.6 kgCO2e/sf
**Benchmark (ICF wall):** 10.0–14.0 kgCO2e/sf → 🟢 Within range
```

### 2. Substitution Carbon Comparison

Side-by-side environmental comparison for Phase 1 substitutions:

```markdown
## Carbon Comparison: W-EXT-01 Substitution Options

| Option | Material | kgCO2e/sf | Cost/sf | Fire Rating | R-Value |
|--------|----------|-----------|---------|-------------|---------|
| Original | 8" CMU | 14.2 | $12.80 | 4 hr | 1.11 |
| **Proposed** | **8" ICF** | **11.6** | **$12.50** | **4 hr** | **23.0** |
| Alt 1 | Timber frame + mineral wool | 6.8 | $14.20 | 2 hr | 21.0 |
| Alt 2 | Steel stud + ext. insulation | 18.5 | $11.90 | 2 hr | 19.5 |

**Recommendation:** ICF delivers 18% carbon reduction vs. CMU with superior thermal performance at lower cost.
```

### 3. Green Code Compliance

Automated checking against sustainability codes and standards:

| Code/Standard | Jurisdiction | Check Type |
|---------------|-------------|------------|
| LEED v4.1 | Voluntary (national) | Material credits, EPD requirements |
| WELL v2 | Voluntary (national) | Material health, VOC limits |
| CALGreen (Title 24 Part 11) | California | Mandatory green building |
| ASHRAE 189.1 | Voluntary (national) | High-performance green buildings |
| IgCC 2021 | Adoptable by jurisdiction | International Green Construction Code |
| Louisiana Act 517 | Louisiana | State energy efficiency requirements |
| Buy Clean policies | Federal/state | Embodied carbon limits for procurement |

```markdown
## Green Code Check: W-EXT-01

| Standard | Requirement | Status |
|----------|------------|--------|
| LEED MRc2 | EPD available for product | 🟢 Pass |
| LEED MRc3 | Recycled content ≥20% | 🟢 Pass (25%) |
| WELL A01 | VOC limits for adhesives | 🟢 Pass |
| Buy Clean | Embodied carbon below threshold | 🟢 Pass (11.6 < 15.0) |
| IgCC 701.3 | Whole-building LCA required | 🟡 Data available |
```

### 4. Whole-Building Life-Cycle Assessment (LCA)

Project-level environmental impact aggregation:

```markdown
## Whole-Building LCA Summary — Project XYZ

### Total Embodied Carbon by System
| Building System | kgCO2e | % of Total | Benchmark |
|----------------|--------|------------|-----------|
| Structure | 85,400 | 38% | 🟡 Slightly above avg |
| Envelope | 42,300 | 19% | 🟢 Below average |
| Interior | 28,100 | 13% | 🟢 Below average |
| MEP Systems | 35,600 | 16% | 🟢 Average |
| Site/Foundation | 32,200 | 14% | 🟢 Below average |
| **Total** | **223,600** | **100%** | |

### Per-Area Metrics
| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| kgCO2e per sf | 44.7 | 50–70 (office) | 🟢 Below average |
| kgCO2e per occupant | 1,490 | 1,500–2,500 | 🟢 Below average |

### Carbon Reduction Opportunities
| Opportunity | Savings (kgCO2e) | Cost Impact | Feasibility |
|-------------|------------------|-------------|-------------|
| Substitute 30% fly-ash concrete | 12,800 | -$2,100 | 🟢 High |
| Use recycled steel (85% recycled) | 8,500 | +$1,200 | 🟢 High |
| Mass timber for 2nd floor | 18,200 | +$15,400 | 🟡 Medium |
| Low-carbon insulation | 3,100 | +$800 | 🟢 High |
```

### 5. EPD Library Management

Local database of Environmental Product Declarations:

```json
{
  "epd_id": "EPD-ICF-001",
  "product": "8-inch ICF Wall Form",
  "manufacturer": "ABC Building Products",
  "program_operator": "NSF International",
  "epd_number": "NSF-2025-00456",
  "valid_from": "2025-06-01",
  "valid_to": "2030-05-31",
  "declared_unit": "1 m² of installed wall",
  "gwp_a1_a3": 28.5,
  "gwp_a4_a5": 4.8,
  "gwp_b1_b7": 9.8,
  "gwp_c1_c4": 4.6,
  "gwp_d": -2.1,
  "gwp_total": 45.6,
  "data_source": "manufacturer_specific",
  "verification": "third_party_verified"
}
```

### 6. Sustainability Reporting

Automated report generation for clients, regulators, and certifications:

- **LEED Documentation Package** — Pre-filled credit worksheets
- **Carbon Disclosure** — Project-level carbon reporting
- **ESG Report Section** — For client corporate sustainability reports
- **Regulatory Submission** — Jurisdiction-specific compliance documentation

## Architecture

### Module Structure
```
aecos/sustainability/
├── __init__.py
├── carbon_calculator.py     # Per-element embodied carbon
├── lca_engine.py           # Whole-building life-cycle assessment
├── green_code_checker.py   # Sustainability code compliance
├── epd_library.py          # EPD database management
├── comparison_engine.py    # Side-by-side environmental comparison
├── reporting.py            # Sustainability report generator
└── data/
    ├── epd_library/
    │   ├── concrete.json
    │   ├── steel.json
    │   ├── masonry.json
    │   ├── wood.json
    │   ├── insulation.json
    │   └── generic_factors.json
    ├── benchmarks/
    │   ├── office_building.json
    │   ├── residential.json
    │   └── industrial.json
    └── codes/
        ├── leed_v4_1.json
        ├── well_v2.json
        ├── igcc_2021.json
        └── buy_clean.json
```

### AecOS Facade Integration
```python
# Per-element carbon
os.calculate_carbon(element_id="W-EXT-01")
os.compare_carbon(element_id="W-EXT-01", alternatives=["PROD-CMU-8STD", "PROD-TF-8"])

# Green code checks
os.check_green_codes(element_id="W-EXT-01", standards=["leed", "well"])

# Whole-building LCA
os.whole_building_lca(project_id="XYZ")
os.carbon_reduction_opportunities(project_id="XYZ")

# Reporting
os.generate_leed_documentation(project_id="XYZ")
os.generate_carbon_report(project_id="XYZ")
```

### Element Folder Output
```
Elements/W-EXT-01/
├── ... (existing files)
├── sustainability/
│   ├── CARBON.md            # Human-readable carbon summary
│   ├── carbon.json          # Machine-readable LCA data
│   ├── epd_reference.json   # Linked EPD data
│   └── green_codes.md       # Sustainability code check results
```

## Deliverables

- [ ] `aecos/sustainability/` module with full LCA pipeline
- [ ] Per-element embodied carbon calculator (EN 15978 stages)
- [ ] Whole-building LCA engine with system-level aggregation
- [ ] Green code compliance checker (LEED, WELL, IgCC, Buy Clean)
- [ ] EPD library with initial dataset (200+ products)
- [ ] Carbon comparison engine for substitution decisions
- [ ] Carbon reduction opportunity identifier
- [ ] LEED documentation package generator
- [ ] Sustainability benchmarks by building type
- [ ] CLI command: `aecos carbon <element-id>`
- [ ] CLI command: `aecos carbon --project <id>`
- [ ] CLI command: `aecos green-check <element-id> --standards leed,well`
- [ ] CLI command: `aecos carbon compare <element-id> --alternatives <list>`

## Testing Strategy

```bash
# Unit tests for carbon calculations
pytest tests/test_sustainability.py

# Integration: Element → Carbon → Green code → Report
pytest tests/integration/test_sustainability_pipeline.py

# Benchmark accuracy against published EPDs
pytest tests/test_carbon_accuracy.py
```

## Bible Compliance Checklist

- [x] Local-first: All LCA calculations from locally stored EPD data
- [x] Git SoT: Carbon data committed to Element folders
- [x] Pure-file: JSON LCA data, Markdown reports — no database
- [x] Cryptographic audit: Carbon calculations signed via AuditLogger
- [x] Revit compatible: Sustainability data linkable to IFC material properties
- [x] Legal/financial first: EPD sources cited, calculations traceable

---

**Dependency Chain:** Items 7, 8, 10 + Phases 1, 13 → This Module
**Next Phase:** Phase 15 (Augmented Reality Field Visualization Layer)
