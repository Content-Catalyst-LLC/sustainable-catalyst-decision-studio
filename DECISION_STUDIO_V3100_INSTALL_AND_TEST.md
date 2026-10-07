# Install and Test Decision Studio v3.10.0

Use Python 3.12. The release apply helper creates a temporary virtual environment outside the Git repository, installs `backend/requirements.txt`, runs the entire backend regression suite and `scripts/test_release.py`, checks PHP/JavaScript/shell syntax, commits, pushes, tags `v3.10.0`, and builds distributables.

Production deployment requires v3.9.0 as the live baseline and performs a real four-module composition, staleness detection, explicit refresh, and cleanup against PostgreSQL.
