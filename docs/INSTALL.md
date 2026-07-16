# Install

## WordPress plugin

1. Upload `sustainable-catalyst-decision-studio-plugin-v1.7.1.zip` in WordPress → Plugins → Add Plugin → Upload Plugin.
2. Activate or replace the existing Decision Studio plugin.
3. Existing shortcodes and saved Decision Packet fields remain compatible.
4. Open **SC Decision Studio → Release Diagnostics** to confirm the plugin version, database migration state, backend health, and version parity.
5. Add `[sc_decision_studio mode="full"]` to a page when creating a new workspace.

Activation and upgrades run the idempotent table migration routine and store the installed plugin and database versions.

## Render deployment

Use the repository `backend/render.yaml` blueprint. The service contract is:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Python: 3.12.11
```

The earlier root-level service configuration could install dependencies successfully but then fail to import `app.main`. v1.7.1 corrects the root directory so `app/main.py` is importable at startup.

Recommended reliability variables:

```text
PYTHON_VERSION=3.12.11
SCDS_BUILD_FINGERPRINT=scds-v1.7.1-53b729b
SCDS_SOURCE_COMMIT=53b729b6940bc6455cf7815c58951bce4a36fff7
SCDS_MAX_REQUEST_BYTES=1048576
SCDS_PUBLIC_RATE_LIMIT=60
SCDS_RATE_WINDOW_SECONDS=60
```

Set `SCDS_API_KEY` when WordPress should authenticate as a trusted backend caller and bypass the public backend rate bucket. Enter the same value in **SC Decision Studio → Methodology Settings → Backend API key**.

## Optional AI briefing backend

Configure provider keys only in the backend environment.

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

Then configure the backend URL and enable Backend and AI Decision Briefing in WordPress.

## Validation

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest
cd ..
python scripts/test_release.py
php -l wordpress-plugin/sustainable-catalyst-decision-studio/sustainable-catalyst-decision-studio.php
```
