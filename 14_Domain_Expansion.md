**Domain Expansion (Roadmap Item 14)**  
**Goal:** Systematically extend the `aecos` ecosystem to support additional AEC disciplines by creating modular, reusable domain-specific components for template handling, parametric generation, compliance validation, cost and schedule estimation, clash detection, visualization, and natural-language parsing, thereby enabling the system to manage complete multi-disciplinary projects from a single unified codebase while preserving traceability and version control across all domains.

**Target Domains for Version 1.0 (Prioritized by Complexity and Immediate Value)**  
- Structural Engineering (beams, columns, slabs, foundations, steel framing)  
- Mechanical, Electrical, and Plumbing (MEP) systems (HVAC ducts, piping, electrical conduits, fixtures)  
- Interior Finishes and Fit-Out (partitions, ceilings, flooring, millwork)  
- Site and Civil Works (grading, paving, retaining walls, utilities)  
- Landscape Architecture (planting, hardscaping, irrigation)  
- Fire Protection and Suppression Systems  

**Integration Points**  
- All new domains plug directly into the existing `aecos.core` modules (library, generator, compliance engine, validator, cost engine, parser, visualization bridge).  
- Automatic registration through a central `DomainRegistry`.  
- Full reuse of Items 1–13 infrastructure with domain-specific overrides.

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–13.  
- `aecos` package installed in editable mode.  
- Existing template library containing at least 50 architectural elements for baseline testing.  
- `pip install` already satisfied from prior items (no new dependencies required).

**Phase 1: Modular Domain Framework (Day 1)**  
Introduce a plugin architecture in `aecos/domains/`:  
```python
# aecos/domains/base.py
from abc import ABC, abstractmethod
from pathlib import Path

class DomainBase(ABC):
    name: str
    ifc_classes: list[str]
    default_region: str = "US"

    @abstractmethod
    def register_templates(self) -> None:
        pass

    @abstractmethod
    def register_compliance_rules(self) -> None:
        pass

    @abstractmethod
    def register_parser_examples(self) -> None:
        pass
```

Create `aecos/domains/registry.py` to auto-discover and load domains on package import.

**Phase 2: Structural Domain Implementation (Day 1–2)**  
- Add 30+ new templates (e.g., `steel_W12x26_beam_us_2025`, `concrete_slab_200mm_fire2hr_ca`).  
- Extend `ParametricSpec` with structural parameters (`span_m`, `load_kN`, `steel_grade`).  
- Update compliance engine with AISC 360, ACI 318, and CBC Chapter 22 rules.  
- Add generator functions using `ifcopenshell.api` for beam/slab creation.  
- Train 20 new parser examples for the fine-tuning loop.

**Phase 3: MEP Domain Implementation (Day 2–3)**  
- Handle complex systems: ducts (IfcDuctSegment), pipes (IfcPipeSegment), equipment (IfcPump, IfcFan).  
- Create hierarchical assemblies (e.g., AHU + duct run + diffuser).  
- Implement system-level validation (clearance, pressure drop, flow rate).  
- Add RSMeans MEP pricing tables and duration models.  
- Generate system-level Markdown reports (e.g., `MEP_SYSTEM_SUMMARY.md`).

**Phase 4: Remaining Domains and Cross-Domain Relationships (Day 3)**  
- Implement interior, site, landscape, and fire-protection domains following the same pattern.  
- Define inter-domain relationships (e.g., wall must support slab, duct must penetrate wall with fire damper).  
- Extend clash suite with discipline-specific rules (e.g., MEP vs. structural clearance).

**Phase 5: Unified Registration and Testing Hooks (Day 4)**  
```python
# aecos/domains/loader.py
def load_all_domains():
    for domain in [StructuralDomain(), MEP_Domain(), ...]:
        domain.register_templates()
        domain.register_compliance_rules()
        domain.register_parser_examples()
```
Add comprehensive integration tests: generate one element from each domain, run full validation + cost + visualization, confirm all files are created correctly.

**Phase 6: CLI and Documentation Enhancements (Day 4)**  
```bash
aecos domain list
aecos domain add structural --templates 30
aecos generate "W16x36 steel beam, span 7.5 m, A992 steel, California"
```
Auto-update master `README.md` with domain coverage matrix.

**Phase 7: Evaluation, Benchmarking, and Maintenance (Day 5)**  
- Benchmark: generate 50 mixed-discipline elements; verify 100 % compliance and visualization fidelity.  
- Performance target: < 4 seconds per new-domain element generation.  
- Future-proofing: template for adding a new domain in < 2 days.  
- GitHub Action to enforce domain registration completeness on PRs.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** Executing `aecos generate "Install 300 mm concrete slab on grade with 2-hour fire rating and 150 psf live load for Baton Rouge LA"` followed by `aecos validate` and `aecos visualize` produces a complete, compliant structural element folder containing IFC, Markdown metadata, cost/schedule data, validation report, and live Speckle preview, with zero manual domain-specific code outside the modular framework.

This domain expansion transforms the AEC OS into a true multi-disciplinary platform capable of supporting complete building projects from concept through coordination.

Implement Phases 1 and 2 today by creating the base domain framework and adding the structural domain with 10 initial templates. Should any questions arise regarding IFC entity creation for specific MEP elements or cross-domain relationship modeling, provide the relevant details for immediate refinement.
