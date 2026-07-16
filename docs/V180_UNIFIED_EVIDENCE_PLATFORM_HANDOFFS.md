# Decision Studio v1.8.0 — Unified Evidence and Platform Handoffs

## Purpose

v1.8.0 makes Decision Studio the governance and synthesis layer for the current Sustainable Catalyst platform. Product outputs enter through a common typed envelope rather than unstructured product-specific JSON.

## Platform workflow

**Knowledge Library → Research Librarian → Site Intelligence → Workbench → Research Lab → Platform Core → Decision Studio**

## Schemas

- Platform artifact: `scds-platform-artifact/1.0`
- Evidence record: `scds-evidence-record/1.0`
- Decision Packet: `scds-decision-packet/1.1`

The Decision Packet change is additive. Existing fields and legacy adapters remain available.

## Required artifact envelope

Every typed artifact contains:

- `artifact_schema`
- `artifact_id`
- `artifact_type`
- `source`
- `provenance`
- `payload`

The source block retains product identity, product version, artifact URL, and timestamps. Provenance retains methodology, freshness, confidence, integrity hash, and transformation history.

## Product mappings

| Product | Primary Decision Packet targets |
|---|---|
| Knowledge Library | evidence registry, sources, citations, quotations |
| Research Librarian | research routes, evidence gaps, follow-up questions |
| Site Intelligence | live evidence, methodologies, source health |
| Workbench | calculations, assumptions, validation checks, technical artifacts |
| Research Lab | experiments, datasets, validation, limitations |
| Platform Core | entities, Evidence Ledger records, relationships, provenance links |

## API additions

- `GET /integrations/platform`
- `GET /integrations/contracts`
- `GET /integrations/contracts/{product_id}`
- `POST /integrations/validate`
- `POST /integrations/import-batch`
- `GET /decision-packet/platform-handoffs`

Equivalent WordPress routes are available under `/wp-json/scds/v1`.

## Integrity behavior

Decision Studio calculates a canonical SHA-256 hash over the artifact payload. A supplied hash that differs from the calculated value is rejected by validation. Artifacts without a supplied hash remain importable but are marked as not independently verified.

## Compatibility

The earlier Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, and Workbench adapters remain available. New integrations should use the typed artifact envelope.

## Boundaries

Decision Studio organizes evidence and review. Integrity checks confirm payload consistency, not truth, professional approval, certification, legal compliance, engineering validity, or financial assurance.
