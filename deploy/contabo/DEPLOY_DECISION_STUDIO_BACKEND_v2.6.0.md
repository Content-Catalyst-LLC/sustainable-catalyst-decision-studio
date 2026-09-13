# Decision Studio v2.6.0 — Contabo Deployment

Release: **Lab + Workbench Native Handoffs**

Production topology remains unchanged:

- root: `/opt/sustainable-catalyst/decision-studio`
- backend: `/opt/sustainable-catalyst/decision-studio/backend`
- container: `sc-decision-studio`
- image: `sustainable-catalyst-decision-studio:2.6.0`
- bind: `127.0.0.1:8089`
- Docker network: `sc-internal`
- public API: `https://decision-studio-api.sustainablecatalyst.com`

The guarded upgrader backs up the current backend and compose file, preserves backend environment files, validates the v2.6 payload, rebuilds the Docker service, and then tests the actual native-handoff lifecycle.

Verification covers:

1. v2.6.0 internal/public identity and fingerprints;
2. all four native handoff contracts;
3. Research Lab analysis handoff with deterministic source-artifact fingerprint;
4. Workbench computation handoff;
5. Decision Studio → Workbench request and returned artifact attachment with `request_id` lineage;
6. rejection of a deliberately tampered handoff;
7. Decision Packet native-handoff projection;
8. preserved v2.5 Scenario/Stress contracts;
9. preserved Energy Systems Runtime Consumer v2.3.0 and bounded handoff acceptance.

A successful handoff receipt means the transport/contract and fingerprint checks passed. It does not validate the scientific or computational claim and does not constitute approval or recommendation.
