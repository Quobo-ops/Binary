"""Embedded golden test prompts + expected outputs for model evaluation."""

from __future__ import annotations

from typing import Any

# 30 golden test cases covering the full range of AEC specifications
GOLDEN_TEST_SET: list[dict[str, Any]] = [
    # --- Walls ---
    {
        "prompt": "150mm concrete wall, 3 meters tall, 5 meters long",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "properties": {"thickness_mm": 150.0, "height_mm": 3000.0, "length_mm": 5000.0},
            "materials": ["concrete"],
        },
    },
    {
        "prompt": "2-hour fire-rated concrete wall, 12 feet tall",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "materials": ["concrete"],
            "performance": {"fire_rating": "2H"},
        },
    },
    {
        "prompt": "exterior insulated steel stud wall with gypsum board",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "materials": ["steel", "gypsum"],
        },
    },
    {
        "prompt": "200mm masonry wall, load bearing, 4m high",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "properties": {"thickness_mm": 200.0, "height_mm": 4000.0},
            "materials": ["masonry"],
        },
    },
    {
        "prompt": "acoustic partition wall STC 55",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "performance": {"acoustic_stc": 55},
        },
    },
    # --- Doors ---
    {
        "prompt": "standard interior door, 36 inches wide, 7 feet tall",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcDoor",
            "properties": {"width_mm": 914.4, "height_mm": 2133.6},
        },
    },
    {
        "prompt": "fire-rated door, 90 minutes, 1200mm wide",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcDoor",
            "properties": {"width_mm": 1200.0},
            "performance": {"fire_rating": "1.5H"},
        },
    },
    {
        "prompt": "ADA compliant accessible door with lever handle, 42 inch clear",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcDoor",
            "constraints": {"accessibility": True},
        },
    },
    # --- Windows ---
    {
        "prompt": "double-hung window, 3 feet wide, 5 feet tall, low-E glass",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWindow",
            "materials": ["glass"],
        },
    },
    {
        "prompt": "curtain wall window panel, 2m by 3m, triple glazed",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWindow",
            "properties": {"width_mm": 2000.0, "height_mm": 3000.0},
        },
    },
    {
        "prompt": "energy efficient window, Title-24 compliant, R-5",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWindow",
            "performance": {"thermal_r_value": 5.0},
            "compliance_codes": ["Title-24"],
        },
    },
    # --- Slabs ---
    {
        "prompt": "200mm reinforced concrete slab, 10m by 8m",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcSlab",
            "properties": {"thickness_mm": 200.0},
            "materials": ["concrete"],
        },
    },
    {
        "prompt": "150mm post-tensioned concrete floor slab, 6 inch thick",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcSlab",
            "materials": ["concrete"],
        },
    },
    {
        "prompt": "roof slab with waterproof membrane, 250mm thick",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcSlab",
            "properties": {"thickness_mm": 250.0},
        },
    },
    # --- Columns ---
    {
        "prompt": "steel W14x90 column, 4 meters tall",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcColumn",
            "properties": {"height_mm": 4000.0},
            "materials": ["steel"],
        },
    },
    {
        "prompt": "400mm round concrete column, 3.5m height",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcColumn",
            "properties": {"height_mm": 3500.0},
            "materials": ["concrete"],
        },
    },
    {
        "prompt": "timber post column, 200mm square, 2.7m",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcColumn",
            "materials": ["timber"],
        },
    },
    # --- Beams ---
    {
        "prompt": "steel I-beam, W12x26, 6 meter span",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcBeam",
            "materials": ["steel"],
        },
    },
    {
        "prompt": "reinforced concrete beam, 300mm wide, 600mm deep, 8m span",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcBeam",
            "properties": {"width_mm": 300.0, "depth_mm": 600.0},
            "materials": ["concrete"],
        },
    },
    {
        "prompt": "glulam timber beam, 150mm x 400mm, 5m long",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcBeam",
            "materials": ["timber"],
        },
    },
    # --- Fire rating specifications ---
    {
        "prompt": "1-hour fire-rated wall assembly, Type X gypsum both sides",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "performance": {"fire_rating": "1H"},
            "materials": ["gypsum"],
        },
    },
    {
        "prompt": "3-hour fire-rated column enclosure, concrete",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcColumn",
            "performance": {"fire_rating": "3H"},
            "materials": ["concrete"],
        },
    },
    # --- Accessibility ---
    {
        "prompt": "ADA accessible ramp, 1:12 slope, 36 inch width",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcSlab",
            "constraints": {"accessibility": True},
        },
    },
    # --- Energy codes ---
    {
        "prompt": "wall insulation R-19, California Title-24 Zone 3",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "performance": {"thermal_r_value": 19.0},
            "compliance_codes": ["Title-24"],
        },
    },
    {
        "prompt": "roof insulation assembly, R-38, IBC 2024 compliant",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcSlab",
            "compliance_codes": ["IBC2024"],
        },
    },
    # --- Structural requirements ---
    {
        "prompt": "seismic category D shear wall, 250mm concrete, California",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "materials": ["concrete"],
            "constraints": {"structural": True},
        },
    },
    # --- Imperial and metric dimensions ---
    {
        "prompt": "8 inch CMU block wall, 10 feet tall, 20 feet long",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
            "materials": ["masonry"],
        },
    },
    {
        "prompt": "600mm x 600mm concrete column, height 3600mm",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcColumn",
            "properties": {"height_mm": 3600.0},
            "materials": ["concrete"],
        },
    },
    # --- Ambiguous input ---
    {
        "prompt": "wall",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcWall",
        },
    },
    {
        "prompt": "make a big beam for the lobby",
        "expected": {
            "intent": "create",
            "ifc_class": "IfcBeam",
        },
    },
]
