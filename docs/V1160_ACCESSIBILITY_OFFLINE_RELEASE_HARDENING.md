# Decision Studio v1.16.0 — Accessibility, Offline Use, and Release Hardening

## Purpose

v1.16.0 prepares Decision Studio for dependable public and institutional operation. It adds explicit accessibility, offline recovery, migration, performance, backup, privacy, and release gates while preserving all v1.15.0 APIs and earlier Decision Packet capabilities.

## Contracts

- `scds-accessibility-audit/1.0`
- `scds-offline-workspace/1.0`
- `scds-release-readiness/1.0`
- `scds-recovery-snapshot/1.0`
- `scds-migration-assessment/1.0`
- Additive Decision Packet `scds-decision-packet/1.9`

## Accessibility validation

The audit covers keyboard navigation, visible focus, semantic landmarks, labels and instructions, live status announcements, accessible tables, chart alternatives, reduced motion, contrast review, error identification, touch-target sizing, and zoom/reflow. A perfect automated record is only `ready_for_human_validation`; it is not a conformance claim.

## Offline workspace

The WordPress client saves local drafts to IndexedDB with a localStorage fallback. It announces online/offline and save status through a live region. Offline work is limited to viewing, local editing, snapshots, and JSON export. Consequential writes require reconnection and manual confirmation.

## Recovery and migrations

Snapshots strip fields whose names indicate credentials, secrets, passwords, tokens, authorization, cookies, or private keys. Packet and snapshot hashes are recorded. Migrations are additive from packet schemas 1.0–1.8 to 1.9; downgrades and unknown targets are blocked.

## Release readiness

Six gates are evaluated:

1. Accessibility
2. Offline recovery
3. Performance and mobile validation
4. Migration compatibility
5. Backup and restore
6. Security and privacy

The result may be `release_candidate_ready`, `conditional`, or `blocked`. Human release authorization is always required and automatic deployment is always false.

## WordPress migration

Database version 2.0.0 adds `release_hardening_json` and `recovery_snapshot_json` to the canonical packet table. The dedicated workspace is available through:

```text
[sc_decision_studio mode="hardening" title="Accessibility, Offline Use, and Release Hardening"]
```

## Boundaries

This release does not certify WCAG conformance, security, legal compliance, restore reliability, or professional suitability. Human testing and review remain authoritative.
