
## Decision Studio modernization line (v3.1+)

- **v3.1.0 — Backend Service Decomposition** — built.
- **v3.2.0 — Decision Kernel & Module Contract Foundation** — built; Canvas, Finance, Narrative Risk, and Global Impact Catalyst are registered first-class modules over one shared kernel.
- **v3.3.0 — PostgreSQL Persistence Foundation** — foundation release; PostgreSQL schema/migrations/repository seam are live but non-authoritative.
- **v3.3.1 — PostgreSQL Migration Revision Repair** — built; corrected the Alembic revision-length production issue and certified the 20-table PostgreSQL foundation.
- **v3.4.0 — Python Decision Repository & Object Persistence** — built; Python/PostgreSQL becomes authoritative for Decision Kernel project, decision, unified object, module-binding, snapshot, and audit-event persistence while final decisions remain human-governed.
- **v3.5.0 — Canvas Python Domain Migration** — built; Canvas framing, alternatives, criteria, assumptions, stakeholder context, and success measures are now authoritative in Python/PostgreSQL over the shared Decision Kernel.
- **v3.6.0 — Finance Python Domain Migration** — current release; Finance domain state is authoritative in Python/PostgreSQL while Workbench remains calculation authority.
- **v3.7.0 — Narrative Risk Python Domain Migration** — next.
- **v3.8.0 — Global Impact Catalyst Python Domain Migration** — planned.

## v2.8.0 — Decision Graph & Dependency Mapping

**Status: built for release.** Adds inspectable decision dependencies, orphan/cycle/unresolved-reference diagnostics, and review-only change-impact tracing while preserving non-causal and human-control boundaries.

## v2.7.0 — Site Intelligence Context Integration

**Status: built for release.** Adds provenance-aware real-world context bundles from Site Intelligence while keeping observation ownership and human interpretation boundaries explicit.

# Decision Studio Roadmap

## v2.6.0 — Lab + Workbench Native Handoffs

Status: built. Typed source-owned handoffs, bounded analysis/computation requests, deterministic fingerprints, receipts, and Decision Object lineage.

## Next

- v2.9.0 — Recommendations, Review & Challenge Layer
- v3.0.0 — Connected Decision Intelligence


## v2.5.0 — Scenario Comparison & Stress Testing

- Named conditional scenario sets
- Cross-scenario tradeoff comparison
- Score ranges and ordering-change diagnostics
- Explicit stress gates and failure modes
- Unified Decision Object attachment
- No scenario likelihood inference, automatic winner selection, or automatic recommendation
