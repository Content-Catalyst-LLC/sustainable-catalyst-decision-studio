# Decision Studio backend v2.2.0 — Contabo deployment

Production topology is preserved: `/opt/sustainable-catalyst/decision-studio`, container `sc-decision-studio`, loopback port `8089`, Docker network `sc-internal`, and `https://decision-studio-api.sustainablecatalyst.com`.

The guarded upgrader backs up the current service, preserves environment files and Compose topology, rebuilds only Decision Studio, verifies v2.2.0 identity, tests Evidence Bundle creation and Decision Object attachment, and checks the public Caddy endpoint when available.

## Mac upload

```bash
scp -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes \
  ~/Downloads/sustainable-catalyst-decision-studio-backend-v2.2.0.zip \
  ~/Downloads/upgrade_decision_studio_backend_v2_2_0_contabo.sh \
  catalystadmin@94.72.113.77:/tmp/
```

## VPS deploy

```bash
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes catalystadmin@94.72.113.77
chmod +x /tmp/upgrade_decision_studio_backend_v2_2_0_contabo.sh
/tmp/upgrade_decision_studio_backend_v2_2_0_contabo.sh \
  /tmp/sustainable-catalyst-decision-studio-backend-v2.2.0.zip
```
