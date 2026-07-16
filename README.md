# Sustainable Catalyst Decision Studio v1.14.0

## Outcomes, Monitoring, and Reassessment

Decision Studio is the governance, synthesis, publication, and accountability layer of the Sustainable Catalyst platform. v1.14.0 extends the governed Decision Packet beyond approval and publication into implementation monitoring, actual-versus-expected comparison, human reassessment, amendment, retirement, and institutional learning.

The release preserves publication, institutional Decision Packs, private Decision Rooms, advanced scenarios, human governance, typed platform evidence, saved packets, and audit/provenance records. Monitoring records evidence and implementation status; it does not automatically certify causality, success, compliance, or professional assurance.

## Outcome-monitoring capabilities

- Decision commitments, accountable owners, targets, and indicators
- Baseline, target, actual, variance, and progress comparison
- Increase, decrease, and acceptable-range indicator directions
- Source-aware observations and Site Intelligence connections
- Implementation milestones and overdue detection
- Emerging risks and assumption invalidation
- Threshold, milestone, risk, assumption, and scheduled reassessment triggers
- Human-owned reassessment records
- Human-authorized implementation amendments and retirement
- Post-implementation reviews, lessons learned, and a durable Decision Registry entry
- SHA-256 event and record hashes
- Additive Decision Packet `scds-decision-packet/1.7`

## Primary endpoints

- `GET /outcomes/template`
- `POST /outcomes/evaluate`
- `POST /outcomes/record-observation`
- `POST /outcomes/reassess`
- `POST /outcomes/amend`
- `POST /outcomes/retire`
- `POST /decision-packet/outcomes`

WordPress exposes matching routes under `/wp-json/scds/v1` and a dedicated shortcode mode:

```text
[sc_decision_studio mode="outcomes" title="Outcomes, Monitoring, and Reassessment"]
```

## Preserved platform layers

v1.14.0 is additive and preserves:

- v1.13.0 Decision Briefing and Publication Studio
- v1.12.0 Institutional and Domain Decision Packs
- v1.11.0 Collaborative Decision Rooms
- v1.10.0 Advanced Scenario and Sensitivity Studio
- v1.9.0 Decision Governance and Review Center
- v1.8.0 typed platform handoffs
- Saved Decision Packets, exports, audit/provenance, readiness gates, and integrated briefs
- Existing shortcodes, REST routes, and legacy Catalyst adapters

## Boundary

Outcome records document observed implementation evidence and trigger structured human review. They are not causal attribution, legal or regulatory certification, engineering acceptance, financial assurance, clinical judgment, tax advice, fiduciary approval, or ESG/SDG assurance. Accountable human decision owners remain authoritative for reassessment, amendment, suspension, and retirement.

See `docs/V1140_OUTCOMES_MONITORING_REASSESSMENT.md` and `docs/ROADMAP.md`.
