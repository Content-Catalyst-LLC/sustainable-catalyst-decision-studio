# Decision Studio v1.11.0 — Collaborative Decision Rooms

## Purpose

Collaborative Decision Rooms place a private, role-aware collaboration layer around the governed Decision Packet. They support human discussion and revision without collapsing comments, recommendations, approval, and implementation into the same record.

## Canonical architecture

WordPress is authoritative for identity, authentication, authorization, room persistence, memberships, and activity records. FastAPI supplies deterministic contract validation and collaboration actions. A room may be evaluated through the backend, but the canonical private record remains in WordPress.

### WordPress storage

- `wp_scds_rooms`: canonical room and packet JSON, visibility, owner, state, and locked-version hash
- `wp_scds_room_members`: user or invited participant, role, status, and invitation metadata
- `wp_scds_room_events`: normalized collaboration events and integrity hashes
- `wp_scds_projects.collaboration_json`: collaboration summary retained with saved Decision Packets

## Roles and permissions

- **Owner:** manages the room and members; comments, resolves, revises, snapshots, locks, and shares.
- **Facilitator:** coordinates members, resolution, revisions, snapshots, locks, and sharing.
- **Editor:** comments, requests changes, snapshots, and applies revisions.
- **Reviewer:** comments, requests changes, resolves items, and captures snapshots.
- **Client:** comments and requests changes in a private client-facing context.
- **Observer:** read-only participation.

WordPress capabilities and room membership remain the final authorization authority.

## Collaboration records

### Comments

Comments attach to explicit target types and identifiers such as a Decision Packet section, evidence record, source, assumption, scenario, calculation, governance condition, or brief paragraph. Resolution records identify the human resolver and resolution note.

### Change requests

A change request records the target, requested revision, requester, status, resolution, and implementation state. Applying a revision creates before-and-after snapshots and a structured comparison.

### Snapshots and comparisons

Snapshots remove recursive collaboration detail, preserve the packet content, and calculate a canonical SHA-256 content hash. Comparisons report changed paths and before/after values, capped to prevent unbounded public computation.

### Activity integrity

Every room event includes a sequence, actor, role, target, details, previous hash, and event hash. The verifier detects modified, deleted, or reordered records. This provides tamper evidence; it is not a digital signature or external notarization.

### Private invitation grants

Invitation tokens are returned once at creation. Only a SHA-256 token hash and short non-secret hint are stored in the room record. Production email delivery and token redemption remain WordPress or Contact and Engagement responsibilities.

### Approved-version locking

Only Decision Packets in `approved` or `implemented` governance states can be locked. Once locked, revision actions are blocked until an authorized human reopens the version and records a reason. Collaboration never grants approval by itself.

## Contact and Engagement handoff

A room owner or facilitator can create an `sc-contact-engagement-handoff/1.0` record containing the Decision Room identifier, project context, participants, collaboration needs, privacy requirement, requested action, and notes. The handoff contains structured context; it does not expose invitation tokens.

## APIs

### FastAPI

- `GET /collaboration/roles`
- `GET /collaboration/template`
- `POST /collaboration/room`
- `POST /collaboration/action`
- `POST /collaboration/comment`
- `POST /collaboration/change-request`
- `POST /collaboration/snapshot`
- `POST /collaboration/share`
- `POST /collaboration/contact-handoff`
- `POST /decision-packet/collaboration`

### WordPress

- `GET /wp-json/scds/v1/collaboration/template`
- `POST /wp-json/scds/v1/collaboration/action`
- `POST /wp-json/scds/v1/decision-packet/collaboration`
- `GET|POST /wp-json/scds/v1/rooms`
- `GET|DELETE /wp-json/scds/v1/rooms/{id}`
- `POST /wp-json/scds/v1/rooms/{id}/action`

## Shortcode

```text
[sc_decision_studio mode="room" title="Collaborative Decision Room"]
```

Anonymous visitors receive a sign-in notice and cannot access canonical room records.

## Preserved boundaries

- Governance approval remains a separate human-controlled record.
- AI cannot approve, sign, certify, assure, or impersonate a participant.
- Scenario results remain conditional screening outputs, not forecasts or guarantees.
- Workbench remains the boundary for probabilistic simulation, optimization, engineering models, and domain forecasting.
- Decision Rooms are not a substitute for legal, financial, engineering, medical, compliance, or assurance review.
