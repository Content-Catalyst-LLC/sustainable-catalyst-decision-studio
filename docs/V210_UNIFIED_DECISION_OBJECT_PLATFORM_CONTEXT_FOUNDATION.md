# Decision Studio v2.1.0 — Unified Decision Object Model & Platform Context Foundation

v2.1.0 turns the decision itself into a first-class Sustainable Catalyst platform object. It is an additive architectural release: `scds-decision-packet/2.0` remains supported, existing v2.0.x workflows remain intact, and packet-to-object migration is reversible.

## Unified Decision Object

The canonical object schema is `scds-decision-object/1.0`. Its core decision fields are:

`question → objective → alternatives → criteria → constraints → assumptions → evidence → models → scenarios → uncertainties → stakeholders → tradeoffs → recommendation → confidence → counterarguments → provenance → decision → rationale → outcome_review`

The model also includes platform context, typed links, compatibility metadata, durable identity, status, and timestamps.

## Platform Context

`scds-platform-context/1.0` establishes stable roles for the products that contribute to a decision:

- Knowledge Library — evidence
- Research Librarian — research routing
- Site Intelligence — real-world context
- Workbench — computation
- Research Lab — analysis
- Platform Core — infrastructure and durable provenance
- Decision Studio — alternatives, tradeoffs, recommendation, governance, and the decision record

Platform context is descriptive and provenance-aware. A link never means that an external product accepted, validated, or approved an artifact unless the source product explicitly records that state.

## Compatibility model

Decision Packets remain the broad workflow and persistence envelope. Decision Objects provide a cleaner cross-product semantic representation. Promotion retains a complete source-packet reference and SHA-256 fingerprint. Projection begins with that source packet when available, updates mapped Decision Object fields, and preserves unknown packet fields.

This lets v2.1.0 become the bridge to future evidence bundles, uncertainty analysis, Decision Graphs, and richer scenario/criteria releases without forcing a breaking migration now.

## Backend routes

- `GET /decision-object/template`
- `GET /platform-context/template`
- `POST /decision-object/from-packet`
- `POST /decision-object/normalize`
- `POST /decision-object/context`
- `POST /decision-object/to-packet`
- `POST /decision-packet/decision-object`

WordPress exposes route parity under `/wp-json/scds/v1` and a new workspace tab/shortcode mode: `[sc_decision_studio mode="decision-object"]`.

## Human-control boundary

The unified object organizes evidence, computation, uncertainty, tradeoffs, recommendations, provenance, and outcomes. It does not automatically approve, publish, externally deliver, certify, assure, or professionally sign off a consequential decision.
