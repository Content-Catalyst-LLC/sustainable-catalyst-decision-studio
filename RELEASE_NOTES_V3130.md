# Decision Studio v3.13.0 — Collaboration & Decision Room Python Persistence

v3.13.0 moves the canonical Collaboration & Decision Room persistence authority from the legacy WordPress representation into Python/PostgreSQL.

## New contracts

- `scds-collaborative-decision-room/2.0`
- `scds-collaboration-event/2.0`
- `scds-decision-room-python-persistence/1.0`

The legacy v1 WordPress collaboration contract remains available as a compatibility projection, but it is no longer canonical persistence.

## PostgreSQL migration

This is the first Decision Studio schema migration after the v3.3 persistence foundation. Alembic advances from `0001_v330_pg_foundation` to `0002_v3130_collaboration`.

Six authoritative collaboration tables are added:

- `decision_rooms`
- `decision_room_members`
- `decision_room_comments`
- `decision_room_change_requests`
- `decision_room_share_grants`
- `decision_room_events`

The existing `snapshots` table is reused for `snapshot_type=decision-room`, increasing the Decision Studio persistence model from 20 to 26 tables.

## Collaboration persistence

Python/PostgreSQL now persists room identity and lifecycle, participant membership and roles, human comments, human change requests, room snapshots, share grants, and hash-chained room events. One canonical room is associated with a decision. Global decision events continue to receive corresponding collaboration audit events.

Share secrets are generated once and returned only at grant creation. Decision Studio persists only the SHA-256 token hash and a non-secret hint. Plaintext share tokens are not stored.

## Human-governance boundaries

- Comments, change requests, approvals, and review dispositions remain human records.
- AI may not impersonate a room participant, approve, sign, certify, or execute a decision.
- Room participation and activity do not imply recommendation or approval.
- Event-chain integrity proves record continuity, not truth or correctness.
- Final decision authority remains human-governed.

## Compatibility

v3.13 preserves:

- v3.12 Module Interoperability & Shared Evidence
- v3.11 Module Artifact & Provenance Standard
- v3.10 Cross-Module Decision Composition
- v3.9 Unified Decision Module Registry
- all four authoritative module domains
- WordPress collaboration routes as compatibility surfaces

Legacy WordPress room import is source-preserving and does not erase the original representation.

## API

Twenty-one routes are added under `/decision-rooms`, bringing Decision Studio to 293 certified API routes across 23 route registries.

## Deployment

Because v3.13 changes the schema, the guarded Contabo deployment creates both a code backup and a compressed PostgreSQL `pg_dump` before applying Alembic. Production is not certified until revision `0002_v3130_collaboration`, all 26 tables, all six collaboration tables, room persistence smoke tests, hash-chain verification, share-token hash verification, and public Caddy checks all pass.
