# Decision Studio v3.7.0 Install & Test

Run `APPLY_AND_PUSH_DECISION_STUDIO_V370.sh` from the extracted v3.7 repository bundle and point it at `~/Downloads/sustainable-catalyst-decision-studio`.

The script requires the current checkout to be v3.6.0, creates an isolated Python 3.12 virtual environment under `/tmp`, runs the complete backend suite and release certification, pushes/tags v3.7.0, and builds distributables.

After local PASS, run `deploy_decision_studio_v3_7_0_from_macos.sh` from `~/Downloads`.
