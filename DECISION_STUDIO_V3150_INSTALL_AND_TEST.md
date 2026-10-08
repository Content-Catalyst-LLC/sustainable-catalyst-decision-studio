# Decision Studio v3.15.0 install and test

## Local apply

```bash
cd ~/Downloads
rm -rf scds-v3.15.0-event-ledger
unzip -q sustainable-catalyst-decision-studio-v3.15.0-repository.zip -d scds-v3.15.0-event-ledger
cd scds-v3.15.0-event-ledger/sustainable-catalyst-decision-studio
chmod +x APPLY_AND_PUSH_DECISION_STUDIO_V3150.sh
./APPLY_AND_PUSH_DECISION_STUDIO_V3150.sh "$HOME/Downloads/sustainable-catalyst-decision-studio"
```

## Production deploy

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v3_15_0_from_macos.sh upgrade_decision_studio_backend_v3_15_0_contabo.sh
./deploy_decision_studio_v3_15_0_from_macos.sh
```

Target production state: version `3.15.0`, Alembic `0003_v3150_event_ledger`, 27 tables, `decision_audit_events` append-only, ledger verification healthy, and v3.14 authentication preserved.
