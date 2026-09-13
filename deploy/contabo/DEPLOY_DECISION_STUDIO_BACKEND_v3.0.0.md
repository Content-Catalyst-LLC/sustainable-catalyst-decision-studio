# Deploy Decision Studio Backend v3.0.0

From macOS after GitHub and WordPress are updated:

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v3_0_0_from_macos.sh
./deploy_decision_studio_v3_0_0_from_macos.sh
```

Expected production identity:
- version `3.0.0`
- fingerprint `scds-v3.0.0-connected-decision-intelligence`
- source `release-v3.0.0`
- container `sc-decision-studio`
- port `127.0.0.1:8089`

The guarded upgrader backs up the existing runtime, preserves env files, deploys the new backend, exercises the eight-stage lifecycle, tamper detection, packet attachment, all preserved v2.9→v2.3 layers, and public Caddy health.
