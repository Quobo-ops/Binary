# Phase 3: Intelligent Digital Twin Handover Package
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 1–19 (full v1.0 core); Phases 1 (Procurement), 2 (As-Built)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Delivers a one-command generator for read-only owner handover archives containing QR-linked element history, final BOM with actual supplier data, and cryptographically signed compliance and validation reports. This package becomes the owner's "digital twin of record" for facility management — far beyond static PDFs or IFC exports.

## Goal

One-command production of a complete, read-only digital twin archive for facility owners. The command `aecos handover --to-owner --project-id XYZ` produces everything an owner needs to operate, maintain, insure, and resell the building with full traceability back to every design decision and field modification.

## Core Capabilities

### 1. Complete Archive Builder

Produces a self-contained directory (or `.zip`) with:

| Component | Content | Format |
|-----------|---------|--------|
| Element Folders | Final as-built data for every element | JSON + MD + IFC |
| Bill of Materials | Consolidated BOM with actual supplier SKUs and delivered costs | CSV + MD |
| Compliance Reports | Per-element and project-wide compliance certification | MD + signed PDF |
| Validation Reports | Clash check results, deviation summaries | MD + signed PDF |
| Audit Trail | Complete chain-of-custody for every element | JSON + signed PDF |
| 3D Model | Browser-viewable full project model | glTF + HTML viewer |
| History Timeline | Interactive element history with QR links | HTML + JSON |
| Warranty Data | Manufacturer warranties, expiration dates, contact info | JSON + MD |
| O&M Manuals | Links/references to operation and maintenance documentation | MD |

### 2. QR-Linked Element History

Every physical element receives a unique QR code that links to its complete digital history:

```
QR Code for W-EXT-01 → handover/elements/W-EXT-01/HISTORY.html

Timeline:
2026-01-15  Created from template (Designer: B.Monson)
2026-02-20  Substitution proposed: CMU → ICF (Contractor: Smith Bros)
2026-02-21  Substitution approved (Designer sign-off)
2026-03-05  Installed — as-built logged (Field: J.Garcia)
2026-03-06  Deviation: 7.5" vs 8" — within tolerance, accepted
2026-03-10  Final inspection passed (Inspector: Parish #4421)
```

### 3. Cryptographically Signed Reports

All reports in the handover package are signed using the existing KeyManager (Item 17):

- **Per-element compliance certificate** — Signed attestation of code compliance
- **Project-wide validation report** — Aggregate clash/validation summary
- **Chain-of-custody manifest** — SHA-256 hash of every file in the archive
- **Audit integrity proof** — Merkle tree of all audit log entries

### 4. Browser-Viewable 3D Model

Extends the Visualization Bridge (Item 11) to produce:

- Full-project glTF model assembled from per-element exports
- Self-contained HTML viewer (model-viewer web component)
- Color-coded by status: compliant (green), deviated-accepted (yellow), warranty-active (blue)
- Click-to-inspect: element details, cost, compliance status, maintenance schedule

### 5. Final BOM with Actual Supplier Data

Consolidates procurement data from Phase 1 and as-built data from Phase 2:

```markdown
# Final Bill of Materials — Project XYZ
| Element | Specified | Actual Installed | Supplier | SKU | Unit Cost | Qty | Total |
|---------|-----------|-----------------|----------|-----|-----------|-----|-------|
| W-EXT-01| 8" CMU   | 8" ICF (approved)| ABC Bldg | ICF-800 | $12.50/sf | 450sf | $5,625 |
| D-101   | HM Door  | HM Door + Closer | Allegion | 4040XP | $1,245 | 1 | $1,245 |
```

## Architecture

### Module Structure
```
aecos/handover/
├── __init__.py
├── archive_builder.py       # Main archive orchestrator
├── bom_consolidator.py      # BOM assembly from element data
├── report_signer.py         # Cryptographic signing of reports
├── qr_generator.py          # QR code generation per element
├── history_timeline.py      # Interactive HTML timeline builder
├── model_assembler.py       # Full-project glTF assembly
├── warranty_collector.py    # Warranty data aggregation
└── templates/
    ├── handover_index.html.j2
    ├── element_history.html.j2
    ├── compliance_cert.md.j2
    ├── bom_report.md.j2
    └── manifest.json.j2
```

### AecOS Facade Integration
```python
# Primary handover command
os.generate_handover_package(
    project_id="XYZ",
    recipient="owner",
    include_3d=True,
    sign_reports=True,
    output_path="./handover_XYZ/"
)

# Component-level access
os.generate_bom(project_id="XYZ")
os.generate_compliance_bundle(project_id="XYZ")
os.generate_qr_tags(project_id="XYZ", format="svg")
```

### Archive Structure
```
handover_XYZ/
├── INDEX.html                     # Self-contained landing page
├── MANIFEST.json                  # SHA-256 of every file, signed
├── CERTIFICATE.pdf                # Project-wide compliance cert (signed)
├── BOM.csv                        # Machine-readable bill of materials
├── BOM.md                         # Human-readable BOM
├── model/
│   ├── project.gltf               # Full 3D model
│   └── viewer.html                # Self-contained 3D viewer
├── elements/
│   ├── W-EXT-01/
│   │   ├── HISTORY.html           # QR-linked timeline
│   │   ├── COMPLIANCE.pdf         # Signed compliance cert
│   │   ├── AS_BUILT.md            # Final as-built record
│   │   ├── COST.md                # Final installed cost
│   │   └── qr_tag.svg             # Printable QR code
│   ├── D-101/
│   │   └── ...
│   └── .../
├── audit/
│   ├── full_audit_log.json        # Complete audit trail
│   ├── chain_of_custody.pdf       # Signed chain-of-custody
│   └── merkle_proof.json          # Integrity verification
└── warranties/
    ├── WARRANTY_INDEX.md
    └── by_manufacturer/
        ├── allegion.md
        └── abc_building.md
```

## Quantified Impact

| Impact Area | Projected Benefit | Mechanism |
|-------------|-------------------|-----------|
| Owner Handover Value | +$150k–$300k in facility data | Living digital twin vs. static deliverables |
| Firm Positioning | Premium fees + preferred status | Delivers $50k design + $80k–$120k handoff asset |
| Insurance Value | Reduced premiums via documented chain | Court-ready audit trail |
| Facility Management | 40–60% faster issue resolution | QR scan → instant element history |
| Resale Documentation | Significantly higher property value support | Complete building genome |

## Deliverables

- [ ] `aecos/handover/` module with full archive builder
- [ ] BOM consolidator integrating procurement and as-built data
- [ ] QR code generator (SVG) per element with history links
- [ ] Interactive HTML history timeline per element
- [ ] Full-project glTF model assembler with HTML viewer
- [ ] Cryptographic report signing using existing KeyManager
- [ ] MANIFEST.json with SHA-256 integrity verification
- [ ] Warranty data collector and index generator
- [ ] CLI command: `aecos handover --to-owner --project-id <id>`
- [ ] CLI command: `aecos handover --verify <archive-path>` (integrity check)

## Testing Strategy

```bash
# Unit tests for archive components
pytest tests/test_handover.py

# Integration: Full handover generation from sample project
pytest tests/integration/test_handover_pipeline.py

# Verification: Archive integrity and signature validation
pytest tests/test_handover_integrity.py
```

## Bible Compliance Checklist

- [x] Local-first: Entire archive generated locally from Git history
- [x] Git SoT: Archive is a deterministic snapshot of Git state
- [x] Pure-file: HTML, JSON, Markdown, CSV, SVG, glTF — no database
- [x] Cryptographic audit: All reports signed, manifest hash-verified
- [x] Revit compatible: IFC files in archive re-linkable in Revit
- [x] Legal/financial first: Signed compliance certs, chain-of-custody proof

---

**Dependency Chain:** Phases 1 + 2 + Items 1–19 → This Module
**Next Phase:** Phase 4 (Zero-Install Mobile Field Interface)
