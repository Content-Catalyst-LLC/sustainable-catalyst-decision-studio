# Decision Studio v1.2.0 — Module Artifact Adapters

Decision Studio v1.2.0 turns the integrated workflow into a working artifact import layer.

## Supported artifact sources

- Catalyst Canvas → `decision_framing`
- Catalyst Data → `evidence_and_measurement.records` and `sources`
- Catalyst Analytics R → `scenarios.records`
- Global Impact Catalyst → `impact_measurement.records`
- Narrative Risk → `claim_and_risk_review.records` and `risks`
- Catalyst Finance → `financial_tradeoffs` and `calculation_trace`
- Catalyst Grit → `execution_and_recovery` and `risks`
- Workbench → `workbench_calculations` and `calculation_trace`

## Backend endpoints

```text
GET  /integrations/adapters
POST /integrations/import
POST /decision-packet/import
POST /decision-packet/analyze
```

## WordPress routes

```text
/wp-json/scds/v1/integrations/adapters
/wp-json/scds/v1/integrations/import
/wp-json/scds/v1/decision-packet/import
```

## Boundary

Adapters normalize user-provided JSON exports. They do not verify truth, professional compliance, source quality, certification status, assurance, or decision approval.
