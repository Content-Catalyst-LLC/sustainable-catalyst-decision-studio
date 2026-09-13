## Decision Studio v2.9.0 — Recommendations, Review & Challenge Layer

## v3.0.0 — Connected Decision Intelligence

Decision Studio v3.0.0 unifies Frame → Evidence → Analyze → Compare → Stress → Review → Decide → Monitor into one inspectable lifecycle. It derives readiness only from recorded objects, preserves cross-product lineage, and suggests bounded next-action routes without automatic stage transitions, approval, winner selection, or external execution.

Decision Studio now supports explicit human-selected recommendation candidates, first-class reviewer challenges, review evaluation, and human disposition records. The layer does not automatically select a winner, infer approval from scores, or execute a decision.

# Sustainable Catalyst Decision Studio v2.8.0

## Decision Graph & Dependency Mapping

Decision Studio v2.8.0 builds on the v2.7.0 Site Intelligence Context Integration release and makes the reasoning structure of a Decision Object inspectable. Evidence, assumptions, models, real-world context, scenarios, criteria, alternatives, uncertainty, tradeoffs, requests, recommendations, and recorded decisions can be mapped as stable nodes and dependency edges.

### v2.8.0 endpoints

- `GET /decision-dependency-graph/template`
- `POST /decision-dependency-graph/build`
- `POST /decision-dependency-graph/validate`
- `POST /decision-dependency-graph/impact`
- `POST /decision-object/dependency-graph`
- `POST /decision-packet/dependency-graph`

### v2.8.0 contracts

- `scds-decision-dependency-graph/1.0`
- `scds-dependency-diagnostics/1.0`
- `scds-change-impact-assessment/1.0`

**Boundary:** graph edges are declared or structural relationships, not causal proof. Node degree is not importance. Downstream reachability queues records for review; it does not automatically invalidate a conclusion, approve an action, select a winner, or change a recommendation.

---

# Sustainable Catalyst Decision Studio v2.7.0

## Site Intelligence Context Integration

Decision Studio v2.7.0 builds on the verified v2.6.0 Lab + Workbench Native Handoffs release and adds a first-class context bridge from Site Intelligence into the Unified Decision Object. Signals retain source identity, geography, observation time, freshness, methodology, limitations, provenance, exact source payloads, and deterministic fingerprints. Explicit scenario links remain descriptive relationships and never change scores automatically or infer likelihood.

### v2.7.0 endpoints

- `/site-intelligence-context/contracts`
- `/site-intelligence-context/template`
- `/site-intelligence-context/build`
- `/site-intelligence-context/validate`
- `/decision-object/site-intelligence-context`
- `/decision-packet/site-intelligence-context`

### v2.7.0 contracts

- `scds-site-intelligence-context-bundle/1.0`
- `scds-site-intelligence-signal-snapshot/1.0`
- `scds-site-intelligence-context-receipt/1.0`

**Boundary:** Site Intelligence owns observation/context. Decision Studio does not infer causality, scenario likelihood, approval, or recommendation from a signal.

---

# Sustainable Catalyst Decision Studio v2.6.0

**Lab + Workbench Native Handoffs**

Decision Studio v2.6.0 builds on the verified v2.5.0 Scenario Comparison & Stress Testing release and adds first-class, provenance-preserving analytical exchange with Research Lab and Workbench. Decision Studio can receive source-owned analytical artifacts, create bounded requests for additional analysis or computation, attach returned artifacts to the Unified Decision Object, and retain request/return lineage without executing Lab experiments or Workbench computation itself.

## v2.6.0 endpoints

- `GET /native-handoffs/contracts`
- `GET /native-handoffs/template`
- `POST /native-handoffs/receive`
- `POST /native-handoffs/request`
- `POST /native-handoffs/return`
- `POST /decision-object/native-handoff`
- `POST /decision-packet/native-handoff`

## v2.6.0 contracts

- `scds-analysis-handoff/1.0`
- `scds-computation-handoff/1.0`
- `scds-handoff-receipt/1.0`
- `scds-analysis-request/1.0`

Source artifact payloads remain intact and are SHA-256 fingerprinted. Handoff acceptance confirms contract/fingerprint handling only; it is not scientific validation, engineering verification, approval, or recommendation.

---

## Previous release documentation

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
