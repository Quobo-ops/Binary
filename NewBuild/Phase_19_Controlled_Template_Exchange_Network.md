# Phase 19: Controlled Template Exchange Network
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 2 (Template Library), 4 (VCS), 17 (Security & Audit); Phase 16 (Portfolio Governance)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Creates a secure, permissioned mechanism for firms to share and exchange validated templates and best-practice assemblies while preserving cryptographic provenance and intellectual-property controls. This is the AEC OS equivalent of a professional library network — firms can share what they choose, with full attribution, licensing, and quality verification.

## Goal

Enable a trusted network where AEC firms can publish, discover, and consume validated templates and assemblies — accelerating the entire industry while protecting each firm's intellectual property. Every shared template carries cryptographic provenance proving its origin, validation status, and usage terms.

## Core Capabilities

### 1. Template Publishing

Firms publish validated templates to the exchange network:

```markdown
## Published Template: ICF-EXT-WALL-8IN-2HR

**Publisher:** Monson Architecture, Baton Rouge LA
**Version:** 1.2.0
**License:** Creative Commons BY-NC (Attribution, Non-Commercial)
**Published:** 2026-03-15

### Template Card
| Property | Value |
|----------|-------|
| Category | Exterior Wall Assembly |
| Material | Insulated Concrete Form (ICF) |
| Thickness | 8 inches |
| Fire Rating | 2 hours |
| R-Value | R-23 |
| Code Compliance | IBC 2024, Louisiana amendments |
| Sustainability | 11.6 kgCO2e/sf, EPD-verified |
| Cost Range | $11.50–$13.50/sf (2026 LA pricing) |
| Downloads | 47 |
| Rating | ⭐⭐⭐⭐⭐ (12 reviews) |

### Provenance Chain
- Created: 2026-01-15 by B. Monson (SHA: abc123)
- Validated: 2026-01-18 by Compliance Engine v1.0
- Field-tested: 3 projects, 1,200+ sf installed
- Published: 2026-03-15 (Signature: xyz789)
```

### 2. Template Discovery

Search and browse available templates:

```python
# Search the exchange
results = os.exchange_search(
    category="exterior_wall",
    fire_rating="2H",
    region="louisiana",
    min_rating=4.0,
    license_type="commercial_ok"
)

# Results
[
    {
        "id": "ICF-EXT-WALL-8IN-2HR",
        "publisher": "Monson Architecture",
        "rating": 4.8,
        "downloads": 47,
        "field_tested": True,
        "cost_range": "$11.50–$13.50/sf",
        "carbon": "11.6 kgCO2e/sf"
    },
    ...
]
```

### 3. Intellectual Property Controls

Multi-level IP protection:

| License Type | Permissions | Restrictions |
|-------------|-------------|-------------|
| Open (CC0) | Use, modify, redistribute | None |
| Attribution (CC-BY) | Use, modify, redistribute | Must credit original author |
| Non-Commercial (CC-BY-NC) | Use, modify for own projects | Cannot resell or redistribute |
| Firm-Only | Use within subscribing firm | No external sharing |
| View-Only | Inspect but not download | Reference only |

```json
{
  "ip_controls": {
    "license": "CC-BY-NC-4.0",
    "attribution": "Monson Architecture, Baton Rouge LA",
    "permitted_uses": ["internal_projects", "modification", "derivative_works"],
    "prohibited_uses": ["resale", "redistribution", "commercial_licensing"],
    "watermark": true,
    "usage_tracking": true,
    "expiry": null
  }
}
```

### 4. Cryptographic Provenance

Every shared template carries an unbroken chain of provenance:

```json
{
  "provenance": {
    "origin": {
      "firm": "Monson Architecture",
      "author": "B. Monson, AIA",
      "created": "2026-01-15T10:00:00Z",
      "signature": "Ed25519:abc123..."
    },
    "validations": [
      {
        "type": "compliance",
        "engine_version": "1.0",
        "codes_checked": ["IBC_2024", "LA_amendments"],
        "result": "pass",
        "date": "2026-01-18T14:30:00Z",
        "signature": "Ed25519:def456..."
      },
      {
        "type": "field_test",
        "projects": 3,
        "total_quantity": "1,200 sf",
        "deviations": 0,
        "date": "2026-03-01T00:00:00Z",
        "signature": "Ed25519:ghi789..."
      }
    ],
    "publication": {
      "exchange_version": "1.0",
      "published": "2026-03-15T09:00:00Z",
      "hash": "SHA-256:jkl012...",
      "signature": "Ed25519:mno345..."
    }
  }
}
```

### 5. Quality Verification

Templates must pass quality gates before publication:

```
Publication Quality Gates:
  ✅ Compliance Engine validation (mandatory)
  ✅ Clash validation clean (mandatory)
  ✅ Cost data attached and sourced (mandatory)
  ✅ Markdown metadata complete (mandatory)
  ✅ IFC export valid and Revit-importable (mandatory)
  🟡 Field-tested on ≥1 project (recommended)
  🟡 Peer-reviewed by ≥1 other user (recommended)
  🟡 Sustainability data attached (recommended)
```

### 6. Exchange Network Architecture

Decentralized, Git-based exchange:

```
Firm A's Repo ←→ Exchange Index (Git) ←→ Firm B's Repo
                       ↕
                  Firm C's Repo

Exchange Index contains:
  - Template metadata (cards, ratings, provenance)
  - Download URLs (pointing to firm-hosted Git repos)
  - Usage statistics
  - Review and rating data

Template data lives on publisher's infrastructure
Exchange index is lightweight, Git-hosted, replicable
```

No central server holds the templates themselves — only the index and metadata. Templates are fetched directly from the publisher's Git repository (or a mirror they control).

## Architecture

### Module Structure
```
aecos/exchange/
├── __init__.py
├── publisher.py             # Template publishing workflow
├── discovery.py             # Search and browse exchange
├── downloader.py            # Secure template download with verification
├── ip_manager.py            # Intellectual property controls
├── provenance_tracker.py    # Cryptographic provenance chain
├── quality_gate.py          # Pre-publication quality checks
├── rating_system.py         # Review and rating management
├── exchange_index.py        # Local index of available templates
└── config/
    ├── exchange_registry.json    # Known exchange nodes
    ├── licenses.json            # License type definitions
    └── quality_requirements.json # Publication requirements
```

### AecOS Facade Integration
```python
# Publishing
os.exchange_publish(template_id="ICF-EXT-WALL-8IN-2HR", license="CC-BY-NC")
os.exchange_unpublish(template_id="ICF-EXT-WALL-8IN-2HR")

# Discovery
os.exchange_search(category="wall", region="louisiana")
os.exchange_browse(sort="rating", limit=20)
os.exchange_template_info(template_id="ICF-EXT-WALL-8IN-2HR")

# Download and use
os.exchange_download(template_id="ICF-EXT-WALL-8IN-2HR")
os.exchange_verify(template_id="ICF-EXT-WALL-8IN-2HR")  # Verify provenance

# Reviews
os.exchange_review(template_id="ICF-EXT-WALL-8IN-2HR", rating=5, comment="...")
```

## Deliverables

- [ ] `aecos/exchange/` module with full exchange pipeline
- [ ] Template publishing workflow with quality gates
- [ ] Discovery engine with search, filter, and browse
- [ ] Secure download with cryptographic provenance verification
- [ ] IP management with multi-level licensing
- [ ] Rating and review system
- [ ] Decentralized exchange index (Git-based)
- [ ] Template card generator with metadata summary
- [ ] Provenance chain verifier
- [ ] CLI command: `aecos exchange publish <template-id> --license <type>`
- [ ] CLI command: `aecos exchange search "<query>"`
- [ ] CLI command: `aecos exchange download <template-id>`
- [ ] CLI command: `aecos exchange verify <template-id>`
- [ ] CLI command: `aecos exchange review <template-id> --rating <1-5>`

## Testing Strategy

```bash
# Unit tests for publishing and provenance
pytest tests/test_exchange.py

# Integration: Publish → Index → Search → Download → Verify
pytest tests/integration/test_exchange_pipeline.py

# IP enforcement tests
pytest tests/test_exchange_ip.py

# Provenance chain verification
pytest tests/test_exchange_provenance.py
```

## Bible Compliance Checklist

- [x] Local-first: Templates downloaded and stored locally; works offline
- [x] Git SoT: Exchange index and templates are Git repositories
- [x] Pure-file: JSON metadata, standard Element folder structure
- [x] Cryptographic audit: Full provenance chain with signatures
- [x] Revit compatible: All exchanged templates are valid IFC elements
- [x] Legal/financial first: IP controls, licensing, usage tracking

---

**Dependency Chain:** Items 2, 4, 17 + Phase 16 → This Module
**Next Phase:** Phase 20 (AEC OS as Industry Digital Thread Standard)
