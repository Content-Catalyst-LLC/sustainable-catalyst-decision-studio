# Decision Studio v2.2.0 — Evidence & Source Bundles

Decision Studio v2.2.0 turns the `evidence` field introduced in the Unified Decision Object into a provenance-aware evidence layer rather than an unstructured list.

## New schemas

- `scds-source-bundle/1.0` — reusable source identities, citations, quality/freshness metadata, provenance, fingerprints, review state, and deterministic deduplication.
- `scds-evidence-bundle/1.0` — evidence claims linked to one or more source IDs, with stance, citations, confidence, quality, limitations, provenance, and human review state.
- `scds-evidence-coverage/1.0` — diagnostics for citation coverage, unresolved source references, review gaps, and visible support/challenge contradictions.

## Design principles

1. **Sources are first-class objects.** Evidence references source identities instead of copying citations into disconnected fields.
2. **Raw source and evidence payloads are preserved.** Normalization is additive and traceable.
3. **Deduplication is deterministic.** Canonical SHA-256 fingerprints identify repeated source/evidence payloads without silently deleting the original relationship.
4. **Contradictions remain visible.** Support and challenge records for the same normalized claim are surfaced rather than collapsed.
5. **Coverage is diagnostic, not epistemic authority.** A 100% citation-coverage score means every evidence record has a source/citation relationship; it does not mean every claim is true.
6. **Review state remains human-owned.** `needs_review`, `reviewed`, `accepted`, and `approved` are recorded states; the system does not automatically grant approval.

## FastAPI routes

- `GET /source-bundle/template`
- `POST /source-bundle/build`
- `GET /evidence-bundle/template`
- `POST /evidence-bundle/build`
- `POST /evidence-bundle/merge`
- `POST /decision-object/evidence`
- `POST /decision-packet/evidence-bundle`

WordPress exposes equivalent routes below `/wp-json/scds/v1` and adds an **Evidence & Sources** workspace tab plus `mode="evidence"`.

## Decision Object integration

The v2.1 Decision Object is preserved. v2.2 adds:

- `evidence_bundles[]`
- `source_bundles[]`
- normalized `evidence[]` records linked to the active bundle
- provenance events when a bundle is attached

Projection back to Decision Packet 2.0 preserves bundle collections additively.

## Platform integration

Knowledge Library remains the primary durable source/evidence provider. Research Librarian can contribute discovery, evidence-gap, contradiction, and follow-up records. Site Intelligence, Workbench, Research Lab, and other platform products can contribute evidence records with explicit provenance rather than being treated as interchangeable source types.

## Boundary

Evidence & Source Bundles improve structure, traceability, and review quality. They do **not** automatically verify factual truth, certify evidence sufficiency, replace expert source appraisal, or authorize consequential decisions.
