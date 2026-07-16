# Decision Studio v1.9.0 — Decision Governance and Review Center

## Purpose

v1.9.0 adds a formal human-governance layer to the typed Decision Packet introduced in v1.8.0. It does not replace evidence readiness or professional review. It records who owns the decision, who reviewed it, what conditions remain, what exceptions or conflicts exist, who signed off, and whether a reviewed or public export is permitted.

## Schemas

- `scds-decision-packet/1.2`
- `scds-decision-governance/1.0`
- `scds-review-event/1.0`

The packet change is additive. v1.8.0 typed artifacts and all legacy adapters remain supported.

## Decision lifecycle

`draft → evidence_gathering → analysis → review → approved → implemented → retired`

Controlled alternate states include `revision_required`, `rejected`, and `deferred`. The transition catalog prevents invalid jumps such as `draft → implemented`.

## Approval controls

Approval is blocked until the packet has:

- A named accountable decision owner
- At least one completed human reviewer assignment
- All required approval conditions satisfied or formally waived
- No unresolved critical or high-severity exception
- No declared conflict without mitigation, resolution, or recusal
- A decision-owner sign-off
- An independent governance reviewer, independent reviewer, or review-chair sign-off

AI cannot create or satisfy these controls.

## Review history

Every authoritative transition creates an append-only event with:

- Actor and actor role
- Previous and requested states
- Reason and transition details
- Timestamp
- Previous event hash
- Canonical SHA-256 event hash

`POST /governance/history/verify` checks the full chain and identifies altered events or broken links.

## Export restrictions

- Internal draft bundles remain available unless the decision is retired.
- Reviewed exports require `approved` or `implemented` state and a clear governance gate.
- Public exports require the reviewed-export conditions and no unresolved confidential exception.
- Professional reliance is always false; Decision Studio cannot certify or provide regulated sign-off.

## API routes

```text
GET  /governance/states
GET  /governance/template
POST /governance/evaluate
POST /governance/transition
POST /decision-packet/governance
POST /governance/history/verify
```

The existing export routes accept `exportAudience` values `internal`, `reviewed`, or `public`. A blocked reviewed or public request returns HTTP 409.

## WordPress

The Governance tab provides fields for lifecycle state, owner, review actor, expiration and reassessment dates, reviewers, conditions, exceptions, conflicts, and sign-offs. WordPress stores governance in `governance_json` and preserves it in saved packets and export bundles.

Authoritative WordPress state transitions require a user with `edit_posts`. Public or disconnected browsers may preview governance evaluation, but browser-fallback history is explicitly marked as unverified.
