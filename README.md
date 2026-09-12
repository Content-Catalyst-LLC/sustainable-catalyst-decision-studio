# Sustainable Catalyst Decision Studio v2.3.1

## Criteria, Alternatives & Tradeoff Matrix

Decision Studio v2.3.1 builds on the v2.2 Evidence & Source Bundle layer with first-class criteria, alternatives, and transparent alternative-by-criterion comparison. `scds-criteria-set/1.0` preserves explicit weights, directions, scales, thresholds, evidence references, and provenance. `scds-alternatives-set/1.0` gives candidate choices stable identities. `scds-tradeoff-matrix/1.0` records evidence-linked evaluations and produces completeness, threshold, review, and matrix-coverage diagnostics through `scds-tradeoff-diagnostics/1.0`.

Weighted scores are comparative aids only. The release does not automatically select a winner or generate a recommendation. Human review remains required for criteria choice, weights, interpretation, and consequential decisions.

### v2.3.1 endpoints

- `GET /criteria/template`
- `POST /criteria/build`
- `GET /alternatives/template`
- `POST /alternatives/build`
- `GET /tradeoff-matrix/template`
- `POST /tradeoff-matrix/build`
- `POST /decision-object/tradeoffs`
- `POST /decision-packet/tradeoff-matrix`

WordPress route parity lives under `/wp-json/scds/v1`, with `[sc_decision_studio mode="tradeoffs" title="Criteria, Alternatives & Tradeoff Matrix"]`.

## v2.2.0 evidence foundation


Decision Studio v2.2.0 builds on the v2.1 Unified Decision Object with first-class source and evidence bundles. `scds-source-bundle/1.0` preserves reusable source identity, citation, provenance, quality, freshness, review status, and SHA-256 fingerprints. `scds-evidence-bundle/1.0` links claims to source IDs and exposes citation coverage, unresolved links, review gaps, and support/challenge contradictions through `scds-evidence-coverage/1.0`.

Evidence bundles attach directly to the Decision Object and project additively back into Decision Packet 2.0. The system improves traceability and review; it does not automatically verify truth or approve evidence.

### v2.2.0 endpoints

- `GET /source-bundle/template`
- `POST /source-bundle/build`
- `GET /evidence-bundle/template`
- `POST /evidence-bundle/build`
- `POST /evidence-bundle/merge`
- `POST /decision-object/evidence`
- `POST /decision-packet/evidence-bundle`

WordPress route parity lives under `/wp-json/scds/v1`, with `[sc_decision_studio mode="evidence" title="Evidence & Source Bundles"]`.

## v2.1.0 foundation

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
