# Install

1. Upload `sustainable-catalyst-decision-studio-v1.0.0.zip` in WordPress → Plugins → Add Plugin → Upload Plugin.
2. Activate the plugin.
3. Add `[sc_decision_studio mode="full"]` to a page.
4. Optional: configure backend URL in SC Decision Studio → Methodology Settings.


## Optional AI briefing backend configuration

Configure provider keys only in the backend environment, such as Render environment variables.

```text
SCDS_AI_PROVIDER=gemini
SCDS_GEMINI_API_KEY=<set-in-render>
SCDS_GEMINI_MODEL=<your-model>

# or
SCDS_AI_PROVIDER=openai
SCDS_OPENAI_API_KEY=<set-in-render>
SCDS_OPENAI_MODEL=<your-model>
```

Then in WordPress: SC Decision Studio → Methodology Settings → set Backend URL, enable Backend, and enable AI Decision Briefing.
