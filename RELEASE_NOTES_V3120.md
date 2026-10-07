# Decision Studio v3.12.0 — Module Interoperability & Shared Evidence

v3.12.0 adds a governed cross-module interoperability layer across Canvas, Finance, Narrative Risk, and Global Impact Catalyst.

## New contracts

- `scds-module-interoperability/1.0`
- `scds-shared-evidence-reference/1.0`

## Core behavior

Evidence is reused by stable reference rather than copied. Each shared evidence reference preserves an owner module, explicit consumer-module usages, module-specific evidence relationships, source/provenance references, and optional artifact references. Cross-module evidence reuse is a relationship, not an ownership transfer.

Contradictions remain visible. Explicit contradiction annotations are first-class, and diagnostics can surface relation disagreements such as one module using the same evidence to support a claim while another uses it to refute that claim. These diagnostics do not adjudicate truth or infer causality.

## Persistence

No PostgreSQL schema migration is introduced. The release reuses the existing `decision_objects` table for the canonical interoperability document and `evidence_links` for module-specific shared-evidence usage edges. Alembic remains `0001_v330_pg_foundation`; the persistence table count remains 20.

## Boundaries

- Evidence identity and source provenance authority remain Platform Core.
- Decision Studio owns sharing/usage relationships and contradiction visibility.
- Evidence payloads are not duplicated.
- Sharing never transfers module ownership.
- Shared evidence does not imply shared interpretation, truth, causality, recommendation, or approval.
- Finance and Global Impact computation remain Workbench responsibilities.
- Final decision authority remains human-governed.

## API

Eight routes are added under `/module-interoperability`, bringing Decision Studio to 272 certified API routes across 22 route registries.
