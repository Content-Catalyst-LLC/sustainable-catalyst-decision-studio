# v3.12.0 — Module Interoperability & Shared Evidence

## Purpose

Create a canonical interoperability layer that lets all four Decision Studio modules reuse the same evidence identity without duplicating evidence payloads or transferring ownership.

## Model

A `scds-shared-evidence-reference/1.0` record contains a stable `evidence_ref`, owner module, source/provenance references, optional artifact reference, and one or more module-specific usage relationships. The canonical interoperability document is `scds-module-interoperability/1.0`.

Decision Studio stores only the relationship layer. Platform Core remains authoritative for evidence identity and source provenance. Module-specific interpretation remains explicit.

## Persistence

The canonical document uses `decision_objects` with object type `module-interoperability-shared-evidence`. Usage edges use existing `evidence_links` rows tagged with `domain=module-interoperability`. Replacing interoperability state only deletes/rebuilds those tagged rows; Narrative Risk and Global Impact evidence links are preserved.

## Contradiction visibility

Explicit contradiction annotations are retained without silent reconciliation. Diagnostics may surface support/refute relationship disagreement against the same claim reference, but this is labeled as a relationship disagreement rather than truth adjudication.

## Governance

Evidence reuse never establishes truth, causality, recommendation, approval, or a final decision. Final decision authority remains human-governed.
