# AI Decision Briefing Layer

Decision Studio v1.0.1 adds a backend-routed AI briefing layer for cautious decision-support drafting. The deterministic four-pillar model remains the source of calculation. AI is used only to summarize, critique assumptions, interpret risk, describe scenarios, and surface caveats.

## Backend-only API key pattern

Do not store provider keys in WordPress. Configure provider credentials in the FastAPI deployment environment.

```text
SCDS_AI_PROVIDER=gemini
SCDS_GEMINI_API_KEY=<set-in-render>
SCDS_GEMINI_MODEL=<your-model>

# or
SCDS_AI_PROVIDER=openai
SCDS_OPENAI_API_KEY=<set-in-render>
SCDS_OPENAI_MODEL=<your-model>
```

## Endpoints

```text
GET /ai/status
POST /brief
POST /report
```

## WordPress routes

```text
GET /wp-json/scds/v1/backend-status
POST /wp-json/scds/v1/ai-brief
```

## Boundary

AI output is a drafting and interpretation aid. It is not legal, financial, engineering, medical, ESG/SDG assurance, tax, compliance, investment, or safety-critical advice.
