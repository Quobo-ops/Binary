# Phase 18: Commercial Packaging and Distribution Strategy
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 18 (Deployment Pipeline); All Phases 1–17 (complete platform)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Develops tiered licensing models, one-click installers, documentation, and go-to-market assets to support both individual practitioners and multi-user firms. This phase transforms AEC OS from an internal tool into a commercially viable product while preserving every architectural principle that makes it valuable.

## Goal

Package AEC OS v2.0 into a product that can be sold, deployed, and supported at scale. This means professional installation, clear licensing, comprehensive documentation, and a distribution strategy that serves solo practitioners, small firms, and enterprise teams — all without compromising the local-first, Git-based architecture.

## Core Capabilities

### 1. Tiered Licensing Model

```markdown
## AEC OS v2.0 — Product Tiers

### Solo Practitioner ($X/month)
- Single user license
- Full design pipeline (Items 1–19)
- Phases 1–5 (contractor basics)
- Phase 10 (project dashboard)
- Community templates
- Email support

### Small Firm (up to 10 users, $X/user/month)
- Everything in Solo, plus:
- Phases 6–9 (full construction management)
- Phase 11 (facility management)
- Phases 13–14 (catalogs + sustainability)
- Multi-user sync (Item 12)
- Collaboration layer (Item 16)
- Firm template governance (Phase 16, basic)
- Priority support

### Enterprise (unlimited users, custom pricing)
- Everything in Small Firm, plus:
- All 20 phases
- Full portfolio governance (Phase 16)
- Ecosystem integrations (Phase 17)
- Custom template development
- On-site training
- Dedicated support engineer
- SLA guarantees
```

### 2. One-Click Installer

Platform-specific installers that handle all dependencies:

| Platform | Installer Type | Includes |
|----------|---------------|----------|
| Windows 10/11 | MSI + WinGet | Python 3.11+, Git, aecos package, templates |
| macOS (Intel/ARM) | .pkg + Homebrew | Python 3.11+, Git, aecos package, templates |
| Linux (Ubuntu/RHEL) | .deb/.rpm + apt/yum | Python 3.11+, Git, aecos package, templates |
| Docker | Docker image | Complete environment, ready to run |
| Cloud | Terraform/Pulumi | AWS/GCP/Azure deployment scripts |

```bash
# Windows (PowerShell)
winget install aecos

# macOS
brew install aecos

# Linux
sudo apt install aecos  # or: sudo yum install aecos

# Docker
docker run -v $(pwd):/project aecos/aecos:v2.0

# From source (any platform)
pip install aecos[full]
```

### 3. Post-Install Setup Wizard

Guided first-run experience:

```
Welcome to AEC OS v2.0!

Step 1/5: License Activation
  → Enter license key or start trial

Step 2/5: User Profile
  → Name, firm, role (designer/contractor/owner)
  → Louisiana registration number (optional)

Step 3/5: Git Configuration
  → Initialize project repository
  → Configure signing keys

Step 4/5: Template Library
  → Download firm templates (if applicable)
  → Select regional template packs (Louisiana, National)

Step 5/5: Integration Setup (optional)
  → Connect Procore, ACC, ERP (skip for now)

Setup complete! Run 'aecos tutorial' for a 5-minute walkthrough.
```

### 4. Comprehensive Documentation

```
docs/
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md          # 5-minute first element
│   ├── tutorial-designer.md    # Designer workflow tutorial
│   ├── tutorial-contractor.md  # Contractor workflow tutorial
│   └── tutorial-owner.md       # Owner/FM workflow tutorial
├── user-guide/
│   ├── cli-reference.md        # Complete CLI documentation
│   ├── natural-language.md     # NL command reference
│   ├── templates.md            # Working with templates
│   ├── field-operations.md     # Phases 1–4 field guide
│   ├── change-orders.md        # Phase 6 guide
│   ├── scheduling.md           # Phase 7 guide
│   ├── approvals.md            # Phase 8 guide
│   ├── handover.md             # Phase 3 guide
│   ├── facility-management.md  # Phase 11 guide
│   └── integrations.md         # Phase 17 guide
├── admin-guide/
│   ├── firm-setup.md           # Multi-user firm configuration
│   ├── template-governance.md  # Phase 16 governance guide
│   ├── security.md             # Security configuration
│   ├── backup-recovery.md      # Backup and disaster recovery
│   └── troubleshooting.md      # Common issues and solutions
├── api-reference/
│   ├── facade-api.md           # AecOS facade complete reference
│   ├── python-api.md           # Python package API docs
│   └── cli-api.md              # CLI argument reference
└── release-notes/
    └── v2.0.md                 # Version 2.0 release notes
```

### 5. Training Materials

```
training/
├── videos/
│   ├── 01-installation.mp4     # 5 min install + setup
│   ├── 02-first-element.mp4    # 10 min first element creation
│   ├── 03-contractor-basics.mp4 # 15 min contractor workflow
│   ├── 04-field-operations.mp4  # 20 min field guide
│   └── 05-advanced-topics.mp4   # 30 min advanced features
├── workshops/
│   ├── designer-half-day.md    # 4-hour designer workshop outline
│   ├── contractor-half-day.md  # 4-hour contractor workshop outline
│   └── admin-full-day.md       # 8-hour admin workshop outline
└── quick-reference/
    ├── designer-cheatsheet.pdf  # 2-page designer quick reference
    ├── contractor-cheatsheet.pdf # 2-page contractor quick reference
    └── cli-cheatsheet.pdf       # 2-page CLI quick reference
```

### 6. Go-to-Market Assets

```
marketing/
├── product-overview.pdf         # 4-page product overview
├── case-study-template.md       # Template for client case studies
├── roi-calculator.xlsx          # ROI projection tool for prospects
├── comparison-matrix.md         # AEC OS vs. competitors
├── demo-script.md               # Standardized demo walkthrough
└── pricing-proposal-template.md # Client proposal template
```

## Architecture

### Module Structure
```
aecos/packaging/
├── __init__.py
├── license_manager.py       # License validation and tier enforcement
├── installer_builder.py     # Cross-platform installer generation
├── setup_wizard.py          # First-run guided setup
├── update_manager.py        # Version checking and update delivery
├── telemetry.py             # Optional, anonymized usage telemetry
└── config/
    ├── tiers.json           # License tier definitions
    ├── features.json        # Feature-to-tier mapping
    └── installer/
        ├── windows/
        ├── macos/
        └── linux/
```

### License Enforcement (Lightweight)
```python
class LicenseManager:
    def check_feature(self, feature: str) -> bool:
        """Check if current license tier includes a feature."""
        tier = self._get_active_tier()
        return feature in TIER_FEATURES[tier]

    def enforce(self, feature: str):
        """Raise if feature not in current tier."""
        if not self.check_feature(feature):
            raise LicenseTierError(
                f"'{feature}' requires {self._required_tier(feature)} tier. "
                f"Current tier: {self._get_active_tier()}. "
                f"Upgrade at https://aecos.dev/upgrade"
            )
```

## Deliverables

- [ ] `aecos/packaging/` module with licensing and installation
- [ ] Tiered licensing model definition and enforcement
- [ ] Windows MSI installer (WinGet package)
- [ ] macOS .pkg installer (Homebrew formula)
- [ ] Linux .deb and .rpm packages
- [ ] Docker image with complete environment
- [ ] Post-install setup wizard
- [ ] Version update manager with rollback
- [ ] Complete user documentation (getting started, guides, API reference)
- [ ] Training video scripts and outlines
- [ ] Quick-reference cheat sheets for each role
- [ ] Go-to-market materials (overview, ROI calculator, demo script)
- [ ] CLI command: `aecos license activate <key>`
- [ ] CLI command: `aecos license status`
- [ ] CLI command: `aecos update check`
- [ ] CLI command: `aecos tutorial`

## Testing Strategy

```bash
# License tier enforcement tests
pytest tests/test_licensing.py

# Installer build verification
pytest tests/test_installer_build.py

# Setup wizard flow tests
pytest tests/test_setup_wizard.py

# Cross-platform installation smoke tests
pytest tests/test_installation_smoke.py
```

## Bible Compliance Checklist

- [x] Local-first: License validation works offline (periodic online check)
- [x] Git SoT: No license data stored in Git; separate encrypted file
- [x] Pure-file: License file is encrypted JSON — no license server required
- [x] Cryptographic audit: License activations logged
- [x] Revit compatible: Installation includes Revit plugin/pyRevit integration
- [x] Legal/financial first: Clear licensing terms, EULA, data policy

---

**Dependency Chain:** Item 18 + All Phases 1–17 → This Module
**Next Phase:** Phase 19 (Controlled Template Exchange Network)
