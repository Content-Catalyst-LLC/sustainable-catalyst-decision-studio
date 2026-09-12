# Decision Studio v2.5.0 — Contabo Deployment

Release: **Scenario Comparison & Stress Testing**

Production topology remains unchanged:

- runtime root: `/opt/sustainable-catalyst/decision-studio`
- container: `sc-decision-studio`
- image: `sustainable-catalyst-decision-studio:2.5.0`
- bind: `127.0.0.1:8089`
- Docker network: `sc-internal`
- public API: `https://decision-studio-api.sustainablecatalyst.com`

The guarded upgrader backs up the current runtime before replacing backend files. It verifies the v2.5.0 release identity, Scenario Set / Scenario Comparison / Stress Test Suite schemas, human-control boundaries, the preserved v2.4 uncertainty layer, and the preserved Energy Runtime Consumer v2.3.0.

The production smoke test builds a real tradeoff matrix, evaluates baseline/downside/stress scenarios, verifies score ranges and ordering changes, executes explicit stress gates, attaches the artifacts to a Unified Decision Object, verifies the Energy runtime handoff, and checks the public Caddy endpoint.

Rollback source is the timestamped backup printed by the upgrader.
