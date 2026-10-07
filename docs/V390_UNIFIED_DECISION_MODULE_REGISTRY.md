# v3.9.0 Unified Decision Module Registry

The v3.9 registry is the canonical discovery and readiness control plane for the four first-class Decision Studio modules. It is governed by the Decision Kernel and aggregates existing authoritative domain contracts rather than replacing their ownership.

The registry exposes module identity, schemas, capabilities, providers, storage/compute authority, security scopes, compatibility, and governance boundaries. It also provides capability/provider indexes and a live readiness view tied to PostgreSQL health.

Legacy `/decision-modules` endpoints remain available and no PostgreSQL schema migration occurs in this release.
