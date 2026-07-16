# Decision Studio v1.7.1 — Production Reliability and Roadmap Repair

Decision Studio v1.7.1 is a compatibility-preserving reliability release. It does not remove or rename public shortcodes, REST routes, Decision Packet sections, or export formats.

## Reliability changes

- Corrected the Render blueprint to use `backend` as the service root and `uvicorn app.main:app` as the startup command.
- Added `/release` and expanded `/health` with release identity, build fingerprint, source commit, uptime, cold-start readiness, and request limits.
- Added a one-megabyte request ceiling and configurable per-route public rate limiting for expensive POST operations.
- Added package markers and pytest configuration so `python -m pytest` works consistently from the backend directory.
- Added WordPress automatic migration checks using explicit database and installed-release version options.
- Added WordPress release and backend-parity diagnostics, including an admin diagnostics screen and REST payloads.
- Added release manifests for the repository, backend, and WordPress plugin.
- Corrected stale release labels and historical v1.6.0 metadata.

## Compatibility contract

- API namespace remains `scds/v1`.
- Existing shortcodes remain available.
- Decision Packet structure remains `scds-decision-packet/1.0`.
- Saved packet and export bundle formats remain structurally compatible.
- Backend unavailability still falls back to deterministic WordPress analysis and briefing behavior.

## Operational environment variables

- `SCDS_BUILD_FINGERPRINT`
- `SCDS_SOURCE_COMMIT`
- `SCDS_MAX_REQUEST_BYTES`
- `SCDS_PUBLIC_RATE_LIMIT`
- `SCDS_RATE_WINDOW_SECONDS`
- `SCDS_API_KEY` for trusted backend callers that should bypass the public rate bucket
