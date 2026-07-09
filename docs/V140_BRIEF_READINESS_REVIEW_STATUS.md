# Decision Studio v1.4.0 — Brief Readiness and Review Status

Decision Studio v1.4.0 adds a section-level readiness and review-status layer for integrated Decision Packets.

## What it adds

- Brief Readiness tab in the public Decision Studio interface.
- Section-level readiness scoring for framing, evidence, scenarios, impact, claims, finance, recovery, audit/provenance, and synthesis.
- Review states: not started, needs evidence, needs review, needs expert review, ready for draft, ready for export.
- Unresolved issue flags with severity, section, issue, and recommended action.
- Export gates for draft brief and reviewed export.
- Professional-reliance gate that remains false without qualified human review.
- Backend and WordPress fallback routes.

## Backend endpoints

```text
GET  /review/status-template
POST /brief-readiness
POST /decision-packet/readiness
POST /review/status
```

## WordPress routes

```text
/wp-json/scds/v1/review/status-template
/wp-json/scds/v1/brief-readiness
/wp-json/scds/v1/decision-packet/readiness
/wp-json/scds/v1/review/status
```

## Shortcode

```text
[sc_decision_studio mode="full" title="Sustainable Catalyst Decision Studio"]
[sc_decision_studio mode="readiness" title="Decision Readiness Review"]
```

## Boundary

Brief readiness is a workflow quality gate. It is not approval, professional signoff, certification, assurance, compliance review, legal advice, financial advice, investment advice, engineering review, medical advice, tax advice, or safety-critical validation.
