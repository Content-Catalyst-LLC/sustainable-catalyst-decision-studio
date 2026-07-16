# Sustainable Catalyst Decision Studio Roadmap

## Current release

### v1.13.0 — Decision Briefing and Publication Studio

- Produce twelve citation-native decision publication types.
- Build Harvard-style bibliographies and evidence anchors from the Decision Packet source registry.
- Control private, institutional, and public section visibility.
- Record deterministic redaction events and block non-public sections from public output.
- Enforce human-governance gates for reviewed and public publications.
- Export JSON, Markdown, print-ready HTML, bibliography, redaction, and publication handoff records.
- Create draft handoffs to Knowledge Library, Research, Publications, and Channel.
- Apply publication records additively to Decision Packet `scds-decision-packet/1.6`.

## Planned releases

### v1.14.0 — Outcomes, Monitoring, and Reassessment
Track commitments, owners, baselines, targets, actual-versus-expected results, implementation milestones, assumption invalidation, reassessment triggers, amendments, lessons learned, and retirement.

### v1.15.0 — Public API, Embeds, and Institutional Integration
Add versioned packet APIs, scoped public dossier endpoints, signed export manifests, internal events, bulk import/export, institutional archive packages, and stable cross-product contracts.

### v1.16.0 — Accessibility, Offline Use, and Release Hardening
Complete mobile, keyboard, screen-reader, chart accessibility, autosave, recovery, offline drafts, migration, security, cold-start, and degradation testing.

### v2.0.0 — Connected Decision Intelligence Platform
Complete the lifecycle: Frame → Research → Gather evidence → Model → Compare → Challenge assumptions → Review → Approve → Publish → Implement → Monitor → Reassess.

## Architectural boundaries

- Knowledge Library supplies durable sources and citations and receives reviewed publication handoffs.
- Research Librarian routes research and evidence gaps.
- Site Intelligence supplies live and comparative evidence.
- Workbench performs calculations, simulations, optimization, and technical analysis.
- Research Lab supplies experimental and scientific artifacts.
- Platform Core supplies shared identity, provenance, and evidence contracts.
- Decision Studio organizes alternatives, methodologies, governance, approval, accountability, publication, and reassessment.
- Publications never replace qualified external review where law, safety, fiduciary duty, clinical practice, engineering standards, or public authority require it.
