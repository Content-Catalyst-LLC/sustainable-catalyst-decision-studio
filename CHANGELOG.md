# Changelog

## 1.12.0 — Institutional and Domain Decision Packs

- Added ten reusable institutional and domain decision methodologies.
- Added pack catalog, detail, validation, application, and Decision Packet routes.
- Added intake, evidence, review-role, and readiness diagnostics.
- Added criteria, indicator, Workbench model, governance-role, risk-question, readiness-rule, and briefing-template application.
- Added WordPress Decision Packs workspace, admin catalog, local fallback parity, database persistence, and export support.
- Advanced the additive Decision Packet schema to `scds-decision-packet/1.5` and WordPress database schema to 1.6.0.
- Preserved collaboration rooms, governance, advanced scenarios, typed platform handoffs, and legacy adapters.
- Expanded the backend suite to 87 tests.

## 1.11.0 — Collaborative Decision Rooms

- Added private, restricted, and institutional WordPress-managed Decision Rooms.
- Added owner, facilitator, editor, reviewer, client, and observer roles with explicit permissions.
- Added comments linked to Decision Packet sections, evidence records, assumptions, scenarios, and brief sections.
- Added change requests, resolution records, revision application, and implementation tracking.
- Added Decision Packet snapshots, version comparison, and changed-path reporting.
- Added SHA-256 chained collaboration events with tamper detection.
- Added private invitations with one-time tokens and stored token hashes only.
- Added approved-version locks and explicit reasoned reopening.
- Added room, membership, and event database tables plus authenticated WordPress REST routes.
- Added Contact and Engagement Platform handoffs for private advisory collaboration.
- Added collaboration to saved packets and export bundles.
- Advanced Decision Packet schema to `scds-decision-packet/1.4` without breaking earlier packet sections.
- Preserved v1.10.0 scenario analysis, v1.9.0 governance, v1.8.0 platform handoffs, and legacy adapters.

# Sustainable Catalyst Decision Studio Changelog

## v1.10.0 — Advanced Scenario and Sensitivity Studio

- Added `scds-scenario-studio/1.0` and additive Decision Packet schema `scds-decision-packet/1.3`.
- Added up to 100 custom alternatives, custom criteria, weighted and unweighted rankings, and dominance review.
- Added one-way sensitivity, tornado ranking, two-variable screening, threshold and break-even analysis.
- Added deterministic uncertainty envelopes, time-horizon comparison, stakeholder distribution, reversibility, and option value.
- Added Scenario Studio WordPress controls, REST routes, deterministic PHP parity, persistence, and export bundles.
- Added explicit Workbench handoffs for probabilistic simulation, optimization, engineering models, and domain forecasting.
- Preserved v1.9.0 human governance and v1.8.0 typed platform handoffs.
- Expanded the backend suite to 68 tests.

## v1.9.0 — Decision Governance and Review Center

- Added `scds-decision-governance/1.0`, `scds-review-event/1.0`, and additive `scds-decision-packet/1.2`.
- Added ten controlled decision states and explicit transition rules.
- Added accountable owner, reviewer assignment, approval condition, exception, conflict-of-interest, and sign-off records.
- Added append-only SHA-256 review-event chains and tamper verification.
- Added approval expiration and reassessment dates.
- Added governance-aware reviewed and public export restrictions with HTTP 409 blocking.
- Added WordPress Governance tab, REST parity, `governance_json` migration, saved-packet persistence, and export integration.
- Preserved v1.8.0 typed platform handoffs, existing shortcodes, REST routes, and legacy adapters.
- Expanded the backend regression suite to 57 tests.

## v1.8.0 — Unified Evidence and Platform Handoffs

- Added typed handoff contracts for Knowledge Library, Research Librarian, Site Intelligence, Workbench, Research Lab, and Platform Core.
- Added `scds-platform-artifact/1.0`, `scds-evidence-record/1.0`, and additive `scds-decision-packet/1.1` schemas.
- Added source-product auto-detection, artifact validation, canonical SHA-256 payload verification, transformation history, and batch import for up to 100 artifacts.
- Added Decision Packet sections for evidence records, citations, quotations, research routes, evidence gaps, live observations, methodologies, technical artifacts, experiments, datasets, entities, Evidence Ledger records, and provenance links.
- Added backend and WordPress routes for platform discovery, contract discovery, validation, batch import, and platform handoff templates.
- Added WordPress browser fallback parity and a Knowledge Library sample artifact.
- Preserved all existing shortcodes, REST routes, and legacy Catalyst artifact adapters.
- Expanded the regression suite to 46 backend tests.

## v1.7.1 — Production Reliability and Roadmap Repair

- Corrected Render root directory, startup command, health check, and pinned runtime settings.
- Added backend and WordPress release manifests, build fingerprints, source commit identity, and `/release` endpoints.
- Added WordPress/backend version-parity diagnostics and an admin diagnostics screen.
- Added automatic WordPress database migration checks on upgrade.
- Added one-megabyte request limits and per-route public rate limiting for expensive operations.
- Normalized Python package markers and pytest execution.
- Added cold-start, release identity, request-limit, and deterministic AI fallback regression tests.
- Corrected stale release labels and v1.6.0 integration metadata without changing public shortcodes or Decision Packet schemas.

## v1.7.0 — Professional Public Landing Page and Demo Refresh

- Added public landing and demo shortcode modes.
- Added backend and WordPress public template endpoints.
- Added admin Public Landing & Demo guidance.
- Added launch-ready workflow copy and scoped public-page CSS.
- Updated tests, docs, terminal commands, and integration manifest.

## v1.6.0 — Saved Decision Packets and Export Center

- Added Saved Decision Packet structure and browser-local save/load/delete workflow.
- Added Export Center tab in the public Decision Studio UI.
- Added export bundle generation with Decision Packet JSON, integrated brief Markdown/HTML/JSON, audit JSON, readiness JSON, scenario JSON, and Workbench handoff JSON.
- Added backend endpoints for storage templates and export bundles.
- Added WordPress REST endpoints for saved packet records and export bundles.
- Added admin Export Center upgrade.
- Added backend tests for export center and saved packet generation.

## v1.5.0 — Scenario Comparison and Workbench Handoff

- Added scenario comparison matrix with option ranking, baseline deltas, sensitivity flags, and tradeoff notes.
- Added Workbench handoff router with recommended tool IDs, shortcodes, reasons, priorities, and payload summaries.
- Added Scenario Comparison and Workbench Handoff UI controls.
- Added backend endpoints for scenario comparison and Workbench handoff generation.
- Integrated scenario comparison and Workbench handoff details into the integrated decision brief.
- Added tests for scenario comparison, handoff generation, and integrated brief enrichment.


## v1.4.0 — Brief Readiness and Review Status

- Added Brief Readiness tab and review status workflow.
- Added backend endpoints for readiness and review status.
- Added section-level scoring, unresolved issue flags, required review states, and export gates.
- Integrated readiness metadata into Decision Packet analysis and integrated briefs.


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

## v1.1.0 — Integrated Platform Workflow

- Added Integrated Workflow tab.
- Added module map for Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, Grit, and Decision Studio.
- Added Decision Packet template and REST/API endpoints.
- Added admin Integrated Workflow page.
- Updated public version labels to v1.1.0.

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
