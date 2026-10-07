# Decision Studio v3.8.0 — Global Impact Catalyst Python Domain Migration

Decision Studio v3.8.0 migrates Global Impact Catalyst into the authoritative Python/PostgreSQL domain architecture introduced in v3.4.0 and extended through Canvas, Finance, and Narrative Risk.

## Core changes

- Adds `scds-global-impact-domain/1.0`.
- Makes Global Impact Catalyst `python-domain-authoritative` with `python-postgresql` storage authority.
- Preserves Workbench as compute authority for quantitative impact calculations.
- Normalizes impact claims into `claims`, evidence relationships into `evidence_links`, and impact indicators into `artifacts` using explicit `domain=global-impact` ownership metadata.
- Preserves environmental, social, economic, SDG, carbon, resource, distributional, stakeholder, pathway, target, and provenance context in the canonical Global Impact Decision Object.
- Adds source-preserving legacy Global Impact import.
- Preserves the existing 20-table PostgreSQL schema and Alembic revision `0001_v330_pg_foundation`; there is no new schema migration.
- Preserves Canvas, Finance, and Narrative Risk authority and cross-domain data isolation.

## Boundaries

Global Impact Catalyst does not treat SDG alignment as proof of impact, modeled impact as observed outcome, or indicator change as causal attribution. Decision Studio does not execute impact models in this release. Automatic impact verification, sustainability rating, recommendation, and approval remain disabled. Final decision authority remains human-governed.

## Certified surface

- 242 API routes
- 18 route registries
- 11 Global Impact routes
- 20 persistence tables
- 4 authoritative Decision Studio domains
