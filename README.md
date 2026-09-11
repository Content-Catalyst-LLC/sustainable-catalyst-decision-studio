# Sustainable Catalyst Decision Studio v2.1.0

## Unified Decision Object Model & Platform Context Foundation

Decision Studio v2.1.0 makes the **decision** a first-class cross-product object while preserving Decision Packet 2.0 and the complete Connected Decision Intelligence Platform. The new `scds-decision-object/1.0` model carries the decision question, objective, alternatives, criteria, constraints, assumptions, evidence, models, scenarios, uncertainty, stakeholders, tradeoffs, recommendation, confidence, counterarguments, provenance, decision record, rationale, and outcome review.

`scds-platform-context/1.0` gives Knowledge Library, Research Librarian, Site Intelligence, Workbench, Research Lab, Platform Core, and Decision Studio explicit roles around that object. Packet promotion is additive and projection is reversible: the source packet and its unknown fields are preserved rather than silently flattened.

### v2.1.0 endpoints

- `GET /decision-object/template`
- `GET /platform-context/template`
- `POST /decision-object/from-packet`
- `POST /decision-object/normalize`
- `POST /decision-object/context`
- `POST /decision-object/to-packet`
- `POST /decision-packet/decision-object`

WordPress route parity lives under `/wp-json/scds/v1`, with `[sc_decision_studio mode="decision-object"]`.

## Connected Decision Intelligence Platform

Decision Studio v2.0.1 restores visible navigation and packet handoffs for Catalyst Canvas, Catalyst Data, Catalyst Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, and Catalyst Grit while preserving the full connected platform. Decision Studio is the decision orchestration, governance, publication, implementation, monitoring, and accountability layer of the Sustainable Catalyst platform. v2.0.0 connects the full lifecycle:

**Frame → Research → Gather Evidence → Model → Compare → Challenge Assumptions → Review → Approve → Publish → Implement → Monitor → Reassess**

The release advances the additive Decision Packet to `scds-decision-packet/2.0` while preserving all v1.x governance, collaboration, scenario, publication, monitoring, public API, offline, and release-hardening capabilities.

## Connected platform capabilities

- Twelve-stage lifecycle assessment with completion, blockers, and current-stage detection
- Cross-product action routing to Research Librarian, Knowledge Library, Site Intelligence, Workbench, Research Lab, Decision Studio, Platform Core, Contact and Engagement, Publications, and Channel
- Decision intelligence graph connecting evidence, indicators, models, experiments, alternatives, risks, publications, entities, and reassessments
- Portfolio attention index for up to 100 Decision Packets
- Prepared connected-exchange manifests with section-level SHA-256 hashes
- Human-confirmed lifecycle transitions with tamper-evident history
- Additive WordPress persistence, browser fallback, export support, and offline recovery

## Human-control boundary

Lifecycle assessment can recommend work and route gaps, but it cannot approve, publish, externally deliver, amend, suspend, retire, certify, assure, or professionally sign off a decision. Those actions require authorized humans and any required qualified professional review.

## Primary endpoints

- `GET /connected-platform/template`
- `POST /connected-platform/assess`
- `POST /connected-platform/transition`
- `POST /connected-platform/portfolio`
- `POST /connected-platform/graph`
- `POST /connected-platform/exchange`
- `POST /connected-platform/history/verify`
- `POST /decision-packet/connected-platform`

WordPress exposes matching routes under `/wp-json/scds/v1` and the workspace:

```text
[sc_decision_studio mode="connected" title="Connected Decision Intelligence Platform"]
```

See `docs/V2000_CONNECTED_DECISION_INTELLIGENCE_PLATFORM.md` and `docs/ROADMAP.md`.
