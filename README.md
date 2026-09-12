# Sustainable Catalyst Decision Studio v2.5.0

## Scenario Comparison & Stress Testing

Decision Studio v2.5.0 builds on the v2.4.0 Uncertainty, Sensitivity & Confidence layer and adds three first-class contracts: `scds-scenario-set/1.0`, `scds-scenario-comparison/1.0`, and `scds-stress-test-suite/1.0`.

The release compares named conditional scenarios against the same v2.3.1 Tradeoff Matrix, records criterion-weight and evaluation overrides, surfaces score ranges, ordering changes, threshold breaches, and matrix completeness, and runs explicit stress-test gates. It preserves v2.4.0 uncertainty/confidence analysis, v2.3.1 tradeoffs, v2.2 evidence bundles, v2.1 Decision Object, Decision Packet 2.0, and the v2.3.0 Energy Systems Runtime Consumer.

### v2.5.0 endpoints

- `GET /scenario-set/template`
- `POST /scenario-set/build`
- `GET /scenario-analysis/template`
- `POST /scenario-analysis/compare`
- `GET /stress-test-suite/template`
- `POST /stress-test-suite/run`
- `POST /decision-object/scenario-stress`
- `POST /decision-packet/scenario-stress`

WordPress parity lives under `/wp-json/scds/v1`. The existing **Scenarios** workspace now includes a v2.5 Scenario Comparison & Stress Testing section in addition to the legacy Advanced Scenario Studio.

### Boundaries

Scenarios are conditional assumptions, not forecasts or likelihood estimates. Stress-test passes are not approval, certification, or recommendations. Decision Studio can expose score instability, ordering changes, and threshold failures, but it does not automatically choose a winner or generate a recommendation.

### Preserved Energy runtime consumer

The Energy Systems Runtime Consumer remains component version `2.3.0` and continues to accept `sc-energy-runtime-handoff/1.0` through its bounded target-side consumer contract.
