# AEC OS Business Logic Bible
**Version:** 1.0 (Final Reference — Nail-First Iteration)
**Date:** 2026-02-17
**Author:** Brennen Monson (with Grok synthesis)
**Status:** Authoritative — All future code, prompts, and decisions must align with this document

## 1. System Vision & Ultimate Outcome

The AEC OS is a complete, local-first AI operating system that replaces manual Revit/IFC authoring with natural-language-driven parametric design.
A practitioner expresses intent in plain English, and the system instantly returns a fully compliant, costed, validated, version-controlled IFC element (or small assembly) with 3D preview, ready for direct insertion into Revit and team collaboration.

**Ultimate outcome (12-24 months):**
Every repetitive, standards-driven design task is reduced from hours/days to seconds, delivering measurable cost avoidance, zero compliance errors from system-generated elements, and the ability to start new Louisiana projects with a fully coordinated, cost-aware base model in under two hours instead of two weeks. The system becomes a living, continuously improving "design intelligence" specific to the user's practice.

## 2. Core Design Principles (Non-Negotiable)

These six principles are sacred and override all other considerations:

1. **Local / Offline Core Intelligence**
   All parsing, compliance checking, generation, validation, and fine-tuning run 100 % locally on consumer hardware. No core logic may ever send data to external APIs.

2. **Git as Single Source of Truth**
   Every element, template, metadata file, audit log, and configuration lives in git. Git is the authoritative state and history.

3. **Pure-File Architecture**
   Primary storage is self-contained folders of plain files (JSON, Markdown, IFC). No external database is required for the element library or project data.

4. **Full Traceability & Cryptographic Auditability**
   Every action produces an immutable, digitally signed audit trail.

5. **Revit Compatibility as First-Class Citizen**
   All output must be immediately usable in Revit 2025-2027 via pyRevit or direct IFC linking.

6. **Legal & Financial Correctness First**
   Compliance accuracy, clash detection, and audit integrity have absolute precedence over speed or convenience.

Cloud services (Speckle, Slack/Teams, RSMeans, GitHub) are permitted only for optional collaboration/enrichment layers and must never be required for baseline functionality.

## 3. Terminology & Glossary

**Canonical terms (mandatory everywhere):**

- **Element** - The atomic, reusable, versioned IFC-based design object (extracted or generated). This is the primary term for the "building block".
- **Template** - A curated, standardized Element that resides in the library and is ready for reuse or parametric modification.
- **Assembly** - A group of related Elements with explicit IFC relationships.
- **Parametric Spec** - The structured output of the natural-language parser that drives generation.

**Retired / Restricted terms:**

- "Chunk" -> replace with "Element"
- "Family" -> use only when discussing Revit-native interop
- "Component" -> reserved exclusively for software architecture

## 4. User Personas & Primary Workflows

**Primary Persona:**
Lead Designer / BIM Architect in a small-to-medium Louisiana AEC firm who values speed, accuracy, and professional liability protection.

**Mature-State Daily Workflow (ideal end-state):**

1. Requirement arrives (brief, RFI, or Slack message).
2. User types or speaks the requirement in plain English.
3. Natural Language Parser converts to Parametric Spec + confidence score.
4. Compliance Engine validates and auto-applies adjustments if needed.
5. System locates best Template or parametrically generates new Element.
6. Clash & Validation Suite runs (against context model if present).
7. Cost & Schedule data is calculated and attached.
8. Full Markdown metadata (README, COMPLIANCE, COST, etc.) is generated.
9. 3D preview exported to Speckle + glTF with embedded links.
10. Element folder is committed to git with full audit trail.
11. Team notified via Slack/Teams with review task and links.
12. User inserts element into Revit via one-click pyRevit action.
13. Any corrections are logged for automatic fine-tuning.

Target cycle time for a typical element: **under 30 seconds** of user attention.

## 5. Module Interdependencies (High-Level Map)

- Item 1 -> feeds Items 2, 3, 5
- Item 2 + Item 3 -> foundation for Items 6, 7, 8
- Item 6 -> drives Items 7, 8, 9, 10
- Item 7 -> constrains Items 8, 9, 10
- Item 8 -> produces output consumed by Items 9, 10, 11
- Item 11-19 -> horizontal supporting layers that wrap the core pipeline

## 6. Business Rules & Decision Logic

- Compliance always overrides generation (Item 7/8).
- Template reuse is preferred over pure parametric generation (Item 2/8).
- Every generated Element must pass validation before commit (Item 9).
- Cost/schedule data is mandatory for every Element (Item 10).
- All changes require audit logging and (when multi-user) sign-off (Item 17).
- Fine-tuning data is captured on every accepted/corrected parse (Item 13).

## 7. Data & State Management Philosophy

- Git repository = single source of truth.
- Element folders are self-describing artifacts (JSON + Markdown + IFC).
- SQLite databases (compliance, audit, analytics) are local support files only.
- Vector index and fine-tuned models are stored locally and versioned via git LFS where large.
- All state changes are atomic and reversible.

## 8. Success Metrics & KPIs

**Leading (daily/weekly):**

- NL parse accuracy -> target >= 95 % after first fine-tuning cycles
- Template reuse rate -> target >= 70 % of new elements
- Time from NL input to committed Element -> target < 30 seconds
- Compliance pass rate on generated elements -> 100 %

**Lagging (per project):**

- Cost avoidance (estimated $ value of avoided manual work)
- Reduction in model coordination / clash-fix time
- Zero compliance violations traceable to AEC OS-generated elements

**Qualitative signals of success:**

- "I haven't opened the Revit Family Editor in weeks."
- New team members become productive on day one.
- The system feels like a true extension of my design intent.

---

## Raw Component Goals (for synthesis reference)

### Item 01 — Data Extraction Pipeline
> Convert any Revit-exported IFC into a lossless, editable folder tree where every individual designed item (wall, door, MEP run, etc.) lives in its own folder with subfolders for geometry, properties, materials, relationships, costs, and a Markdown summary. Output is pure files—no database required—so you can git it, template it, and feed it to LLMs later.

### Item 02 — Template Library
> Create a git-versioned, searchable collection of 100+ standardized, single-element (or small assembly) IFC templates. Each is a ready-to-drop building block that matches your extraction pipeline's folder format exactly. Templates are pre-tagged for type, material, performance, code compliance, and region—so later roadmap steps (NLP parser, compliance engine) can find and insert them instantly.

### Item 03 — Markdown Metadata Layer
> Turn every folder created by the extraction pipeline (Item 1) and every template (Item 2) into a human-first knowledge base. Auto-generate short, dense, version-controlled Markdown files (primarily `README.md`, plus optional `COMPLIANCE.md`, `USAGE.md`, `COST.md`) that LLMs, teammates, and future roadmap steps can read instantly. No more hunting through JSON—open the folder and see exactly what the element is, why it complies, and how to use it.

### Item 04 — Version Control Backbone
> Establish a robust, git-based foundation for the entire system that ensures traceability, collaboration, safe experimentation, and automated quality gates across the template library (Item 2), extracted project data (Item 1), and generated Markdown metadata (Item 3). The repository structure treats IFC templates and project-derived elements as versioned artifacts, enabling branching for new regions/codes, releases for stable sets, and hooks for CI validation. This creates a single source of truth that scales to team use and future items (e.g., multi-user sync in Item 12).

### Item 05 — Python API Wrapper
> Develop a centralized, installable Python package that provides a clean, consistent, and extensible application programming interface for all prior components. The wrapper unifies operations on IFC files (via ifcopenshell), the template library (Item 2), extracted project structures (Item 1), and Markdown metadata generation (Item 3). It supports full CRUD functionality (Create, Read, Update, Delete) on individual elements and assemblies, while serving as the foundation for later roadmap items such as natural-language parsing (Item 6) and compliance checking (Item 7).

### Item 06 — Natural Language Parser
> Transform human-readable building specifications into structured IFC parameters and constraints. Uses LangChain framework with local LLM to enable offline, privacy-preserving natural language understanding. A natural language processing pipeline that converts plain-language building descriptions ("fire-rated wall", "accessible parking area", "high-efficiency HVAC") into precise, actionable IFC parameters for automated generation.

### Item 07 — Code Compliance Engine
> Establish a centralized, version-controlled, and fully local database of building code requirements that automatically validates every element or assembly against applicable regulations. The engine ingests key provisions from major codes (International Building Code, California Building Code, Title 24, and selected local amendments), structures them for precise querying, and integrates directly with the natural language parser (Item 6), template library (Item 2), and Python API wrapper (Item 5). It returns compliance status, required modifications, and alternative compliant templates, with traceable citations to original code sections.

### Item 08 — Parametric Generation
> Create a robust parametric generation module within the `aecos` package that accepts validated specifications from the natural language parser (Item 6) and compliance engine (Item 7), then programmatically constructs or modifies IFC elements and small assemblies using `ifcopenshell.api`. The module produces complete, standards-compliant IFC elements that integrate seamlessly with the template library (Item 2), Markdown metadata layer (Item 3), and Python API wrapper (Item 5). This capability extends beyond static templates to generate bespoke elements while preserving traceability and version control.

### Item 09 — Clash & Validation Suite
> Establish a fully automated, extensible validation and clash-detection module within the `aecos` package that performs geometric, topological, semantic, and constructability checks on newly generated elements (Item 8), extracted data (Item 1), or full assemblies before they are committed to the template library or project repository. The suite replicates essential capabilities of commercial tools such as Solibri Model Checker while remaining lightweight, local, and integrated with the existing pipeline, ensuring every element satisfies spatial coordination, clearance requirements, code-derived constraints (Item 7), and library standards (Item 2).

### Item 10 — Cost & Schedule Hooks
> Embed accurate, traceable cost estimation and preliminary scheduling data directly into every element and assembly within the `aecos` ecosystem. The module automatically calculates unit costs, total installed costs, labor hours, and high-level activity durations by linking the template library (Item 2), parametric generator (Item 8), and compliance engine (Item 7) to authoritative sources. Outputs are attached as standardized JSON and Markdown files, enabling instant project-level takeoffs, budget dashboards, and schedule stubs while remaining fully local or API-driven for privacy and speed.

### Item 11 — Visualization Bridge
> Develop a bidirectional visualization bridge within the `aecos` package that converts any generated, extracted, or parametric element (or full assembly) into real-time, interactive 3D representations. The bridge supports immediate previews in professional AEC viewers, web-based interfaces, and immersive environments, enabling rapid design iteration, stakeholder feedback, clash visualization, and AR/VR walkthroughs without manual file conversion or external tools. All exports remain fully traceable to the source folder structure, Markdown metadata, and version-control history.

### Item 12 — Multi-User Sync
> Extend the existing Git-based version control backbone (Item 4) into a robust, real-time and asynchronous multi-user synchronization layer that supports concurrent work by distributed teams (architects, engineers, BIM coordinators, and stakeholders). The module provides automated conflict detection and resolution tailored to AEC file types (IFC elements, JSON metadata, Markdown specifications), webhook-driven notifications, role-based permissions, and seamless integration with the Python API wrapper (Item 5), natural language parser (Item 6), and visualization bridge (Item 11), ensuring every change is traceable, auditable, and instantly visible to the appropriate team members while preserving the single source of truth in the repository.

### Item 13 — Fine-Tuning Loop
> Establish a fully automated, human-in-the-loop fine-tuning pipeline that continuously improves the accuracy, domain specificity, and reliability of your local LLM. The loop collects real user interactions, corrections, and high-quality outputs; curates them into structured training datasets; performs efficient LoRA/QLoRA fine-tuning on consumer-grade hardware; evaluates the new model against AEC-specific benchmarks; and deploys the improved model with full version control and rollback capability. This turns the system from a static LLM into an evolving, company- and user-specific "design intelligence" that learns your preferences, regional practices, and project-specific conventions over time.

### Item 14 — Domain Expansion
> Systematically extend the `aecos` ecosystem to support additional AEC disciplines by creating modular, reusable domain-specific components for template handling, parametric generation, compliance validation, cost and schedule estimation, clash detection, visualization, and natural-language parsing, thereby enabling the system to manage complete multi-disciplinary projects from a single unified codebase while preserving traceability and version control across all domains.

### Item 15 — Regulatory Auto-Update
> Establish an automated, scheduled process that continuously monitors authoritative sources for amendments, errata, and new editions of building codes and standards (International Building Code, California Building Code, Title 24, ASCE 7, ASHRAE 90.1, NEC, and applicable local amendments). The system ingests changes, updates the compliance database (Item 7), re-tags and re-validates affected templates in the library (Item 2), regenerates associated Markdown metadata (Item 3), triggers fine-tuning examples where appropriate (Item 13), and propagates notifications through the multi-user sync and collaboration layers (Items 12 and 16). This ensures perpetual regulatory compliance across the entire AEC OS without manual intervention while preserving complete auditability and version history (Item 4).

### Item 16 — Collaboration Layer
> Establish a comprehensive, integrated collaboration interface that enables distributed team members to interact with the AEC OS in real time and asynchronously through familiar messaging platforms (Slack, Microsoft Teams, Discord) and a lightweight web dashboard. Natural-language commands issued in chat are automatically translated via the natural language parser (Item 6), executed through the Python API wrapper (Item 5), and synchronized across the version-control backbone (Item 4), visualization bridge (Item 11), and multi-user sync (Item 12). All interactions are fully traceable, auditable (Item 13), and linked to specific element folders, generating contextual threads, task assignments, and approval workflows.

### Item 17 — Security & Audit
> Develop a comprehensive, enterprise-grade security and audit framework that safeguards all assets within the AEC OS, enforces strict access controls, and maintains an immutable, cryptographically verifiable record of every action taken across the system. It ensures compliance with relevant standards (AIA Contract Documents, ISO 27001, SOC 2 Type II, and client-specific data-security requirements), protects proprietary templates and fine-tuned models, and delivers auditable evidence suitable for professional liability, insurance, and legal review.

### Item 18 — Deployment Pipeline
> Create a fully automated, repeatable, and secure deployment pipeline that transforms the complete `aecos` system—core package, template library, compliance database, fine-tuned models, vector index, and all supporting scripts—into a production-ready environment that can be deployed to individual workstations, team servers, cloud instances, or containerized clusters with a single command. The pipeline ensures consistent environments across Windows (for Revit/pyRevit users), Linux/macOS servers, and cloud platforms (AWS, GCP, Azure), while incorporating security controls (Item 17), version pinning, rollback capability, and zero-downtime updates for collaborative teams.

### Item 19 — Analytics Dashboard
> Deliver a centralized, interactive, and secure analytics dashboard that provides real-time and historical insights into the performance, usage, and value of the entire AEC OS. The dashboard aggregates key metrics across all prior roadmap components—including extraction volume (Item 1), template reuse rates (Item 2), parse accuracy and fine-tuning progress (Items 6 and 13), compliance pass rates (Item 7), generation throughput (Item 8), cost savings (Item 10), collaboration activity (Item 16), security events (Item 17), and deployment health (Item 18)—enabling data-driven decision-making, productivity tracking, and continuous system optimization for both individual users and enterprise teams.
