# Sustainable Catalyst Decision Studio Roadmap

## Current release

### v2.2.0 — Evidence & Source Bundles

- Make sources durable, reusable objects with provenance, citation, quality, freshness, and review metadata.
- Bind evidence claims to source identities rather than disconnected citation text.
- Surface evidence coverage, unresolved source relationships, review gaps, and contradictions.
- Preserve deterministic SHA-256 fingerprints and raw payloads for reproducibility.
- Attach evidence bundles directly to the Unified Decision Object and Decision Packet 2.0.
- Keep truth verification and approval as explicit human/expert review responsibilities.

## Next build

### v2.3.0 — Criteria, Alternatives & Tradeoff Matrix

- First-class criteria registry with weights, units, direction, thresholds, source/evidence links, and review state.
- Alternative registry with structured attributes, constraints, scenario links, and evidence coverage.
- Transparent tradeoff matrix with dominance, incomparability, and sensitivity-ready outputs.
- No automatic approval or false single-score certainty.

## Architectural boundaries

- Knowledge Library supplies durable sources and citations and receives reviewed publication handoffs.
- Research Librarian routes research and evidence gaps.
- Site Intelligence supplies live, comparative, and monitoring evidence with methodology and freshness context.
- Workbench performs calculations, simulations, optimization, and technical analysis.
- Research Lab supplies experimental and scientific artifacts.
- Platform Core supplies shared identity, provenance, Evidence Ledger, Decision Registry, events, and exchange contracts.
- Decision Studio orchestrates alternatives, governance, approval, publication, implementation, monitoring, reassessment, and accountability.
- Connected routes are structured handoffs and do not claim external acceptance or execution.
- Automated assessment never replaces human approval, professional judgment, required assurance, security review, or accessibility testing.
