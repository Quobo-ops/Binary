# Phase 4: Zero-Install Mobile Field Interface
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 4 (VCS), 6 (NLParser), 11 (Visualization Bridge), 15 (Git Ops), 17 (Security & Audit); Phases 1–3
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Creates a self-contained, browser-based `FIELD.html` application per Element that supports QR-code scanning, voice input, offline operation with automatic sync, and visual traffic-light status indicators for immediate foreman adoption. Zero app store, zero login, zero training — open on any smartphone and start working.

## Goal

Deliver a one-tap mobile field experience that is self-contained and requires zero installation. The Visualization Bridge (Item 11) generates, inside every Element folder, a single `FIELD.html` file that opens on any smartphone browser and provides full read/write access to the element's digital thread.

## Core Capabilities

### 1. Self-Contained HTML Application

A single `FIELD.html` file per Element folder containing:

- **All logic embedded** — No CDN dependencies, no external scripts
- **Progressive enhancement** — Core functionality works on any browser; advanced features (voice, camera) activate when available
- **Responsive layout** — Optimized for 4"–7" phone screens in portrait mode
- **Dark/light mode** — Automatic based on ambient light or manual toggle

### 2. QR Code Scanning

Browser-native camera access for scanning element QR tags:

```javascript
// Uses getUserMedia + jsQR library (embedded, client-side)
// No app installation required
navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
    .then(stream => { /* jsQR processing */ })
```

- **Scan → Instant context** — QR code on physical element links to its FIELD.html
- **Chain scanning** — Scan multiple elements in sequence for batch logging
- **QR generation** — Print tags from the handover package (Phase 3)

### 3. Voice Input

Web Speech API for hands-free field logging:

```javascript
// Progressive enhancement — works where available
const recognition = new webkitSpeechRecognition();
recognition.continuous = false;
recognition.lang = 'en-US';
// Transcript → NLParser processing
```

- **Tap-and-talk** — Single button press, speak observation
- **Confirmation before commit** — Shows parsed intent for approval
- **Fallback** — Text input always available when voice unavailable

### 4. Offline Operation with Automatic Sync

Full offline capability via Service Worker + IndexedDB:

```
Online Flow:
  FIELD.html → Read/Write → Git (via existing Git ops, Item 15)

Offline Flow:
  FIELD.html → Read/Write → IndexedDB (local queue)
  ... connectivity restored ...
  Service Worker → git pull / git push → Sync complete
  Conflict? → Flag for manual resolution
```

- **Queue all changes locally** — IndexedDB stores pending commits
- **Automatic sync on reconnect** — Service Worker detects connectivity
- **Conflict resolution** — Visual diff if remote has diverged
- **Sync status indicator** — Green (synced), yellow (pending), red (conflict)

### 5. Traffic-Light Status Indicators

Visual, at-a-glance status for every element:

| Color | Meaning | Action |
|-------|---------|--------|
| 🟢 Green | Installed, verified, compliant | No action needed |
| 🟡 Yellow | Deviation detected, under review | Review required |
| 🔴 Red | Non-compliant, blocked, or failed | Immediate action |
| ⚪ Gray | Not yet installed | Awaiting field work |
| 🔵 Blue | Substitution proposed | Approval pending |

### 6. One-Tap Action Buttons

Pre-built actions requiring no typing:

- **"Mark Installed"** — Logs installation with timestamp and user
- **"Propose Substitution"** — Opens Phase 1 substitution flow
- **"Log Issue"** — Opens free-text/voice observation entry
- **"View Spec"** — Shows current design spec, cost, compliance status
- **"View 3D"** — Loads glTF preview (model-viewer web component)
- **"Photo Attach"** — Camera capture attached to current entry

## Architecture

### File Structure (per Element)
```
Elements/W-EXT-01/
├── ... (existing files)
├── FIELD.html              # Self-contained mobile interface
├── FIELD_STATUS.md         # Machine-readable status (from Phase 2)
├── field_assets/
│   ├── sw.js               # Service Worker for offline
│   ├── style.css           # Embedded styles (also inline in HTML)
│   └── model.gltf          # 3D preview model (from Item 11)
```

### FIELD.html Generation
```python
# Extension to Visualization Bridge (Item 11)
class FieldHtmlGenerator:
    def generate(self, element_folder: Path) -> Path:
        """Generate FIELD.html for an element folder."""
        # Load element data
        spec = self._load_spec(element_folder)
        status = self._load_field_status(element_folder)
        model_path = self._find_gltf(element_folder)

        # Render self-contained HTML
        html = self._render_template(
            spec=spec,
            status=status,
            model_path=model_path,
            qr_scanner=True,
            voice_input=True,
            offline_support=True
        )

        output = element_folder / "FIELD.html"
        output.write_text(html)
        return output
```

### AecOS Facade Integration
```python
# Generate FIELD.html for all elements
os.generate_field_interfaces(project_id="XYZ")

# Generate for single element
os.generate_field_interface(element_id="W-EXT-01")

# Regenerate after status change
os.refresh_field_status(element_id="W-EXT-01")
```

### Technology Stack (All Client-Side)

| Feature | Library/API | Fallback |
|---------|------------|----------|
| QR Scanning | jsQR + getUserMedia | Manual element ID entry |
| Voice Input | Web Speech API | Text input field |
| 3D Preview | model-viewer (Google) | Static image |
| Offline Storage | IndexedDB + Service Worker | Online-only mode |
| Sync | Background Sync API | Manual sync button |
| Camera/Photos | MediaStream Image Capture | File upload input |

## User Experience Flow

```
Foreman arrives at element on site
    ↓
Scans QR tag with phone camera (or opens bookmarked FIELD.html)
    ↓
Sees: Traffic-light status + current spec + one-tap actions
    ↓
Taps "Mark Installed" or "Log Issue" or "Propose Substitution"
    ↓
Speaks or types observation
    ↓
Sees parsed intent → Confirms → Commit created
    ↓
If online: Synced immediately
If offline: Queued → synced when connectivity returns
```

## Deliverables

- [ ] `FIELD.html` generator integrated into Visualization Bridge
- [ ] Service Worker with IndexedDB offline queue
- [ ] QR code scanner (jsQR, client-side only)
- [ ] Voice input integration (Web Speech API, progressive)
- [ ] Traffic-light status rendering from FIELD_STATUS.md
- [ ] One-tap action buttons (Install, Substitute, Issue, Spec, 3D, Photo)
- [ ] Automatic sync on reconnect with conflict detection
- [ ] Responsive mobile-first CSS (4"–7" screens)
- [ ] CLI command: `aecos field-html <element-id>` or `aecos field-html --all`
- [ ] No external dependencies — fully self-contained HTML

## Testing Strategy

```bash
# Unit tests for HTML generation
pytest tests/test_field_html.py

# Browser tests (Playwright/Selenium)
pytest tests/browser/test_field_interface.py

# Offline simulation tests
pytest tests/browser/test_offline_sync.py
```

## Bible Compliance Checklist

- [x] Local-first: Entire HTML app runs client-side, no server required
- [x] Git SoT: All field entries become Git commits (online or queued)
- [x] Pure-file: Single HTML file + optional assets, no database
- [x] Cryptographic audit: Commits signed via existing KeyManager
- [x] Revit compatible: No impact on IFC data; supplements existing files
- [x] Legal/financial first: All field entries auditable and traceable

---

**Dependency Chain:** Phases 1–3 + Items 4, 6, 11, 15, 17 → This Module
**Next Phase:** Phase 5 (Contractor-Specific Natural-Language Context Engine)
