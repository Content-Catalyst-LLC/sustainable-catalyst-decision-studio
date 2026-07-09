# Decision Studio v1.1.1 — Audit & Provenance Upgrade

This release upgrades the Decision Studio audit layer from a basic assumptions log into a structured audit and provenance appendix.

## Added

- Decision Packet audit/provenance schema
- Module Artifact Ledger
- Source Ledger
- Assumptions Register
- Calculation Trace
- Claim Trace
- Change Log
- Review Status
- Exportable Audit Appendix

## Backend endpoints

```text
GET  /audit/template
POST /audit/generate
```

## WordPress REST routes

```text
/wp-json/scds/v1/audit/template
/wp-json/scds/v1/audit/generate
```

## Boundary

This is educational decision support and does not certify outcomes or replace professional legal, financial, engineering, medical, tax, compliance, assurance, or safety-critical review.
