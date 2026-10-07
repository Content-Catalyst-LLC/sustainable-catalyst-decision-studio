# Current release: v3.13.0 — Collaboration & Decision Room Python Persistence


## Decision Studio modernization line (v3.1+)

- **v3.1.0 — Backend Service Decomposition** — built.
- **v3.2.0 — Decision Kernel & Module Contract Foundation** — built; Canvas, Finance, Narrative Risk, and Global Impact Catalyst are registered first-class modules over one shared kernel.
- **v3.3.0 — PostgreSQL Persistence Foundation** — foundation release; PostgreSQL schema/migrations/repository seam are live but non-authoritative.
- **v3.3.1 — PostgreSQL Migration Revision Repair** — built; corrected the Alembic revision-length production issue and certified the 20-table PostgreSQL foundation.
- **v3.4.0 — Python Decision Repository & Object Persistence** — built; Python/PostgreSQL becomes authoritative for Decision Kernel project, decision, unified object, module-binding, snapshot, and audit-event persistence while final decisions remain human-governed.
- **v3.5.0 — Canvas Python Domain Migration** — built; Canvas framing, alternatives, criteria, assumptions, stakeholder context, and success measures are now authoritative in Python/PostgreSQL over the shared Decision Kernel.
- **v3.6.0 — Finance Python Domain Migration** — built; Finance domain state is authoritative in Python/PostgreSQL while Workbench remains calculation authority.
- **v3.7.0 — Narrative Risk Python Domain Migration** — built; claims, evidence relationships, signals, actors, exposures, and competing narratives are authoritative in Python/PostgreSQL with explicit epistemic boundaries.
- **v3.8.0 — Global Impact Catalyst Python Domain Migration** — built; impact claims, evidence links, indicators, SDG/carbon/resource/distributional context, and provenance are authoritative in Python/PostgreSQL while Workbench remains compute authority.
- **v3.9.0 — Unified Decision Module Registry** — built.
- **v3.10.0 — Cross-Module Decision Composition** — built.
- **v3.11.0 — Module Artifact & Provenance Standard** — built.
- **v3.12.0 — Module Interoperability & Shared Evidence** — built.
- **v3.13.0 — Collaboration & Decision Room Python Persistence** — current build.
- **v3.14.0 — Global Authentication & Authorization Integration** — next.

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


## v3.10.0 — Cross-Module Decision Composition

- Compose two or more authoritative Decision Studio modules under one shared Decision Kernel identity.
- Preserve module ownership, explicit cross-module links, Workbench compute authority, provenance, and human final-decision authority.
- Store compositions in the existing Python/PostgreSQL repository with no schema migration.
- Next: v3.11.0 — Module Artifact & Provenance Standard.


## v3.11.0 — Module Artifact & Provenance Standard

- Canonical module-artifact envelope shared by Canvas, Finance, Narrative Risk, and Global Impact.
- Immutable revision lineage with SHA-256 integrity and explicit parent/source/evidence/computation references.
- Existing `artifacts` + `decision_events` persistence; no new schema migration.
- Platform Core retains evidence identity/source provenance; Workbench retains Finance/Impact computation; final decisions remain human-governed.

Next: **v3.14.0 — Global Authentication & Authorization Integration**.


## v3.12.0 — Module Interoperability & Shared Evidence

- Stable-reference evidence reuse across authoritative modules without payload duplication or ownership transfer.
- Explicit consumer-module relationships, contradiction annotations, and relation-disagreement diagnostics.
- Reuses `decision_objects` and `evidence_links`; Alembic remains `0001_v330_pg_foundation`.

## v3.13.0 — Collaboration & Decision Room Python Persistence

- Canonical room state, membership, comments, change requests, share grants, and room events move to Python/PostgreSQL.
- Adds six collaboration tables; reuses existing snapshots for room snapshots.
- Alembic advances to `0002_v3130_collaboration`; persistence table count becomes 26.
- Legacy WordPress collaboration remains a compatibility projection; final authority remains human-governed.

Next: **v3.14.0 — Global Authentication & Authorization Integration**.
