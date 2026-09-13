# Decision Studio backend v2.9.0 deployment

From macOS, place the backend ZIP and deploy wrapper in `~/Downloads`, then run:

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v2_9_0_from_macos.sh
./deploy_decision_studio_v2_9_0_from_macos.sh
```

The guarded VPS upgrader backs up the current runtime, preserves `.env` files, rebuilds `sc-decision-studio` on port 8089, verifies v2.9 identity, exercises recommendation candidate/challenge/human-disposition/tamper flows, and rechecks the v2.8–v2.3 preserved layers plus the public Caddy endpoint.
