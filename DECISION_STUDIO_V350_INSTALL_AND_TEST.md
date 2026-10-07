# Decision Studio v3.5.0 Install and Test

Use `APPLY_AND_PUSH_DECISION_STUDIO_V350.sh` from the extracted v3.5.0 repository bundle to overlay the release onto an existing clean v3.4.0 Git checkout. The script creates a temporary Python 3.12 validation environment outside the repository, runs the complete backend suite and release certification, commits/pushes/tags v3.5.0, and builds distributables.

Then run `deploy_decision_studio_v3_5_0_from_macos.sh` from `~/Downloads` to perform the guarded Contabo deployment and Canvas production smoke test.
