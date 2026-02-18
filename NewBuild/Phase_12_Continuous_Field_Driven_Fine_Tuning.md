# Phase 12: Continuous Field-Driven Fine-Tuning Loop
**AEC OS v2.0 — The Full Lifecycle Platform**
**Status:** Planned
**Date:** 2026-02-18
**Builds On:** Items 6 (NLParser), 13 (Fine-Tuning Loop); Phases 1–5 (contractor data sources), Phase 11 (FM data)
**Bible Compliance:** 100 % — Local-first, Git SoT, pure-file, cryptographic audit, Revit-compatible, legal/financial correctness

---

## Overview

Automates the capture of contractor corrections and field observations to drive local model fine-tuning, closing the learning loop across all user roles. The system learns not just from designers but from every field correction, substitution outcome, deviation resolution, and maintenance observation — making the AI continuously smarter about real-world construction.

## Goal

Extend the existing Fine-Tuning Loop (Item 13) to ingest field-generated data as training signal. Every time a contractor corrects a parse, a foreman provides a better description, a substitution succeeds or fails, or an as-built deviation reveals a pattern — that knowledge flows back into the local model, improving future predictions for all roles.

## Core Capabilities

### 1. Multi-Role Training Data Capture

Automated capture from every user interaction:

| Data Source | Training Signal | Example |
|-------------|----------------|---------|
| NL parse corrections | "I said X, system understood Y, correct answer is Z" | "Sister" = reinforce, not "sibling" |
| Substitution outcomes | Approved substitutions with final cost/performance data | ICF outperformed CMU by 12% |
| As-built deviations | Common deviation patterns by element type/trade | Slab pours consistently +1/4" |
| Change order patterns | Frequent change types by project/region/season | Louisiana: hurricane prep COs spike Aug–Oct |
| Approval decisions | What gets approved/rejected and why | Owner rejects substitutions >10% cost increase |
| Work order resolutions | How issues were actually fixed | "Grinding noise" = worn belt, not bearing failure |
| Performance data | Design predictions vs. actual performance | Energy model was 6% conservative |

### 2. Automatic Training Dataset Curation

Intelligent filtering and formatting of raw field data:

```python
class FieldDataCurator:
    def curate(self, raw_observations: list) -> TrainingDataset:
        """Transform field data into structured training examples."""
        examples = []
        for obs in raw_observations:
            # Filter: Only use verified, approved observations
            if not obs.is_verified:
                continue

            # Quality gate: Minimum confidence threshold
            if obs.confidence < 0.80:
                self._flag_for_human_review(obs)
                continue

            # Format: Input → Expected output pair
            example = TrainingExample(
                input_text=obs.original_command,
                expected_output=obs.corrected_spec,
                context=obs.role_context,
                domain=obs.trade_domain,
                weight=self._calculate_weight(obs)
            )
            examples.append(example)

        return TrainingDataset(
            examples=examples,
            source="field_observations",
            version=self._next_version(),
            created=datetime.now()
        )
```

### 3. Incremental Fine-Tuning Pipeline

Extends Item 13 with field-specific training:

```
Data Collection (continuous)
    ↓
Quality Filtering (automated + human review)
    ↓
Dataset Assembly (versioned, Git-stored)
    ↓
LoRA/QLoRA Fine-Tuning (local, consumer GPU)
    ↓
Evaluation (AEC benchmarks + field-specific tests)
    ↓
A/B Comparison (new model vs. current)
    ↓
Deployment with Rollback (Git-versioned model weights)
```

### 4. Role-Specific Model Adaptation

The fine-tuning process can produce role-optimized model variants:

| Variant | Optimized For | Training Emphasis |
|---------|--------------|-------------------|
| Base | All roles | General AEC + code compliance |
| Contractor | Field operations | Trade vocabulary, installation methods |
| Estimator | Cost analysis | Material pricing, labor estimation |
| FM | Facility management | Maintenance, diagnostics, warranties |

All variants share the same base architecture — role context selects the appropriate LoRA adapter at inference time.

### 5. Feedback Quality Gates

Ensuring training data doesn't degrade model quality:

- **Verified only** — Only use observations that passed compliance re-check
- **Consensus required** — Conflicting corrections flagged for human review
- **Statistical validation** — Detect and exclude outliers
- **Regression testing** — New model must pass all existing benchmarks
- **Rollback trigger** — Automatic revert if accuracy drops >2%

### 6. Cross-Project Learning

Anonymized patterns shared across projects (within the same firm):

```
Project A: "Louisiana clay soil consistently requires 18" deeper footings than code minimum"
Project B: "Baton Rouge area — confirm same deep footing pattern"
→ System learns: Louisiana clay soil → suggest 18" footing depth increase
→ Applied to Project C automatically (as suggestion, not override)
```

## Architecture

### Module Structure
```
aecos/finetune/
├── ... (existing Item 13 files)
├── field_curator.py         # Field data curation engine
├── role_adapter.py          # Role-specific LoRA adapter management
├── quality_gate.py          # Training data quality validation
├── cross_project.py         # Anonymized cross-project pattern learning
├── feedback_collector.py    # Automated feedback capture from all phases
└── training_data/
    ├── field_observations/  # Git-versioned training datasets
    ├── substitution_outcomes/
    ├── deviation_patterns/
    └── performance_actuals/
```

### AecOS Facade Integration
```python
# Capture feedback
os.log_correction(element_id="W-EXT-01", original="...", corrected="...")
os.log_outcome(substitution_id="SUB-001", outcome="success", metrics={...})

# Training pipeline
os.curate_training_data(source="field", min_confidence=0.80)
os.fine_tune(dataset="field_observations_v3", adapter="contractor")
os.evaluate_model(adapter="contractor", benchmark="field_accuracy")

# Model management
os.active_adapters()  # List active LoRA adapters
os.rollback_adapter(adapter="contractor", to_version="v2")
```

## Deliverables

- [ ] Field data curation engine with quality gates
- [ ] Multi-role training data capture from Phases 1–11
- [ ] Role-specific LoRA adapter management
- [ ] Incremental fine-tuning pipeline (extends Item 13)
- [ ] Cross-project pattern learning (anonymized)
- [ ] Regression testing suite for model quality
- [ ] Automatic rollback on accuracy degradation
- [ ] Training data versioning in Git
- [ ] CLI command: `aecos finetune curate --source field`
- [ ] CLI command: `aecos finetune train --adapter contractor`
- [ ] CLI command: `aecos finetune evaluate --adapter contractor`
- [ ] CLI command: `aecos finetune rollback --adapter contractor --to v2`

## Testing Strategy

```bash
# Unit tests for curation and quality gates
pytest tests/test_finetune_field.py

# Integration: Field data → Curation → Training → Evaluation
pytest tests/integration/test_finetune_pipeline.py

# Regression: Ensure new model doesn't degrade
pytest tests/test_model_regression.py
```

## Bible Compliance Checklist

- [x] Local-first: All training and inference on local hardware
- [x] Git SoT: Training data and model weights versioned in Git
- [x] Pure-file: Training datasets as JSON files, model weights as binary
- [x] Cryptographic audit: Training runs logged via AuditLogger
- [x] Revit compatible: Model improvements transparent to IFC pipeline
- [x] Legal/financial first: No training on unverified data

---

**Dependency Chain:** Items 6, 13 + Phases 1–5, 11 → This Module
**Next Phase:** Phase 13 (Dynamic Regional Material and Supplier Catalog)
