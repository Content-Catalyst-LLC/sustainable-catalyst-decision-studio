# Decision Studio v1.5.0 — Scenario Comparison and Workbench Handoff

Decision Studio v1.5.0 adds a deeper scenario comparison and Workbench handoff layer.

## Scenario Comparison

The scenario comparison engine normalizes built-in Decision Studio scenarios and imported Catalyst Analytics R artifacts into a comparison matrix with:

- scenario label and option ID
- annual and total avoided emissions
- NPV
- payback
- risk score
- confidence
- implementation complexity
- decision score
- delta versus baseline
- tradeoff note
- recommended option
- sensitivity flags

## Workbench Handoff

The Workbench handoff router recommends deeper tools when a decision needs more analysis:

- economics forecasting and scenario analysis
- risk and resilience matrix
- Graph Studio parameter sensitivity
- engineering-mode calculation notes
- environmental QA/QC
- symbolic formula review
- advanced domain calculator library

Each handoff includes a tool ID, label, reason, priority, shortcode, and payload summary.

## Backend endpoints

```text
GET  /scenario-comparison/template
POST /scenario-comparison
POST /decision-packet/scenario-comparison
GET  /workbench/handoffs
POST /workbench/handoff
POST /decision-packet/workbench-handoff
```

## WordPress routes

```text
/wp-json/scds/v1/scenario-comparison/template
/wp-json/scds/v1/scenario-comparison
/wp-json/scds/v1/decision-packet/scenario-comparison
/wp-json/scds/v1/workbench/handoffs
/wp-json/scds/v1/workbench/handoff
/wp-json/scds/v1/decision-packet/workbench-handoff
```

## Boundary

Scenario comparison is a decision-support screen, not a forecast. Workbench handoffs are analytical supports, not professional approval, certification, assurance, or expert signoff.
