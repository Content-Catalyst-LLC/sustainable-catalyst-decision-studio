# Sustainable Catalyst Decision Studio Roadmap

## Current release

### v1.16.0 — Accessibility, Offline Use, and Release Hardening

- Add keyboard, focus, landmark, label, live-region, table, chart-alternative, reduced-motion, contrast, error, touch-target, and zoom/reflow checks.
- Require human assistive-technology validation before a conformance claim.
- Add IndexedDB autosave with localStorage fallback and online/offline announcements.
- Strip secrets and credentials from recovery storage.
- Create hashed recovery snapshots before migration or release.
- Assess additive migrations from Decision Packet 1.0–1.8 to 1.9.
- Gate release readiness on accessibility, offline recovery, performance, migration, backup/restore, security, and privacy.
- Require named-human release authorization and prohibit automatic deployment.

## Planned releases

### v2.0.0 — Connected Decision Intelligence Platform
Complete the lifecycle: Frame → Research → Gather evidence → Model → Compare → Challenge assumptions → Review → Approve → Publish → Implement → Monitor → Reassess.

## Architectural boundaries

- Knowledge Library supplies durable sources and citations and receives reviewed publication handoffs.
- Research Librarian routes research and evidence gaps.
- Site Intelligence supplies live, comparative, and monitoring evidence with methodology and freshness context.
- Workbench performs calculations, simulations, optimization, and technical analysis.
- Research Lab supplies experimental and scientific artifacts.
- Platform Core supplies shared identity, provenance, evidence, and Decision Registry exchange contracts.
- Decision Studio organizes alternatives, methodologies, governance, approval, accountability, publication, implementation monitoring, reassessment, institutional exchange, and release readiness.
- Offline storage never caches institutional credentials or automatically replays consequential writes.
- Automated accessibility and release checks do not replace human testing, security review, professional judgment, or required external assurance.
