# Decision Studio v3.6.0 Install & Test

## Local apply

Run `APPLY_AND_PUSH_DECISION_STUDIO_V360.sh` from the extracted v3.6 repository and point it at the existing `~/Downloads/sustainable-catalyst-decision-studio` checkout.

The script requires the current checkout to be v3.5.0, creates an isolated Python 3.12 virtual environment under `/tmp`, runs the complete backend suite and release certification, pushes/tag v3.6.0, and builds distributables.

## Production deploy

Run `deploy_decision_studio_v3_6_0_from_macos.sh` from `~/Downloads`.

The VPS upgrader verifies the v3.5 Canvas baseline, current 20-table PostgreSQL schema, and current Alembic revision before deploying Finance authority. It performs an authenticated Finance write/read smoke, checks normalized database rows, verifies Workbench remains compute authority, and removes synthetic smoke data.
