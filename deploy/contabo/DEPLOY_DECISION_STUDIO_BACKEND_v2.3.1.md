# Deploy Decision Studio Backend v2.3.1 to Contabo

Production topology is preserved: `/opt/sustainable-catalyst/decision-studio`, container `sc-decision-studio`, loopback port `127.0.0.1:8089`, Docker network `sc-internal`, and public Caddy hostname `decision-studio-api.sustainablecatalyst.com`.

From the Mac, use `deploy_decision_studio_v2_3_1_from_macos.sh`. The VPS upgrader creates a timestamped backup, preserves backend environment files, replaces only the backend tree, rebuilds the Docker image, verifies health, builds a real Criteria/Alternatives/Tradeoff Matrix smoke object, attaches it to the Unified Decision Object, verifies the preserved v2.3.0 Energy Systems Runtime Consumer with an actual handoff receipt, and checks the public API.

Expected identity:

- version `2.3.1`
- build fingerprint `scds-v2.3.1-criteria-alternatives-tradeoff-matrix`
- source commit `release-v2.3.1`

Preserved Energy consumer component:

- consumer version `2.3.0`
- handoff schema `sc-energy-runtime-handoff/1.0`
- consumer contract `sc-energy-runtime-decision-studio-handoff/1.0`
- endpoints `GET /v1/energy-runtime/consumer` and `POST /v1/energy-runtime/consume`
