# Decision Studio v3.14.0 Install and Test

## Local source upgrade

The target Git checkout must be clean and currently on Decision Studio v3.13.0.

```bash
cd ~/Downloads
rm -rf scds-v3.14.0-global-auth
unzip -q sustainable-catalyst-decision-studio-v3.14.0-repository.zip -d scds-v3.14.0-global-auth
cd scds-v3.14.0-global-auth/sustainable-catalyst-decision-studio
chmod +x APPLY_AND_PUSH_DECISION_STUDIO_V3140.sh
./APPLY_AND_PUSH_DECISION_STUDIO_V3140.sh "$HOME/Downloads/sustainable-catalyst-decision-studio"
```

## Production backend

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v3_14_0_from_macos.sh upgrade_decision_studio_backend_v3_14_0_contabo.sh
./deploy_decision_studio_v3_14_0_from_macos.sh
```

The upgrader preserves the v3.13 schema (`0002_v3130_collaboration`, 26 tables), verifies Alembic is a no-op, provisions the global-auth JWT relying-party secret if absent, tests bearer authentication, tests downgrade resistance, verifies Decision Room membership/role authorization and actor anti-spoofing, and performs public Caddy checks.
