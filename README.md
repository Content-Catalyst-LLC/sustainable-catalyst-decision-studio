# Sustainable Catalyst Decision Studio v1.13.0

## Decision Briefing and Publication Studio

Decision Studio is the governance, synthesis, and publication layer of the Sustainable Catalyst platform. v1.13.0 turns a governed Decision Packet into citation-native executive memos, technical reports, leadership briefs, alternatives analyses, public dossiers, evidence and audit appendices, implementation plans, dissenting views, and monitoring plans.

The release preserves Decision Packs, private Decision Rooms, advanced scenarios, human governance, typed platform evidence, saved packets, and audit/provenance records. Reviewed and public outputs remain blocked until the governance gate permits release.

## Publication capabilities

- Twelve governed publication types
- Harvard bibliography and stable evidence anchors
- Private, institutional, and public section visibility
- Deterministic redaction records
- Markdown, print-ready HTML, JSON, bibliography, and publication manifests
- Draft handoffs to Knowledge Library, Research, Publications, and Channel
- Additive Decision Packet `scds-decision-packet/1.6`
- No AI approval, assurance, certification, or professional sign-off

## Primary endpoints

- `GET /publication-studio/template`
- `POST /publication-studio/generate`
- `POST /publication-studio/redact`
- `POST /publication-studio/handoff`
- `POST /decision-packet/publication`

WordPress exposes matching routes under `/wp-json/scds/v1` and a dedicated shortcode mode:

```text
[sc_decision_studio mode="publication" title="Decision Briefing and Publication Studio"]
```

## Preserved platform layers

v1.13.0 is additive and preserves:

- v1.12.0 Institutional and Domain Decision Packs
- v1.11.0 Collaborative Decision Rooms
- v1.10.0 Advanced Scenario and Sensitivity Studio
- v1.9.0 Decision Governance and Review Center
- v1.8.0 typed platform handoffs
- Saved Decision Packets, exports, audit/provenance, readiness gates, and integrated briefs
- Existing shortcodes, REST routes, and legacy Catalyst adapters

## Boundary

Generated publications are governed decision-support artifacts. They are not legal, engineering, financial, medical, tax, compliance, fiduciary, ESG/SDG assurance, or other professional certification. Human review remains authoritative.

See `docs/V1130_DECISION_BRIEFING_PUBLICATION_STUDIO.md` and `docs/ROADMAP.md`.
