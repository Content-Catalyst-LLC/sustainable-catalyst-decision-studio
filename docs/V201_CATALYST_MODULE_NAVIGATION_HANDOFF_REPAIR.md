# Decision Studio v2.0.1 — Catalyst Module Navigation and Handoff Repair

## Purpose

v2.0.1 repairs the gap between adapter compatibility and visible user workflow. Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, and Grit are now first-class destinations inside the Decision Studio Workflow panel.

## User workflow

1. Open **Catalyst Modules** in Decision Studio.
2. Choose a module card.
3. Use **Send Decision Packet** to prepare a browser-local handoff and open the module with `scds_handoff`, `scds_source`, and `scds_return` query parameters.
4. Complete work in the specialized module and export its JSON artifact.
5. Return to Decision Studio, choose **Import Artifact**, paste JSON, validate, and merge it into the mapped packet section.

## Module map

| Module | Stage | Packet target | Default route |
|---|---|---|---|
| Catalyst Canvas | Frame | `decision_framing` | `/narrative-strategy/catalyst-canvas/` |
| Catalyst Data | Anchor | `evidence_and_measurement` | `/infrastructure/catalyst-data/` |
| Catalyst Analytics R | Model | `scenarios` | `/modeling-analytics/catalyst-analytics-r/` |
| Global Impact Catalyst | Measure | `impact_measurement` | `/modeling-analytics/global-impact-catalyst/` |
| Narrative Risk | Review | `claim_and_risk_review` | `/narrative-strategy/narrative-risk/` |
| Catalyst Finance | Evaluate | `financial_tradeoffs` | `/modeling-analytics/catalyst-finance/` |
| Catalyst Grit | Sustain | `execution_and_recovery` | `/human-systems/catalyst-grit/` |

## Handoff boundary

The browser handoff does not silently transmit data to a server. It stores a structured `scds-catalyst-module-handoff/1.0` record in local storage and opens the chosen route. Destination products must explicitly import it. Manual JSON export/import remains the guaranteed compatibility path.

## Administration

WordPress administrators can change all seven routes under **Decision Studio → Methodology Settings → Catalyst Module Routes** and can disable browser-local handoffs without disabling artifact import.
