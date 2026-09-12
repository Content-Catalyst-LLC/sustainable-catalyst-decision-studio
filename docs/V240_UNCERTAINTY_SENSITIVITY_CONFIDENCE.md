# Decision Studio v2.4.0 — Uncertainty, Sensitivity & Confidence

## Purpose

v2.4.0 extends the transparent comparison system introduced in v2.3.1. The objective is to make uncertainty and fragility inspectable without converting analytical coverage into false certainty.

## Contracts

### `scds-uncertainty-register/1.0`

Records uncertainty as a first-class object with a stable ID, target type and target ID, parameter, baseline, lower and upper bounds, units, optional distribution metadata, source references, rationale, review status, provenance, and target/bound diagnostics.

Supported targets include evaluations, criterion weights, criteria, alternatives, assumptions, models, scenarios, sources, and the decision itself. v2.4.0 actively applies bounded evaluation uncertainty during matrix sensitivity analysis; other target types remain preserved for downstream analysis.

### `scds-sensitivity-analysis/1.0`

Runs deterministic perturbation tests against a `scds-tradeoff-matrix/1.0` matrix. v2.4.0 includes:

- configurable criterion-weight perturbation (default ±20%);
- automatic re-normalization of criterion weights;
- lower/upper testing of bounded evaluation scores or values;
- baseline alternative scores;
- score deltas for each perturbation;
- alternative score envelopes across tested cases;
- pairwise score-range overlap diagnostics;
- ordering-change visibility;
- maximum absolute tested score shift.

The analysis is deterministic and reproducible. It does not use random sampling in v2.4.0.

### `scds-confidence-assessment/1.0`

Summarizes five visible process dimensions:

1. matrix completeness;
2. review coverage;
3. evidence linkage;
4. uncertainty characterization;
5. sensitivity coverage.

The arithmetic mean is exposed as `process_confidence_index`, with the underlying dimensions always retained. The index is a workflow/documentation diagnostic only. It is **not** a probability that a decision, recommendation, or alternative is correct.

## Decision Object integration

`POST /decision-object/uncertainty-confidence` attaches:

- `uncertainty_registers[]`;
- `sensitivity_analyses[]`;
- `confidence_assessments[]`;
- current `uncertainties`;
- a bounded current `confidence` summary;
- provenance event `uncertainty_sensitivity_confidence_attached`.

Decision Packet 2.0 remains supported through `POST /decision-packet/uncertainty-confidence`.

## Human-control boundary

v2.4.0 may show that an ordering changes under tested perturbations, or that alternative score ranges overlap. It may also show low process confidence because evidence or review coverage is incomplete. It does not:

- select a winner;
- generate an automatic recommendation;
- claim a probability of correctness;
- certify evidence sufficiency;
- approve or authorize a consequential decision.

## Preserved Energy integration

The Energy Systems Runtime Consumer introduced in Decision Studio v2.3.0 remains registered and component-versioned at **2.3.0**, including its bounded target-side handoff behavior.

## Next canonical build

**v2.5.0 — Scenario Comparison & Stress Testing** should consume the v2.4 uncertainty and sensitivity artifacts rather than reimplementing them.
