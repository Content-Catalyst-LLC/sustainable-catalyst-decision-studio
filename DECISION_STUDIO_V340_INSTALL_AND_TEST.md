# Install and test Decision Studio v3.4.0

Use the bundled `APPLY_AND_PUSH_DECISION_STUDIO_V340.sh` from the extracted repository package. It overlays the certified v3.4 source onto the existing v3.3.1 Git checkout, creates a temporary Python 3.12 validation environment outside the repository, runs the complete backend and release-integrity suites, commits/pushes/tag v3.4.0, and builds the distributables into `~/Downloads`.

After local certification, deploy with `deploy_decision_studio_v3_4_0_from_macos.sh`. The Contabo upgrader verifies the existing PostgreSQL revision/table inventory before enabling repository write authority.
