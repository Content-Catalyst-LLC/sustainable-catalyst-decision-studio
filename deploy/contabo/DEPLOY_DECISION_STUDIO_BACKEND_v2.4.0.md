# Deploy Decision Studio Backend v2.4.0

Production target:

- root: `/opt/sustainable-catalyst/decision-studio`
- container: `sc-decision-studio`
- host port: `127.0.0.1:8089`
- Docker network: `sc-internal`
- public API: `https://decision-studio-api.sustainablecatalyst.com`
- image: `sustainable-catalyst-decision-studio:2.4.0`
- build fingerprint: `scds-v2.4.0-uncertainty-sensitivity-confidence`
- source commit: `release-v2.4.0`

The guarded upgrader backs up the live runtime, preserves environment files, deploys the backend, rebuilds/recreates the container, and verifies:

1. v2.4.0 health/release identity;
2. Uncertainty Register 1.0;
3. deterministic sensitivity analysis over the Tradeoff Matrix;
4. bounded Confidence Assessment 1.0;
5. attachment to the Unified Decision Object;
6. preserved Energy Runtime Consumer v2.3.0;
7. public Caddy health.

From macOS, run `deploy_decision_studio_v2_4_0_from_macos.sh` after GitHub and WordPress are aligned.
