# Decision Studio v2.7.0 — Contabo Deployment

Release: **Site Intelligence Context Integration**

Production topology remains unchanged:

- root: `/opt/sustainable-catalyst/decision-studio`
- backend: `/opt/sustainable-catalyst/decision-studio/backend`
- container: `sc-decision-studio`
- image: `sustainable-catalyst-decision-studio:2.7.0`
- bind: `127.0.0.1:8089`
- Docker network: `sc-internal`
- public API: `https://decision-studio-api.sustainablecatalyst.com`

The guarded upgrader backs up the current backend and compose file, preserves backend environment files, validates the v2.7 payload, rebuilds the Docker service, and tests the Site Intelligence context lifecycle.

Verification covers:

1. v2.7.0 internal/public identity and fingerprints;
2. all three Site Intelligence context contracts;
3. source identity, geography, observation/update time, freshness, methodology, limitations, provenance, and raw payload preservation;
4. explicit scenario-context linking without score mutation or scenario-likelihood inference;
5. deterministic context/signal fingerprints and rejection of tampered snapshots;
6. Unified Decision Object and Decision Packet context attachment;
7. preserved v2.6 Lab + Workbench native handoffs;
8. preserved v2.5 Scenario/Stress contracts;
9. preserved Energy Systems Runtime Consumer v2.3.0 and bounded handoff acceptance;
10. public Caddy verification.

A Site Intelligence context receipt confirms contract and fingerprint acceptance only. It does not establish causal relevance, truth, approval, scenario probability, or a recommendation. Site Intelligence remains the owner of observations and public-intelligence context; Decision Studio retains a bounded snapshot for decision analysis.
