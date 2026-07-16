# Sustainable Catalyst Decision Studio v1.11.0

**Collaborative Decision Rooms**

Decision Studio is the Sustainable Catalyst platform's governed decision orchestration layer. v1.11.0 adds private, WordPress-managed collaboration rooms around the Decision Packet so owners, facilitators, editors, reviewers, clients, and observers can work through comments, change requests, revisions, snapshots, version comparisons, approvals, and implementation records without weakening the governance controls introduced in v1.9.0.

## v1.11.0 highlights

- Private, restricted, and institutional Decision Rooms
- Role-based permissions for owners, facilitators, editors, reviewers, clients, and observers
- Section-linked comments and resolution records
- Change requests with implementation tracking
- Decision Packet snapshots and structured version comparison
- Tamper-evident collaboration activity history using SHA-256 hash chaining
- Private invitations with one-time tokens; only token hashes are retained
- Approved-version locking and reasoned reopening
- WordPress as the canonical room and membership store
- Contact and Engagement Platform handoffs for private advisory workspaces
- Decision Packet `scds-decision-packet/1.4`
- Collaboration contracts `scds-collaborative-decision-room/1.0` and `scds-collaboration-event/1.0`

## Primary collaboration endpoints

- `GET /collaboration/roles`
- `GET /collaboration/template`
- `POST /collaboration/room`
- `POST /collaboration/action`
- `POST /collaboration/comment`
- `POST /collaboration/change-request`
- `POST /collaboration/snapshot`
- `POST /collaboration/share`
- `POST /collaboration/contact-handoff`
- `POST /decision-packet/collaboration`

WordPress adds authenticated room routes under `/wp-json/scds/v1/rooms` and a dedicated shortcode mode:

```text
[sc_decision_studio mode="room" title="Collaborative Decision Room"]
```

## Preserved platform layers

v1.11.0 is additive. It preserves:

- v1.10.0 Advanced Scenario and Sensitivity Studio
- v1.9.0 Decision Governance and Review Center
- v1.8.0 typed platform handoffs
- Saved Decision Packets, export bundles, audit/provenance, readiness gates, and integrated briefs
- Existing shortcodes, REST routes, and legacy Catalyst adapters

Collaboration never substitutes for approval. Governance state, human sign-offs, export restrictions, and professional-review boundaries remain authoritative.

## v1.8.0 — Unified Evidence and Platform Handoffs

Decision Studio is now the governance and synthesis layer for the current Sustainable Catalyst platform. It accepts provenance-preserving typed artifacts from Knowledge Library, Research Librarian, Site Intelligence, Workbench, Research Lab, and Platform Core through `scds-platform-artifact/1.0`, merges them into `scds-decision-packet/1.1`, verifies canonical payload hashes, and retains the earlier Catalyst adapters as a compatibility layer.

Key additions:

- Six current product contracts and auto-detection rules
- Unified evidence, citation, research-route, live-indicator, calculation, experiment, entity, and provenance sections
- Individual validation/import plus batch import for up to 100 artifacts
- Integrity hashes and transformation history
- WordPress local fallback parity when the FastAPI backend is unavailable
- New platform, contract, validation, batch, and handoff-template endpoints

See `docs/V180_UNIFIED_EVIDENCE_PLATFORM_HANDOFFS.md` and `docs/ROADMAP.md`.

## v1.7.1 — Production Reliability and Roadmap Repair

This compatibility-preserving patch repairs Render deployment, adds build identity and version-parity diagnostics, runs WordPress database migrations automatically, limits oversized and abusive public requests, normalizes backend tests, and preserves existing shortcodes and Decision Packet schemas.

See `docs/V171_PRODUCTION_RELIABILITY_ROADMAP_REPAIR.md` and `docs/ROADMAP.md`.

## v1.7.0 — Professional Public Landing Page and Demo Refresh

Adds landing/demo shortcode modes, public product-page templates, admin launch guidance, and cleaner public positioning for the integrated Decision Packet workflow.

## v1.6.0 — Saved Decision Packets and Export Center

- Added saved Decision Packet workflow for preserving current packet state.
- Added Export Center tab with JSON, Markdown, HTML, audit, readiness, scenario, and Workbench handoff exports.
- Added browser-local save/load/delete support for public-facing workflows.
- Added backend endpoints `/export-center/template`, `/export-center/bundle`, and `/decision-packet/export-bundle`.
- Added WordPress REST endpoints for packet storage templates, saved packet records, and export bundles.
- Added admin Export Center upgrade for saved Decision Packets.


## Positioning

Workbench is the broad analytical calculator and equation layer. Decision Studio is the applied decision workflow layer.

- Workbench asks: what calculator, model, equation, or method should I use?
- Decision Studio asks: should this project, policy, procurement choice, retrofit, or sustainability strategy move forward?

## WordPress shortcodes

```text
[sc_decision_studio mode="full"]
[sc_decision_studio mode="project-intake"]
[sc_decision_studio mode="scorecard"]
[sc_decision_studio mode="risk"]
[sc_decision_studio mode="scenario"]
[sc_decision_studio mode="handoff"]
[sc_decision_studio mode="report"]
[sc_decision_studio mode="drawer" title="Open Decision Studio"]
```

Legacy compatibility is included:

```text
[sustainable_catalyst_platform]
```

## Admin areas

- SC Decision Studio → Dashboard
- SC Decision Studio → Projects
- SC Decision Studio → Scenario Templates
- SC Decision Studio → Scorecard Builder
- SC Decision Studio → Report Templates
- SC Decision Studio → Validation Dashboard
- SC Decision Studio → Export Center
- SC Decision Studio → Release Diagnostics
- SC Decision Studio → Methodology Settings

## Boundary

Educational decision support only. Not legal, financial, engineering, medical, ESG/SDG assurance, tax, compliance, or investment advice.


## AI Decision Briefing Layer

v1.0.1 adds cautious AI decision briefs through the FastAPI backend. Provider keys are configured in backend environment variables, not WordPress. If AI is unavailable, the system returns a deterministic fallback brief with assumption critique, risk interpretation, scenario interpretation, stakeholder notes, governance readiness, caveats, and Workbench handoffs.

Backend endpoints:

```text
GET /ai/status
POST /brief
POST /report
```


## v1.1.0 Integrated Platform Workflow

Decision Studio includes a typed platform workflow connecting Knowledge Library, Research Librarian, Site Intelligence, Workbench, Research Lab, Platform Core, and Decision Studio. Earlier Catalyst modules remain supported through legacy adapters.


## v1.2.0 Module Artifact Adapters

Decision Studio normalizes typed artifacts from current Sustainable Catalyst products into a shared Decision Packet. The import layer preserves raw artifacts, validates contracts, verifies integrity metadata, maps product outputs into packet sections, and supports readiness analysis before brief generation. Legacy JSON exports remain compatible.

Key endpoints:

- `GET /integrations/adapters`
- `POST /integrations/import`
- `POST /decision-packet/import`
- `POST /decision-packet/analyze`

WordPress routes:

- `/wp-json/scds/v1/integrations/adapters`
- `/wp-json/scds/v1/integrations/import`
- `/wp-json/scds/v1/decision-packet/import`


## v1.3.0 Integrated Brief Generator

Decision Studio can now generate a professional integrated decision memo from the full Decision Packet, including module artifact imports, audit/provenance records, four-pillar scores, scenario comparison, finance, impact, narrative risk, recovery, and Workbench handoffs.

Endpoints:

- `POST /integrated-brief`
- `POST /decision-packet/brief`

Exports:

- Markdown
- HTML
- JSON
- Print/PDF through the browser


## v1.4.0 — Brief Readiness and Review Status

Adds section-level Decision Packet readiness scoring, review status states, unresolved issue flags, export gates, and a public Readiness tab.


## v1.5.0 Scenario Comparison and Workbench Handoff

Decision Studio now includes a normalized scenario comparison matrix and Workbench handoff router. Scenario comparison ranks options, shows deltas versus baseline, adds tradeoff notes, and identifies sensitivity flags. Workbench handoff recommendations route deeper analysis to Workbench tools such as economics forecasting, risk/resilience, Graph Studio, engineering mode, environmental QA/QC, symbolic formula review, and advanced calculators.

Key endpoints:

```text
GET /scenario-comparison/template
POST /scenario-comparison
POST /decision-packet/scenario-comparison
GET /workbench/handoffs
POST /workbench/handoff
POST /decision-packet/workbench-handoff
```
