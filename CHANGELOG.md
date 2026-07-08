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
