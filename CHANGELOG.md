
## v1.3.0 — Integrated Brief Generator

- Added professional integrated decision brief generator.
- Added backend endpoints `POST /integrated-brief` and `POST /decision-packet/brief`.
- Added WordPress REST route `/wp-json/scds/v1/integrated-brief`.
- Synthesizes Decision Packet sections: framing, evidence, scenarios, impact, claims, finance, recovery, audit, and Workbench handoffs.
- Added Markdown, HTML, JSON, and print/PDF-ready export flow.
- Added tests for integrated brief generation and Decision Packet brief synthesis.


## v1.2.0 — Module Artifact Adapters

- Added adapter catalog for Catalyst Canvas, Catalyst Data, Catalyst Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, Catalyst Grit, and Workbench.
- Added backend artifact import endpoints for normalizing module JSON exports into the Decision Packet.
- Added WordPress REST import routes with backend proxy and deterministic local fallback.
- Added public UI for pasting/importing JSON artifacts inside the Integrated Workflow tab.
- Added Decision Packet merge logic, module slot updates, source ledger/assumption/calculation/claim integration, and readiness analysis.
- Updated audit/provenance and Decision Packet versions to v1.2.0.

## v1.1.1 - Audit & Provenance Upgrade

- Added Audit & Provenance schema for Decision Packet reviews.
- Added module artifact ledger, source ledger, assumptions register, calculation trace, claim trace, change log, and review status.
- Added backend endpoints `/audit/template` and `/audit/generate`.
- Added WordPress REST routes `/wp-json/scds/v1/audit/template` and `/wp-json/scds/v1/audit/generate`.
- Added exportable audit appendix UI and audit JSON download.

## v1.1.1 — Integrated Platform Workflow

- Added Integrated Workflow tab.
- Added module map for Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, and Decision Studio.
- Added Decision Packet template and REST/API endpoints.
- Added admin Integrated Workflow page.
- Updated public version labels to v1.1.1.

# Changelog

## 1.0.2
- Pinned Render Python runtime to 3.12.11 at both repository root and backend root.
- Added Gemini environment variable aliases: GEMINI_API_KEY, GOOGLE_API_KEY, and GEMINI_MODEL.
- Added automatic Gemini provider detection when a Gemini key is present.
- Updated the default Gemini model to gemini-2.5-flash and kept deterministic fallback behavior.

## 1.0.1
- Added AI Decision Briefing Layer with backend-routed Gemini/OpenAI provider support.
- Added deterministic fallback briefs when provider credentials or backend are unavailable.
- Added assumption critique, risk interpretation, scenario interpretation, stakeholder summary, governance readiness, and caveats.
- Added WordPress AI Brief tab, backend status route, and AI Briefing admin page.
- Fixed duplicate Audit tab from v1.0.0.

## 1.0.0
- Renamed and upgraded the earlier sustainability platform prototype into Sustainable Catalyst Decision Studio.
- Added modular shortcodes, admin dashboards, validation dashboard, export center, report templates, and backend-ready REST routes.
