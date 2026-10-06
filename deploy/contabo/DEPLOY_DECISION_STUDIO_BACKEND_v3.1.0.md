# Deploy Decision Studio Backend v3.1.0

From macOS after the v3.1.0 repository/plugin release is installed:

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v3_1_0_from_macos.sh
./deploy_decision_studio_v3_1_0_from_macos.sh
```

Expected production identity:

- version `3.1.0`
- fingerprint `scds-v3.1.0-backend-service-decomposition`
- source `release-v3.1.0`
- container `sc-decision-studio`
- port `127.0.0.1:8089`
- API inventory `176` routes
- database migration `false`
- WordPress authority change `false`

The guarded upgrader preserves environment files, backs up the existing runtime, verifies the decomposed backend architecture, runs the connected-decision-intelligence smoke tests, verifies preserved v2.x layers, and checks the public Caddy health endpoint.
