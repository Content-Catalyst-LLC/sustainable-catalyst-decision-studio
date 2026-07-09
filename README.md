# Sustainable Catalyst Decision Studio v1.4.0

Sustainable Catalyst Decision Studio is an applied sustainability decision-support layer for Content Catalyst LLC / Sustainable Catalyst. It upgrades the earlier Sustainable Catalyst 1.0 prototype into a modular WordPress + FastAPI-ready platform for project intake, four-pillar scoring, scenarios, risk, reports, validation, exports, Workbench integration, and backend-routed AI decision briefing.

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


## v1.1.1 Integrated Platform Workflow

Decision Studio now includes an Integrated Workflow tab and Decision Packet structure connecting Catalyst Canvas, Catalyst Data, Catalyst Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, Catalyst Grit, and Decision Studio.


## v1.2.0 Module Artifact Adapters

Decision Studio can now normalize JSON exports from Catalyst Canvas, Catalyst Data, Catalyst Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, Catalyst Grit, and Workbench into a shared Decision Packet. The import layer preserves raw artifacts, maps data into packet sections, adds provenance entries, and supports readiness analysis before brief generation.

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
