# v3.10.0 — Cross-Module Decision Composition

## Purpose

Cross-module composition lets one Decision Kernel identity be reviewed through multiple authoritative module lenses without merging module authority. A composition records selected module snapshots, ownership-preserving shared Kernel projections, explicit cross-module links, module fingerprints, diagnostics, and provenance.

## Composition semantics

The composition layer is a coordination/control object, not a new analytical authority. It can expose a Finance Workbench receipt next to a Global Impact indicator or a Narrative Risk claim next to a Canvas alternative, but it does not decide how those objects should be weighted, whether a claim is true, or whether one relationship is causal.

## Persistence

Compositions use `decision_objects` with object type `cross-module-decision-composition`. No new table or Alembic revision is introduced in v3.10.0.

## Staleness

Each selected domain state is deterministically fingerprinted. If a domain changes after composition, the diagnostics endpoint reports the stale module. `POST .../refresh` explicitly rebuilds the composition and advances its revision.

## Security

Authenticated reads require `composition:read`; writes and refreshes require `composition:write`. The repository key and repository read/write scopes remain authorized as compatibility/super-scopes.
