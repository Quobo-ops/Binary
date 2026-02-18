# Phase 15: Augmented Reality Field Visualization Layer
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 9 (Clash Validation), 11 (Visualization Bridge); Phases 2 (As-Built), 4 (Mobile Field Interface)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Extends the Visualization Bridge to deliver mobile AR overlays for on-site design-intent verification, clash checking, and installation guidance. Using WebXR and the device camera, field teams can see the digital model superimposed on the physical jobsite — comparing what should be there with what is actually there, in real time.

## Goal

Give field teams the ability to "see through walls" by overlaying the design model onto the real-world jobsite through their smartphone or tablet camera. No special hardware, no dedicated AR headset — the same device running FIELD.html (Phase 4) gains AR capabilities through progressive enhancement.

## Core Capabilities

### 1. WebXR-Based AR Overlay

Browser-native augmented reality using the WebXR API:

```javascript
// Progressive enhancement — AR activates on supported devices
if (navigator.xr && await navigator.xr.isSessionSupported('immersive-ar')) {
    // Full AR experience
    const session = await navigator.xr.requestSession('immersive-ar', {
        requiredFeatures: ['hit-test', 'dom-overlay'],
        domOverlay: { root: document.getElementById('overlay') }
    });
    // Load glTF model into AR scene
    // Anchor to physical reference points
} else {
    // Fallback: Camera feed + manual model overlay
}
```

### 2. Design-Intent Verification

Compare digital model against physical reality:

```
Field Verification Workflow:
  1. Open FIELD.html on smartphone at element location
  2. Tap "AR Verify" button
  3. Camera activates with model overlay
  4. System shows design intent as translucent 3D overlay
  5. User visually compares overlay to installed element
  6. Tap "Matches" or "Deviation" to log result
  7. If deviation: capture photo + voice note of discrepancy
```

**Visual Indicators:**
- **Green overlay** — Design matches installed (within tolerance)
- **Yellow overlay** — Minor deviation detected (within tolerance)
- **Red overlay** — Significant deviation (outside tolerance)
- **Blue overlay** — Element not yet installed (shows where it should go)

### 3. AR Clash Checking

Real-time clash detection between installed elements and upcoming work:

```markdown
## AR Clash Alerts (at current location)

| Clash | Elements | Type | Severity |
|-------|----------|------|----------|
| CL-042 | HVAC duct vs. beam B-201 | Hard clash | 🔴 Critical |
| CL-043 | Sprinkler pipe vs. light fixture | Soft clash (2" clearance) | 🟡 Warning |
| CL-044 | Conduit path vs. wall cavity | Constructability | 🟡 Warning |

Tap any clash to see 3D visualization in AR view.
```

### 4. Installation Guidance

Step-by-step AR guidance for complex installations:

```
Installation Guide: Storefront Glazing at Grid B-4

Step 1: Verify blocking locations (shown in blue)
  → AR overlay shows: 2×4 blocking at 48" o.c.
  → Tap to confirm each blocking location

Step 2: Check opening dimensions (shown in green)
  → AR overlay shows: 72" W × 96" H opening
  → Measurement tool available for verification

Step 3: Review anchorage points (shown in yellow)
  → AR overlay shows: anchor bolt locations
  → Spacing: 24" o.c. both sides

Step 4: Verify clearances (shown with dotted lines)
  → Minimum 1/4" sealant joint all sides
  → AR overlay shows required gap dimensions
```

### 5. Spatial Anchoring

Methods for aligning the digital model to the physical space:

| Method | Accuracy | Requirements | Best For |
|--------|----------|-------------|----------|
| QR Code Anchors | ±1/4" | Printed QR at known locations | Individual elements |
| GPS + Compass | ±3 feet | Device GPS | Exterior, site-scale |
| Manual Placement | User-dependent | Touch interaction | Quick verification |
| Image Recognition | ±1" | Pre-captured reference photos | Repeat visits |
| LiDAR Scan | ±1/8" | Device with LiDAR (iPad Pro) | Precision work |

### 6. Measurement Tools

AR-integrated measurement capabilities:

- **Point-to-point** — Tap two points in AR to measure distance
- **Level check** — Digital level overlay on camera view
- **Plumb check** — Vertical alignment verification
- **Square check** — 90° corner verification
- **Height verification** — Measure floor-to-element height

## Architecture

### Module Structure
```
aecos/ar/
├── __init__.py
├── ar_generator.py          # AR scene builder from Element data
├── anchor_manager.py        # Spatial anchoring strategies
├── clash_visualizer.py      # AR clash visualization
├── install_guide.py         # Step-by-step AR guidance generator
├── measurement_tools.py     # AR measurement utilities
├── model_optimizer.py       # glTF optimization for AR performance
└── templates/
    ├── ar_viewer.html.j2    # AR-enabled HTML template
    ├── ar_overlay.js        # AR overlay logic
    ├── ar_measurement.js    # Measurement tool logic
    └── ar_styles.css        # AR UI styles
```

### Integration with FIELD.html (Phase 4)

AR capabilities are added as a progressive enhancement to the existing FIELD.html:

```html
<!-- Added to FIELD.html when AR is available -->
<button id="ar-verify" class="field-action-btn"
        style="display: none;"
        onclick="startARVerification()">
    AR Verify
</button>

<script>
// Feature detection
if (navigator.xr) {
    navigator.xr.isSessionSupported('immersive-ar').then(supported => {
        if (supported) {
            document.getElementById('ar-verify').style.display = 'block';
        }
    });
}
</script>
```

### AecOS Facade Integration
```python
# Generate AR-enabled FIELD.html
os.generate_field_interface(element_id="W-EXT-01", ar_enabled=True)

# Generate AR installation guide
os.generate_ar_guide(element_id="GLAZ-B4", steps=True)

# Generate AR anchor markers
os.generate_ar_anchors(project_id="XYZ", locations=["grid_A1", "grid_B4"])

# Optimize models for AR
os.optimize_for_ar(element_id="W-EXT-01", target_triangles=5000)
```

### Data Flow
```
Element Folder (IFC + glTF from Item 11)
    ↓
AR Generator → Optimized glTF + anchor data
    ↓
FIELD.html (Phase 4) → AR button added
    ↓
User taps "AR Verify" on smartphone
    ↓
WebXR session starts → Camera + model overlay
    ↓
User interaction → Verification/measurement logged
    ↓
As-Built Logger (Phase 2) → Git commit
```

## Performance Requirements

| Metric | Target | Rationale |
|--------|--------|-----------|
| AR model load time | <3 seconds | User patience threshold |
| Frame rate | ≥30 fps | Smooth AR experience |
| Model triangle count | <50k per element | Mobile GPU limits |
| Anchor accuracy | ±1" (QR), ±3' (GPS) | Construction tolerance |
| Battery impact | <15% per hour of AR use | Full-shift usability |

## Deliverables

- [ ] `aecos/ar/` module with AR generation pipeline
- [ ] WebXR-based AR viewer integrated into FIELD.html
- [ ] QR-based spatial anchoring system
- [ ] AR clash visualization from existing clash data
- [ ] Step-by-step AR installation guide generator
- [ ] AR measurement tools (distance, level, plumb, square)
- [ ] glTF model optimizer for mobile AR performance
- [ ] Fallback: Camera + manual overlay for non-WebXR devices
- [ ] CLI command: `aecos ar generate <element-id>`
- [ ] CLI command: `aecos ar anchors --project <id>`
- [ ] CLI command: `aecos ar optimize <element-id> --triangles <max>`

## Testing Strategy

```bash
# Unit tests for model optimization and anchor generation
pytest tests/test_ar.py

# Integration: Element → AR model → FIELD.html → AR session
pytest tests/integration/test_ar_pipeline.py

# Performance: Model size and load time validation
pytest tests/benchmark/test_ar_performance.py
```

## Bible Compliance Checklist

- [x] Local-first: AR runs entirely on device, no cloud rendering
- [x] Git SoT: AR verification results committed as field observations
- [x] Pure-file: glTF models, HTML viewer — no proprietary format
- [x] Cryptographic audit: AR verifications logged via AuditLogger
- [x] Revit compatible: AR models derived from IFC-sourced glTF
- [x] Legal/financial first: AR verification creates auditable field record

---

**Dependency Chain:** Items 9, 11 + Phases 2, 4 → This Module
**Next Phase:** Phase 16 (Firm-Wide Portfolio and Multi-Project Governance)
