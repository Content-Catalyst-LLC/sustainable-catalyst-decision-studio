# Decision Studio v1.14.0 — Outcomes, Monitoring, and Reassessment

## Purpose

v1.14.0 closes the gap between approving a decision and learning from its implementation. The Outcome Monitoring record is a structured, source-aware part of the Decision Packet that compares expected and observed results, surfaces material deviations, and creates explicit human reassessment paths.

## Contracts

- `scds-outcome-monitoring/1.0`
- `scds-reassessment-event/1.0`
- `scds-decision-registry-entry/1.0`
- Additive Decision Packet `scds-decision-packet/1.7`

Versioned contract and sample files are available in `data/` and in the packaged WordPress plugin.

## Monitoring model

A monitoring record can contain:

- Decision and implementation owners
- Commitments and measurable targets
- Indicators with baselines, targets, actual values, units, direction, and tolerance
- Source-aware observations
- Site Intelligence source and methodology connections
- Monitoring cadence and next review date
- Implementation milestones
- Emerging risks
- Assumption invalidations
- Reassessment triggers and their evaluations
- Post-implementation reviews
- Lessons learned
- Reassessment history
- Implementation amendments
- A Decision Registry entry

## Indicator evaluation

Indicators support increasing, decreasing, and acceptable-range targets. The engine calculates current status, variance from target, and progress where sufficient baseline and target data exist. Output states are `no_data`, `on_track`, `at_risk`, and `off_track`.

These deterministic results are screening signals. They do not establish attribution or prove that the decision caused an observed outcome.

## Reassessment triggers

Supported triggers include:

- Indicator above a threshold
- Indicator below a threshold
- Overdue implementation milestone
- Invalidated or materially changed assumption
- Active high or critical emerging risk
- Scheduled reassessment date

Triggered conditions move the monitoring record to `reassessment_required`; they do not automatically amend, suspend, approve, or retire a decision.

## Human authority

Named human actors are required for:

- Formal reassessment
- Implementation amendment
- Decision retirement

Reassessment records, amendments, and monitoring events contain hashes for integrity review. Human governance remains authoritative, and AI cannot approve, certify, assure, or professionally sign off the result.

## Decision Registry

Every evaluation creates or updates a compact Decision Registry entry with:

- Decision Packet identity and title
- Governance and lifecycle states
- Decision and implementation owners
- Monitoring status
- Last monitoring and next reassessment dates
- Target summary
- Amendment and reassessment counts
- Retirement date where applicable
- SHA-256 registry hash

The registry entry is designed for future Platform Core and institutional API integration without exposing private packet content by default.

## WordPress workspace

Use:

```text
[sc_decision_studio mode="outcomes" title="Outcomes, Monitoring, and Reassessment"]
```

The workspace supports monitoring JSON, observations, reassessments, amendments, retirement, local/backend parity, packet persistence, and monitoring downloads. WordPress database version 1.8.0 adds `outcome_monitoring_json` to saved Decision Packet records.

## API routes

```text
GET  /outcomes/template
POST /outcomes/evaluate
POST /outcomes/record-observation
POST /outcomes/reassess
POST /outcomes/amend
POST /outcomes/retire
POST /decision-packet/outcomes
```

Matching WordPress REST routes are exposed under `/wp-json/scds/v1`.

## Export support

The export bundle includes:

- `outcome_monitoring_json`
- `decision_registry_json`
- `reassessment_history_json`

## Preserved layers

v1.14.0 preserves the v1.13 Publication Studio, v1.12 Decision Packs, v1.11 Decision Rooms, v1.10 Scenario Studio, v1.9 Governance Center, v1.8 typed platform handoffs, saved packets, audit/provenance, and legacy adapters.
