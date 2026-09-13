# Decision Studio v2.8.0 — Decision Graph & Dependency Mapping

Decision Studio v2.8.0 adds an inspectable dependency graph over the Unified Decision Object.

## Contracts

- `scds-decision-dependency-graph/1.0`
- `scds-dependency-diagnostics/1.0`
- `scds-change-impact-assessment/1.0`

## Graph semantics

Nodes represent decision records such as evidence, assumptions, models, Site Intelligence context, scenarios, criteria, alternatives, uncertainty, tradeoffs, analysis requests, recommendations, recorded decisions, and the decision itself. Edges may be explicit record references or deterministic structural relationships. Every edge records `causal_claim: false` and `automatic_invalidation: false`.

## Diagnostics

The graph surfaces orphan records, roots and leaves, unresolved references, cycles, and high fan-out nodes. Fan-out is structural only and is never interpreted as importance, truth, or causal influence.

## Change impact

A changed node can be traced through downstream edges to create a review queue. Reachability does not automatically invalidate a record or alter a recommendation.

## Human-control boundary

Decision Studio maps relationships. It does not infer causality, approve a decision, select a winner, or automatically change a recommendation from graph connectivity.
