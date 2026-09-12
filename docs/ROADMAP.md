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
