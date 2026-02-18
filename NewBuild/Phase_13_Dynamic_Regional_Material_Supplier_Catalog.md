# Phase 13: Dynamic Regional Material and Supplier Catalog
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 2 (Template Library), 10 (Cost & Schedule); Phase 1 (Procurement)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Establishes a living, locally managed catalog of Louisiana and national suppliers with pricing, lead times, sustainability scores, and substitution rules, kept current via controlled Git updates. This is the data backbone that powers Phase 1 (Procurement), Phase 7 (5D Cost), and Phase 14 (Sustainability) with real, actionable supplier intelligence.

## Goal

Build and maintain a comprehensive, locally stored material and supplier database that serves as the single authoritative source for pricing, availability, lead times, performance data, and sustainability metrics. Updated quarterly via Git, never requiring cloud access for core operation.

## Core Capabilities

### 1. Supplier Registry

Structured catalog of regional and national suppliers:

```json
{
  "supplier_id": "SUP-LA-001",
  "name": "ABC Masonry Supply",
  "type": "distributor",
  "headquarters": "Baton Rouge, LA",
  "service_area": ["East Baton Rouge", "West Baton Rouge", "Ascension", "Livingston"],
  "contacts": {
    "sales": {"name": "Mike Johnson", "phone": "225-555-0100", "email": "mjohnson@abcmasonry.com"},
    "delivery": {"name": "Dispatch", "phone": "225-555-0101"}
  },
  "categories": ["masonry", "concrete", "mortar", "rebar"],
  "payment_terms": "Net 30",
  "delivery": {
    "min_lead_days": 3,
    "typical_lead_days": 5,
    "rush_available": true,
    "rush_surcharge_pct": 15
  },
  "certifications": ["MBE", "DBE"],
  "sustainability_score": 72,
  "reliability_score": 88,
  "last_verified": "2026-01-15"
}
```

### 2. Product Catalog with Pricing

Granular product data tied to suppliers:

```json
{
  "product_id": "PROD-CMU-8STD",
  "name": "8-inch Standard CMU Block",
  "category": "masonry",
  "specifications": {
    "nominal_size": "8×8×16 in",
    "weight": "38 lb",
    "compressive_strength_psi": 1900,
    "fire_rating_hours": 4,
    "r_value": 1.11,
    "density": "normal_weight"
  },
  "pricing": [
    {
      "supplier_id": "SUP-LA-001",
      "unit_price": 2.15,
      "unit": "each",
      "price_per_sf": 4.30,
      "effective_date": "2026-01-01",
      "expiry_date": "2026-03-31",
      "min_order": 100,
      "volume_breaks": [
        {"qty": 500, "discount_pct": 5},
        {"qty": 2000, "discount_pct": 10},
        {"qty": 5000, "discount_pct": 15}
      ]
    }
  ],
  "substitutions": [
    {
      "product_id": "PROD-ICF-8STD",
      "equivalence": "performance_equivalent",
      "notes": "Higher R-value, requires different crew skill"
    }
  ],
  "sustainability": {
    "embodied_carbon_kgco2e_per_unit": 12.5,
    "recycled_content_pct": 25,
    "local_sourcing": true,
    "eol_recyclable": true
  }
}
```

### 3. Regional Pricing Intelligence

Louisiana-specific market data:

```markdown
## Regional Pricing Index — Baton Rouge Metro, Q1 2026

| Material Category | BR Metro Index | National Avg | Delta | Trend |
|------------------|---------------|-------------|-------|-------|
| Concrete (3000 psi) | $145/cy | $160/cy | -9.4% | → Stable |
| Structural Steel | $2,850/ton | $2,920/ton | -2.4% | ↑ Rising |
| Lumber (SPF 2×4) | $4.85/bf | $5.10/bf | -4.9% | ↓ Falling |
| CMU (8" standard) | $2.15/ea | $2.35/ea | -8.5% | → Stable |
| Drywall (1/2" 4×8) | $12.50/sht | $13.80/sht | -9.4% | → Stable |
| Roofing (30yr arch) | $98/sq | $110/sq | -10.9% | ↑ Rising |

**Regional Adjustment Factor:** 0.92 (BR Metro relative to national)
**Last Updated:** 2026-01-15 | **Next Update:** 2026-04-01
```

### 4. Lead-Time Intelligence

Real-time-equivalent lead-time data:

```markdown
## Lead Time Report — Current as of 2026-02-18

### Standard Materials (In-Stock at Local Distributors)
| Material | Typical Lead | Current Lead | Status |
|----------|-------------|-------------|--------|
| CMU Block | 3–5 days | 3 days | 🟢 Normal |
| Ready-Mix Concrete | 1–2 days | 1 day | 🟢 Normal |
| Structural Steel | 6–8 weeks | 10 weeks | 🔴 Extended |
| Lumber (framing) | 3–5 days | 4 days | 🟢 Normal |
| Windows (standard) | 4–6 weeks | 5 weeks | 🟢 Normal |
| Windows (custom) | 8–12 weeks | 14 weeks | 🟡 Delayed |

### Supply Chain Alerts
- ⚠️ Structural steel lead times extended due to tariff impacts
- ⚠️ Custom window orders from Manufacturer X delayed 2 weeks
- ✅ Concrete supply normalized after Q4 2025 shortage
```

### 5. Substitution Rules Engine

Automated equivalency checking:

```python
class SubstitutionRules:
    def find_equivalents(self, product_id: str, criteria: dict) -> list:
        """Find approved substitutions meeting specified criteria."""
        # Load product spec
        product = self.catalog.get(product_id)

        # Find candidates matching minimum performance
        candidates = self.catalog.search(
            category=product.category,
            min_fire_rating=criteria.get("min_fire_rating", product.fire_rating),
            min_r_value=criteria.get("min_r_value", product.r_value),
            max_cost_delta_pct=criteria.get("max_cost_delta_pct", 20),
            in_stock=criteria.get("in_stock", False)
        )

        # Rank by: cost savings, lead time, sustainability, reliability
        return self.rank_substitutions(candidates, criteria)
```

### 6. Catalog Update Workflow

Controlled, versioned updates:

```
Quarterly Update Process:
  1. Firm admin pulls latest catalog from firm's private Git repo
  2. Diff shows: 45 prices updated, 12 new products, 3 suppliers added
  3. Admin reviews changes, approves or modifies
  4. git merge → Catalog updated across all projects
  5. Affected elements flagged for cost re-calculation

Ad-Hoc Updates:
  - Contractor submits new supplier data via CLI
  - Reviewed by designated catalog manager
  - Merged into catalog with full audit trail
```

## Architecture

### Module Structure
```
aecos/catalog/
├── __init__.py
├── supplier_registry.py     # Supplier CRUD and search
├── product_catalog.py       # Product CRUD, search, comparison
├── pricing_engine.py        # Regional pricing and volume breaks
├── lead_time_tracker.py     # Lead-time intelligence
├── substitution_rules.py    # Equivalency and substitution logic
├── catalog_updater.py       # Git-based catalog update workflow
├── sustainability_scorer.py # Environmental scoring per product
└── data/
    ├── suppliers/
    │   ├── louisiana.json
    │   └── national.json
    ├── products/
    │   ├── masonry.json
    │   ├── concrete.json
    │   ├── steel.json
    │   ├── lumber.json
    │   ├── doors_hardware.json
    │   ├── windows.json
    │   ├── roofing.json
    │   ├── finishes.json
    │   └── mechanical.json
    ├── pricing/
    │   ├── baton_rouge_2026_q1.json
    │   └── national_index_2026_q1.json
    └── lead_times/
        └── current.json
```

### AecOS Facade Integration
```python
# Search catalog
os.find_product(category="masonry", fire_rating="4H")
os.find_supplier(area="East Baton Rouge", category="masonry")
os.find_substitutions(product_id="PROD-CMU-8STD", max_cost_delta=15)

# Pricing
os.current_price(product_id="PROD-CMU-8STD", supplier_id="SUP-LA-001", qty=500)
os.regional_index(region="baton_rouge", category="masonry")

# Lead times
os.lead_time(product_id="PROD-CMU-8STD", supplier_id="SUP-LA-001")
os.supply_alerts(region="louisiana")

# Catalog management
os.catalog_update(source="firm_repo")
os.add_product(data={...})
os.add_supplier(data={...})
```

## Deliverables

- [ ] `aecos/catalog/` module with full catalog management
- [ ] Supplier registry with Louisiana regional focus
- [ ] Product catalog with specifications and pricing
- [ ] Regional pricing engine with adjustment factors
- [ ] Lead-time tracking with supply chain alerts
- [ ] Substitution rules engine with ranking
- [ ] Git-based catalog update workflow
- [ ] Sustainability scoring per product
- [ ] Initial Louisiana dataset (50+ suppliers, 500+ products)
- [ ] CLI command: `aecos catalog search "<query>"`
- [ ] CLI command: `aecos catalog price <product-id> --qty <n>`
- [ ] CLI command: `aecos catalog substitutions <product-id>`
- [ ] CLI command: `aecos catalog update --from <repo>`

## Testing Strategy

```bash
# Unit tests for catalog operations
pytest tests/test_catalog.py

# Integration: Catalog → Procurement → Cost Engine
pytest tests/integration/test_catalog_pipeline.py

# Data validation: Ensure catalog integrity
pytest tests/test_catalog_data.py
```

## Bible Compliance Checklist

- [x] Local-first: Entire catalog stored and queried locally
- [x] Git SoT: Catalog data versioned in Git, updates via git merge
- [x] Pure-file: JSON catalogs, CSV exports — no external database
- [x] Cryptographic audit: Catalog changes logged via AuditLogger
- [x] Revit compatible: Product specs mappable to IFC material properties
- [x] Legal/financial first: Pricing data traceable to source and date

---

**Dependency Chain:** Items 2, 10 + Phase 1 → This Module
**Next Phase:** Phase 14 (Embodied Carbon and Sustainability Analysis Engine)
