# Sustainable Catalyst Decision Studio v1.12.0

**Institutional and Domain Decision Packs**

Decision Studio is the Sustainable Catalyst platform's governed decision-orchestration layer. v1.12.0 adds reusable institutional methodologies that configure the Decision Packet without replacing evidence, scenario analysis, collaboration, governance, or qualified human review.

## v1.12.0 highlights

- Ten institutional and domain Decision Packs
- Required intake and transparent decision criteria
- Required evidence and readiness diagnostics
- Suggested Site Intelligence indicators
- Structured Workbench model routing
- Required human review roles and risk questions
- Domain readiness rules and briefing templates
- Browser, WordPress, and FastAPI contract parity
- Decision Packet `scds-decision-packet/1.5`
- Pack contracts `scds-institutional-decision-pack/1.0` and `scds-decision-pack-application/1.0`

## Included Decision Packs

1. Climate and Energy Strategy
2. Infrastructure and Capital Investment
3. Urban Resilience
4. Sustainable Procurement
5. Responsible AI and Technology Governance
6. Research Program Approval
7. Environmental Intervention
8. Humanitarian and Development Programming
9. Organizational Policy
10. Advisory Diagnostic and Recommendation

## Primary endpoints

- `GET /decision-packs/catalog`
- `GET /decision-packs/{pack_id}`
- `POST /decision-packs/validate`
- `POST /decision-packs/apply`
- `POST /decision-packet/domain-pack`

WordPress exposes matching routes under `/wp-json/scds/v1` and a dedicated shortcode mode:

```text
[sc_decision_studio mode="packs" title="Institutional Decision Packs"]
```

## Preserved platform layers

v1.12.0 is additive and preserves:

- v1.11.0 Collaborative Decision Rooms
- v1.10.0 Advanced Scenario and Sensitivity Studio
- v1.9.0 Decision Governance and Review Center
- v1.8.0 typed platform handoffs
- Saved Decision Packets, exports, audit/provenance, readiness gates, and integrated briefs
- Existing shortcodes, REST routes, and legacy Catalyst adapters

## Boundary

Decision Packs are decision-support methodologies. They are not legal, engineering, financial, medical, tax, compliance, fiduciary, ESG/SDG assurance, or other professional certification. AI may organize evidence and draft questions but cannot approve, certify, assure, or sign off a decision.

See `docs/V1120_INSTITUTIONAL_DOMAIN_DECISION_PACKS.md` and `docs/ROADMAP.md`.
