"""Embedded default pricing data — no external CSV files required.

Realistic 2026 pricing for common AEC materials and element types.
Base prices in USD.  Source attribution included for traceability.
"""

from __future__ import annotations

from typing import Any

# Source: RSMeans 2026 Q1 estimated (projected from 2024-2025 trends)
SOURCE = "RSMeans 2026 Q1 estimated"

# Unit cost data: (material, ifc_class) -> {material_cost, labor_cost, unit_type}
# material_cost and labor_cost are per unit (m2, m3, each, m)
SEED_PRICING: dict[tuple[str, str], dict[str, Any]] = {
    # Walls
    ("concrete", "IfcWall"): {
        "material_cost_per_unit": 85.00,
        "labor_cost_per_unit": 65.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    ("cmu", "IfcWall"): {
        "material_cost_per_unit": 72.00,
        "labor_cost_per_unit": 58.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    ("brick", "IfcWall"): {
        "material_cost_per_unit": 95.00,
        "labor_cost_per_unit": 78.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    ("gypsum", "IfcWall"): {
        "material_cost_per_unit": 35.00,
        "labor_cost_per_unit": 42.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    ("steel", "IfcWall"): {
        "material_cost_per_unit": 120.00,
        "labor_cost_per_unit": 85.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    ("wood", "IfcWall"): {
        "material_cost_per_unit": 55.00,
        "labor_cost_per_unit": 48.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    # Doors
    ("wood", "IfcDoor"): {
        "material_cost_per_unit": 450.00,
        "labor_cost_per_unit": 180.00,
        "unit_type": "each",
        "source": SOURCE,
    },
    ("steel", "IfcDoor"): {
        "material_cost_per_unit": 750.00,
        "labor_cost_per_unit": 220.00,
        "unit_type": "each",
        "source": SOURCE,
    },
    ("aluminum", "IfcDoor"): {
        "material_cost_per_unit": 850.00,
        "labor_cost_per_unit": 200.00,
        "unit_type": "each",
        "source": SOURCE,
    },
    ("glass", "IfcDoor"): {
        "material_cost_per_unit": 1200.00,
        "labor_cost_per_unit": 250.00,
        "unit_type": "each",
        "source": SOURCE,
    },
    # Windows
    ("glass", "IfcWindow"): {
        "material_cost_per_unit": 380.00,
        "labor_cost_per_unit": 160.00,
        "unit_type": "each",
        "source": SOURCE,
    },
    ("aluminum", "IfcWindow"): {
        "material_cost_per_unit": 520.00,
        "labor_cost_per_unit": 180.00,
        "unit_type": "each",
        "source": SOURCE,
    },
    # Slabs
    ("concrete", "IfcSlab"): {
        "material_cost_per_unit": 95.00,
        "labor_cost_per_unit": 70.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    ("steel", "IfcSlab"): {
        "material_cost_per_unit": 140.00,
        "labor_cost_per_unit": 90.00,
        "unit_type": "m2",
        "source": SOURCE,
    },
    # Columns
    ("concrete", "IfcColumn"): {
        "material_cost_per_unit": 320.00,
        "labor_cost_per_unit": 210.00,
        "unit_type": "m3",
        "source": SOURCE,
    },
    ("steel", "IfcColumn"): {
        "material_cost_per_unit": 480.00,
        "labor_cost_per_unit": 280.00,
        "unit_type": "m3",
        "source": SOURCE,
    },
    ("wood", "IfcColumn"): {
        "material_cost_per_unit": 250.00,
        "labor_cost_per_unit": 160.00,
        "unit_type": "m3",
        "source": SOURCE,
    },
    # Beams
    ("steel", "IfcBeam"): {
        "material_cost_per_unit": 180.00,
        "labor_cost_per_unit": 120.00,
        "unit_type": "m",
        "source": SOURCE,
    },
    ("concrete", "IfcBeam"): {
        "material_cost_per_unit": 150.00,
        "labor_cost_per_unit": 95.00,
        "unit_type": "m",
        "source": SOURCE,
    },
    ("wood", "IfcBeam"): {
        "material_cost_per_unit": 85.00,
        "labor_cost_per_unit": 65.00,
        "unit_type": "m",
        "source": SOURCE,
    },
}

# Default pricing when material/class combo not found
DEFAULT_PRICING: dict[str, Any] = {
    "material_cost_per_unit": 100.00,
    "labor_cost_per_unit": 75.00,
    "unit_type": "m2",
    "source": f"{SOURCE} (default estimate)",
}

# Regional adjustment factors
REGIONAL_FACTORS: dict[str, float] = {
    "US_AVG": 1.00,
    "LA": 0.92,  # Louisiana / Baton Rouge
    "CA": 1.15,  # California
    "NY": 1.35,  # New York
    "TX": 0.88,  # Texas
    "FL": 0.94,  # Florida
    "IL": 1.05,  # Illinois
    "WA": 1.10,  # Washington
    "CO": 1.02,  # Colorado
    "GA": 0.90,  # Georgia
}

# Schedule productivity rates: days per unit by (ifc_class)
# These are for a standard crew
PRODUCTIVITY_RATES: dict[str, dict[str, Any]] = {
    "IfcWall": {
        "rate_per_m2": 0.12,
        "crew_size": 4,
        "predecessor_type": "structural",
    },
    "IfcWallStandardCase": {
        "rate_per_m2": 0.12,
        "crew_size": 4,
        "predecessor_type": "structural",
    },
    "IfcDoor": {
        "rate_per_each": 0.25,
        "crew_size": 2,
        "predecessor_type": "architectural",
    },
    "IfcWindow": {
        "rate_per_each": 0.30,
        "crew_size": 2,
        "predecessor_type": "architectural",
    },
    "IfcSlab": {
        "rate_per_m2": 0.08,
        "crew_size": 6,
        "predecessor_type": "foundation",
    },
    "IfcColumn": {
        "rate_per_m3": 0.50,
        "crew_size": 4,
        "predecessor_type": "foundation",
    },
    "IfcBeam": {
        "rate_per_m": 0.15,
        "crew_size": 4,
        "predecessor_type": "structural",
    },
}
