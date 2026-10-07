
## v3.12.0 — Module Interoperability & Shared Evidence
- Canonical `scds-module-interoperability/1.0` contract.
- Shared evidence by stable reference across Canvas, Finance, Narrative Risk, and Global Impact.
- Explicit owner/consumer module relationships, provenance continuity, artifact references, and contradiction visibility.
- Reuses `decision_objects` and `evidence_links`; no PostgreSQL schema migration.
- Evidence reuse does not imply truth, causality, recommendation, approval, or ownership transfer.
- Next: v3.13.0 — Collaboration & Decision Room Python Persistence.

## Decision Studio modernization line (v3.1+)

- **v3.1.0 — Backend Service Decomposition** — built.
- **v3.2.0 — Decision Kernel & Module Contract Foundation** — built; Canvas, Finance, Narrative Risk, and Global Impact Catalyst are registered first-class modules over one shared kernel.
- **v3.3.0 — PostgreSQL Persistence Foundation** — foundation release; PostgreSQL schema/migrations/repository seam are live but non-authoritative.
- **v3.3.1 — PostgreSQL Migration Revision Repair** — built; corrected the Alembic revision-length production issue and certified the 20-table PostgreSQL foundation.
- **v3.4.0 — Python Decision Repository & Object Persistence** — built; Python/PostgreSQL becomes authoritative for Decision Kernel project, decision, unified object, module-binding, snapshot, and audit-event persistence while final decisions remain human-governed.
- **v3.5.0 — Canvas Python Domain Migration** — built; Canvas framing, alternatives, criteria, assumptions, stakeholder context, and success measures are now authoritative in Python/PostgreSQL over the shared Decision Kernel.
- **v3.6.0 — Finance Python Domain Migration** — built; Finance domain state is authoritative in Python/PostgreSQL while Workbench remains calculation authority.
- **v3.7.0 — Narrative Risk Python Domain Migration** — built; claims, evidence relationships, signals, actors, exposures, and competing narratives are authoritative in Python/PostgreSQL with explicit epistemic boundaries.
- **v3.8.0 — Global Impact Catalyst Python Domain Migration** — current release; impact claims, evidence links, indicators, SDG/carbon/resource/distributional context, and provenance are authoritative in Python/PostgreSQL while Workbench remains compute authority.
- **v3.9.0 — Unified Decision Module Registry** — next.

# Sustainable Catalyst Decision Studio Roadmap

## Current release

### v2.3.1 — Criteria, Alternatives & Tradeoff Matrix

- First-class criteria registry with weights, direction, scales, thresholds, evidence links, and provenance.
- First-class alternatives registry with stable IDs, attributes, constraints, evidence links, and provenance.
- Transparent alternative-by-criterion evaluation matrix.
- Missing-cell, score, review, coverage, and threshold diagnostics.
- Weighted comparative summaries with explicit no-auto-recommendation boundary.
- Unified Decision Object and Decision Packet projection.

## Next build

### v2.4.0 — Uncertainty, Sensitivity & Confidence

- Uncertainty objects connected to criteria, evaluations, scenarios, and evidence.
- Weight and score sensitivity without hiding assumptions.
- Confidence ranges and robustness diagnostics for comparative results.
- Threshold and break-point analysis for recommendation stability.
- No automatic approval or false certainty.

## Architectural boundaries

- Knowledge Library supplies durable sources and citations and receives reviewed publication handoffs.
- Research Librarian routes research and evidence gaps.
- Site Intelligence supplies live, comparative, and monitoring evidence with methodology and freshness context.
- Workbench performs calculations, simulations, optimization, and technical analysis.
- Research Lab supplies experimental and scientific artifacts.
- Platform Core supplies shared identity, provenance, Evidence Ledger, Decision Registry, events, and exchange contracts.
- Decision Studio orchestrates criteria, alternatives, tradeoffs, governance, approval, publication, implementation, monitoring, reassessment, and accountability.
- Connected routes are structured handoffs and do not claim external acceptance or execution.
- Automated assessment never replaces human approval, professional judgment, required assurance, security review, or accessibility testing.


## v3.10.0 — Cross-Module Decision Composition

- Compose two or more authoritative Decision Studio modules under one shared Decision Kernel identity.
- Preserve module ownership, explicit cross-module links, Workbench compute authority, provenance, and human final-decision authority.
- Store compositions in the existing Python/PostgreSQL repository with no schema migration.
- Next: v3.11.0 — Module Artifact & Provenance Standard.
