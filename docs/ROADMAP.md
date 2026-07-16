# Sustainable Catalyst Decision Studio Roadmap

## Current release

### v1.14.0 — Outcomes, Monitoring, and Reassessment

- Track decision commitments and accountable implementation owners.
- Compare baselines, targets, and observed values with direction-aware tolerances.
- Retain source, methodology, confidence, freshness, and Site Intelligence connections for observations.
- Track implementation milestones and overdue work.
- Record emerging risks and invalidated assumptions.
- Evaluate threshold, milestone, risk, assumption, and scheduled reassessment triggers.
- Require named human actors for reassessment, amendments, and retirement.
- Preserve append-only hashed monitoring and reassessment events.
- Maintain post-implementation reviews, lessons learned, and a durable Decision Registry entry.
- Apply monitoring records additively to Decision Packet `scds-decision-packet/1.7`.

## Planned releases

### v1.15.0 — Public API, Embeds, and Institutional Integration
Add versioned packet APIs, scoped public dossier and Decision Registry endpoints, signed export manifests, embeds, internal events, bulk import/export, institutional archive packages, and stable cross-product contracts.

### v1.16.0 — Accessibility, Offline Use, and Release Hardening
Complete mobile, keyboard, screen-reader, chart accessibility, autosave, recovery, offline drafts, migration, security, cold-start, and degradation testing.

### v2.0.0 — Connected Decision Intelligence Platform
Complete the lifecycle: Frame → Research → Gather evidence → Model → Compare → Challenge assumptions → Review → Approve → Publish → Implement → Monitor → Reassess.

## Architectural boundaries

- Knowledge Library supplies durable sources and citations and receives reviewed publication handoffs.
- Research Librarian routes research and evidence gaps.
- Site Intelligence supplies live, comparative, and monitoring evidence with methodology and freshness context.
- Workbench performs calculations, simulations, optimization, and technical analysis.
- Research Lab supplies experimental and scientific artifacts.
- Platform Core supplies shared identity, provenance, evidence, and future Decision Registry contracts.
- Decision Studio organizes alternatives, methodologies, governance, approval, accountability, publication, implementation monitoring, and reassessment.
- Monitoring results do not establish causality or replace qualified external review where law, safety, fiduciary duty, clinical practice, engineering standards, assurance, or public authority require it.
