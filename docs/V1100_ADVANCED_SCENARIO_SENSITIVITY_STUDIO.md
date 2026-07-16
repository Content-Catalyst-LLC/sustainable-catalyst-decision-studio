# Decision Studio v1.10.0 — Advanced Scenario and Sensitivity Studio

## Purpose

v1.10.0 expands the compatibility scenario matrix into a governed, inspectable scenario-modeling workspace. It supports comparative screening and sensitivity analysis while preserving a clear boundary between deterministic decision support and probabilistic or domain-specific simulation.

## Core contract

- Scenario schema: `scds-scenario-studio/1.0`
- Decision Packet schema: `scds-decision-packet/1.3`
- Maximum alternatives: 100
- Maximum criteria: 50
- Sensitivity parameters: up to 20
- Grid points per one-way range: 3–21

## Analysis capabilities

1. Weighted and unweighted multi-criteria rankings.
2. One-way parameter sensitivity and tornado ranking.
3. Two-variable 3×3 screening grids.
4. Threshold and break-even searches.
5. Combined endpoint uncertainty envelopes.
6. Multi-horizon financial, emissions, and score comparison.
7. Stakeholder distribution summaries.
8. Dominance and tradeoff analysis.
9. Reversibility and option-value comparison.
10. Structured Workbench handoffs for deeper computation.

## Interpretation boundary

Scenario results are conditional on user-entered assumptions and ranges. They are not forecasts, guarantees, confidence intervals, or probability distributions. Monte Carlo simulation, optimization, engineering models, uncertainty propagation, and domain forecasting belong in Workbench and should return typed artifacts to Decision Studio.

## Governance

The v1.9.0 Governance and Review Center remains authoritative. Scenario rankings do not approve a decision. Reviewed or public exports remain subject to human ownership, review, sign-off, condition, exception, conflict, and state-transition gates.

## WordPress interface

The Scenario Studio panel includes editable JSON for alternatives, ranges, and criteria; sensitivity parameters; threshold controls; time horizons; grid resolution; ranked summaries; sensitivity tables; break-even results; and JSON export. The older scenario-comparison matrix remains available as a compatibility view.

## Persistence and export

Advanced results are stored in `scenario_studio_json` and copied into these Decision Packet sections:

- `scenario_studio`
- `sensitivity_analysis`
- `threshold_analysis`
- `uncertainty_analysis`

Saved packets and export bundles include `scenario_studio_json` while retaining the compatibility `scenario_json` export.
