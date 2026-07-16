# Sustainable Catalyst Decision Studio Roadmap

## Current release

### v1.11.0 — Collaborative Decision Rooms

- Create private, restricted, and institutional Decision Rooms around a Decision Packet.
- Assign room roles with explicit permissions for ownership, facilitation, editing, review, client participation, and observation.
- Attach comments and change requests to packet sections, evidence, assumptions, scenarios, and brief content.
- Record resolutions, implementation status, revisions, notifications, and activity history.
- Capture Decision Packet snapshots and compare changed paths between versions.
- Protect approved or implemented versions with explicit locks and reasoned reopening.
- Store rooms, members, and events canonically in WordPress while retaining backend contract parity.
- Generate private Contact and Engagement Platform handoffs for advisory or institutional collaboration.
- Preserve v1.10.0 scenario analysis, v1.9.0 governance, v1.8.0 typed handoffs, and legacy adapters.

## Planned releases

### v1.12.0 — Institutional and Domain Decision Packs
Add reusable evidence, criteria, review, scenario, collaboration, and brief templates for climate, infrastructure, procurement, responsible AI, research, humanitarian, and policy decisions.

### v1.13.0 — Decision Briefing and Publication Studio
Add citation-native executive memos, technical reports, public dossiers, evidence appendices, redaction controls, and publishing handoffs.

### v1.14.0 — Outcomes, Monitoring, and Reassessment
Track commitments, owners, indicators, milestones, actual-versus-expected performance, invalidated assumptions, reassessment triggers, and lessons learned.

### v1.15.0 — Public API, Embeds, and Institutional Integration
Expose scoped APIs, public-safe dossier endpoints, embeds, signed manifests, internal events, bulk exchange, and institutional archive packages.

### v1.16.0 — Accessibility, Offline Use, and Release Hardening
Complete keyboard, screen-reader, mobile, recovery, offline-draft, migration, backup, security, privacy, and performance hardening.

### v2.0.0 — Connected Decision Intelligence Platform
Complete the lifecycle: frame, research, gather evidence, model, compare, collaborate, challenge assumptions, review, approve, publish, implement, monitor, and reassess.

## Canonical build sequence

1. **v1.11.0 — Collaborative Decision Rooms** — current
2. **v1.12.0 — Institutional and Domain Decision Packs**
3. **v1.13.0 — Decision Briefing and Publication Studio**
4. **v1.14.0 — Outcomes, Monitoring, and Reassessment**
5. **v1.15.0 — Public API, Embeds, and Institutional Integration**
6. **v1.16.0 — Accessibility, Offline Use, and Release Hardening**
7. **v2.0.0 — Connected Decision Intelligence Platform**

## Architecture and product boundaries

- **Knowledge Library** supplies durable sources, quotations, citations, and bibliographies.
- **Research Librarian** supplies research routes, recommendations, evidence gaps, and follow-up questions.
- **Site Intelligence** supplies live indicators, dossiers, methodology, freshness, and source-health records.
- **Workbench** performs calculations, simulations, sensitivity analysis, optimization, and technical modeling.
- **Research Lab** supplies experiments, notebooks, datasets, instruments, and validation results.
- **Platform Core** supplies shared entities, Evidence Ledger records, provenance, relationships, and manifests.
- **Decision Studio** organizes alternatives, collaboration, governance, approval, publication, implementation, and reassessment.
- **Contact and Engagement Platform** receives structured handoffs when a Decision Room needs a private advisory or client workspace.

Decision Studio remains decision support. AI can help identify missing evidence, contradictions, unresolved assumptions, or drafting opportunities, but cannot approve, sign, certify, assure, or impersonate a human participant.
