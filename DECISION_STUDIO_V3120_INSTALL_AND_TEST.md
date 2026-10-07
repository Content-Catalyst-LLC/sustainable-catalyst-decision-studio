# Decision Studio v3.12.0 Install and Test

Use `APPLY_AND_PUSH_DECISION_STUDIO_V3120.sh` against a clean v3.11.0 checkout. The script uses Python 3.12, runs the complete backend test suite and release certification, validates PHP/JavaScript/shell syntax, commits and pushes `main`, creates tag `v3.12.0`, and builds release ZIPs into `~/Downloads`.

After local validation, deploy with `deploy_decision_studio_v3_12_0_from_macos.sh`. The VPS upgrader refuses an invalid baseline, verifies the existing 20-table PostgreSQL schema, performs an Alembic no-op, deploys v3.12.0, then exercises reference-only shared evidence, explicit module usage edges, contradiction visibility, and preservation of the v3.11 artifact/provenance standard.

See `V3120_MODULE_INTEROPERABILITY_SHARED_EVIDENCE_COMMANDS.txt` for copy/paste commands.
