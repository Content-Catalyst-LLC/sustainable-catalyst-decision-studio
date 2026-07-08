# Install

1. Upload `sustainable-catalyst-decision-studio-v1.0.0.zip` in WordPress → Plugins → Add Plugin → Upload Plugin.
2. Activate the plugin.
3. Add `[sc_decision_studio mode="full"]` to a page.
4. Optional: configure backend URL in SC Decision Studio → Methodology Settings.



## Render deployment notes

This backend is pinned to Python 3.12.11 for Render compatibility. The repository includes `.python-version` files at both the repository root and `backend/.python-version`. If Render is still selecting Python 3.14, also set this Render environment variable:

```text
PYTHON_VERSION=3.12.11
```

## Optional AI briefing backend configuration

Configure provider keys only in the backend environment, such as Render environment variables.

```text
SCDS_AI_PROVIDER=gemini
SCDS_GEMINI_API_KEY=<set-in-render>
SCDS_GEMINI_MODEL=gemini-2.5-flash

# accepted aliases
GEMINI_API_KEY=<set-in-render>
GOOGLE_API_KEY=<set-in-render>
GEMINI_MODEL=gemini-2.5-flash

# or
SCDS_AI_PROVIDER=openai
SCDS_OPENAI_API_KEY=<set-in-render>
SCDS_OPENAI_MODEL=<your-model>
```

Then in WordPress: SC Decision Studio → Methodology Settings → set Backend URL, enable Backend, and enable AI Decision Briefing.
