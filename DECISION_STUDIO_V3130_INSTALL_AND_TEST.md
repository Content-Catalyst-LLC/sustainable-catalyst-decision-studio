# Decision Studio v3.13.0 Install and Test

## Local baseline

The target repository must be v3.12.0. Use Python 3.12.

```bash
cd ~/Downloads
rm -rf scds-v3.13.0-collaboration-persistence
unzip -q sustainable-catalyst-decision-studio-v3.13.0-repository.zip -d scds-v3.13.0-collaboration-persistence
cd scds-v3.13.0-collaboration-persistence/sustainable-catalyst-decision-studio
chmod +x APPLY_AND_PUSH_DECISION_STUDIO_V3130.sh
./APPLY_AND_PUSH_DECISION_STUDIO_V3130.sh "$HOME/Downloads/sustainable-catalyst-decision-studio"
```

The apply script runs the complete backend regression suite, release certification, PHP/JavaScript checks, and a real Alembic test migration to `0002_v3130_collaboration` with 26 tables before committing/tagging.

## Production deployment

Production must already be on healthy v3.12.0 before the first v3.13 deployment.

```bash
cd ~/Downloads
chmod +x deploy_decision_studio_v3_13_0_from_macos.sh upgrade_decision_studio_backend_v3_13_0_contabo.sh
./deploy_decision_studio_v3_13_0_from_macos.sh
```

The VPS upgrader creates both code and PostgreSQL backups, applies Alembic, checks the six collaboration tables, runs authoritative room persistence tests, verifies SHA-256-only share-token storage and the hash-chained room event ledger, preserves v3.12/v3.11/v3.10/v3.9 contracts, and checks the public API.
