# Sustainable Catalyst Decision Studio v1.16.0

## Accessibility, Offline Use, and Release Hardening

Decision Studio is the governance, synthesis, publication, monitoring, accountability, and release-control layer of the Sustainable Catalyst platform. v1.16.0 adds an explicit hardening system for accessibility validation, local offline drafts, recovery snapshots, additive packet migration, large-packet and mobile testing, backup and restore drills, privacy review, and named-human release authorization.

The release advances the additive Decision Packet to `scds-decision-packet/1.9`. It preserves the v1.15.0 public API and institutional integration layer and all earlier governance, collaboration, scenario, publication, monitoring, evidence, and export capabilities.

## Hardening capabilities

- Twelve-point accessibility audit covering keyboard operation, focus visibility, landmarks, labels, live status, tables, chart alternatives, reduced motion, contrast, errors, touch targets, and zoom/reflow
- Explicit requirement for human screen-reader, keyboard-only, forced-colors, contrast, and reflow testing
- IndexedDB local draft storage with localStorage fallback
- Fifteen-second autosave and online/offline status announcements
- Sensitive-field stripping before recovery storage
- Recovery snapshots with packet and snapshot SHA-256 hashes
- Additive migration assessment from Decision Packet 1.0–1.8 to 1.9
- Large-packet and mobile performance gates
- Backup, restore, and privacy-review gates
- Human release authorization required; automatic deployment remains disabled

## Primary endpoints

- `GET /release-hardening/template`
- `POST /release-hardening/accessibility-audit`
- `POST /release-hardening/offline-manifest`
- `POST /release-hardening/recovery-snapshot`
- `POST /release-hardening/migration-assessment`
- `POST /release-hardening/readiness`
- `POST /decision-packet/release-hardening`

WordPress exposes matching routes under `/wp-json/scds/v1` and a dedicated workspace:

```text
[sc_decision_studio mode="hardening" title="Accessibility, Offline Use, and Release Hardening"]
```

## Offline boundary

Offline mode supports viewing the active packet, editing a local draft, creating a recovery snapshot, and exporting JSON. Governance transitions, room membership changes, institutional API operations, publication handoffs, and external delivery require reconnection and explicit authenticated confirmation. Queued writes are never replayed automatically.

## Accessibility boundary

Automated checks cannot establish full WCAG conformance. Assistive-technology testing, contrast review, reflow validation, restore drills, privacy review, security review, and named-human release authorization remain required.

See `docs/V1160_ACCESSIBILITY_OFFLINE_RELEASE_HARDENING.md` and `docs/ROADMAP.md`.
