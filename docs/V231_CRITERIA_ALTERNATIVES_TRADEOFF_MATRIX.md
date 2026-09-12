# Decision Studio v2.3.1 — Criteria, Alternatives & Tradeoff Matrix

## Purpose

Make decision comparison explicit and inspectable. Criteria, weights, candidate alternatives, evaluation cells, evidence references, thresholds, and review state become first-class objects rather than disappearing inside a single score.

## Schemas

- `scds-criteria-set/1.0`
- `scds-alternatives-set/1.0`
- `scds-tradeoff-matrix/1.0`
- `scds-tradeoff-diagnostics/1.0`

## Comparison behavior

Criteria retain the user's input weight and receive a normalized weight when the total weight is positive. Evaluations may supply a direct 0–100 score or a raw numeric value with a criterion scale. Minimize criteria invert the scale-derived score. Threshold violations are surfaced but do not automatically eliminate an alternative.

Alternative summaries receive a weighted comparative score only when all required matrix cells are scored. Missing cells remain visible. Score ordering is not treated as a recommendation.

## Diagnostics

The matrix reports criteria count, alternatives count, expected and evaluated cells, matrix coverage, weight totals, missing evaluations, unknown IDs, unscored cells, review gaps, threshold violations, and completeness.

## Decision Object integration

`POST /decision-object/tradeoffs` attaches the matrix to `tradeoff_matrices`, while promoting the matrix criteria, alternatives, and evaluation records into the canonical Decision Object fields. `POST /decision-packet/tradeoff-matrix` projects the same structures additively into Decision Packet 2.0.

## Human-control boundary

Decision Studio does not select a winner, approve an alternative, or generate a recommendation solely from weighted scores. Criteria selection, weights, evidence sufficiency, uncertainty, professional review, and accountable judgment remain human responsibilities.

## Energy Systems Runtime Consumer preservation

Decision Studio v2.3.1 is based on the canonical v2.3.0 Energy Systems Runtime Consumer release. The Energy target-side consumer remains available at `GET /v1/energy-runtime/consumer` and `POST /v1/energy-runtime/consume`, preserving the `sc-energy-runtime-decision-studio-handoff/1.0` contract and its no-automatic-ranking/no-automatic-recommendation boundary.

