# Decision Studio v1.15.0 — Public API, Embeds, and Institutional Integration

## Purpose

v1.15.0 makes governed Decision Packets interoperable without making private collaboration records public. It separates public-safe read surfaces from scoped institutional operations and records every exchange in a versioned contract.

## Contracts

- `scds-public-api/1.0`
- `scds-embed-descriptor/1.0`
- `scds-institutional-archive/1.0`
- `scds-webhook-event/1.0`
- `scds-cross-product-sdk/1.0`
- `scds-platform-core-gateway/1.0`
- additive Decision Packet `scds-decision-packet/1.8`

## Public-safe surfaces

A public dossier may be generated only when governance permits public export or the decision state is approved or implemented. The sanitizer removes private rooms, memberships, invitation material, API credentials, personal contacts, private/internal notes, and raw artifacts.

Readiness and scenario endpoints return script-free descriptors. Each contains a safe payload, minimal host-controlled HTML placeholder, content hash, and explicit security metadata. Decision Studio does not inject third-party scripts into the host page.

## Institutional operations

Institutional operations use `X-SCDS-API-Key` or bearer authentication. `SCDS_INSTITUTIONAL_API_KEYS` maps each key to one or more scopes:

- `packet:read`
- `packet:write`
- `archive:write`
- `gateway:write`
- `event:emit`

`SCDS_API_KEY` remains an optional all-scopes compatibility key. Bulk packet operations are capped at 100 records.

## Signing

When `SCDS_EXPORT_SIGNING_SECRET` is configured, manifests use HMAC-SHA256. Without it, the system produces an unsigned SHA-256 digest and labels the manifest accordingly. A digest proves content identity, not institutional legal attestation.

## Platform Core and events

The gateway creates a structured exchange record containing packet identity, entity and Evidence Ledger references, provenance links, and an integrity hash. It prepares a handoff; it does not claim Platform Core accepted or persisted it.

The event endpoint creates typed, hashed internal records such as `decision_packet.updated`. v1.15.0 deliberately does not make outbound webhook calls.

## WordPress

WordPress database version 1.9.0 adds `institutional_integration_json`. The API & Embeds workspace can create public-safe dossiers and embeds, institutional archive/gateway/event records for authorized users, discover SDK contracts, persist integration records, and include them in export bundles.

## Boundary

Human governance remains authoritative. APIs cannot approve decisions, and public surfaces cannot bypass export gates. Institutional archives are not assurance, certification, regulatory filing, or legal acceptance.
