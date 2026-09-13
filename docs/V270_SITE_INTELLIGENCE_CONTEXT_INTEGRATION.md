# Decision Studio v2.7.0 — Site Intelligence Context Integration

Decision Studio v2.7.0 adds a first-class, provenance-aware context bridge from Site Intelligence into the Unified Decision Object.

## Contracts

- `scds-site-intelligence-context-bundle/1.0`
- `scds-site-intelligence-signal-snapshot/1.0`
- `scds-site-intelligence-context-receipt/1.0`

Each snapshot preserves the exact source payload plus source identity, geography, observation/update time, freshness, methodology, limitations, destination links, explicit scenario references, and a deterministic SHA-256 fingerprint.

## Decision boundary

Site Intelligence owns observation and public-intelligence context. Decision Studio consumes that context but does not rewrite observations as causal findings, infer scenario likelihood, alter scenario scores from context alone, approve an action, or generate a recommendation from a signal.

A context receipt confirms schema and fingerprint integrity only. It is not truth verification, source verification, causal inference, certification, approval, or recommendation.

## Decision Object behavior

Valid bundles attach to `site_intelligence_context_bundles`, `site_intelligence_context_receipts`, and `real_world_context`. Context records are also projected into the evidence collection with `evidence_role=contextual_evidence`. Explicit scenario links are recorded as relationships with `automatic_score_change=false`.

## Compatibility

v2.7.0 preserves v2.6.0 Lab + Workbench native handoffs, v2.5.0 Scenario Comparison & Stress Testing, v2.4.0 Uncertainty/Sensitivity/Confidence, v2.3.1 tradeoff analysis, and the distinct Energy Runtime Consumer v2.3.0.
