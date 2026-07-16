# Sustainable Catalyst Decision Studio v1.15.0

## Public API, Embeds, and Institutional Integration

Decision Studio is the governance, synthesis, publication, monitoring, and accountability layer of the Sustainable Catalyst platform. v1.15.0 adds controlled interoperability for public dossiers, script-free embeds, institutional packet exchange, signed archives, Platform Core gateway records, internal events, and stable cross-product contracts.

Public surfaces expose only governance-permitted, public-safe records. Institutional write and archive operations require scoped API keys. The release does not expose private Decision Rooms, invitation records, personal contact details, secrets, or internal notes.

## Integration capabilities

- Versioned `scds-decision-packet/1.8` packet exchange
- Public-safe dossier generation gated by approved or implemented governance states
- Script-free readiness and scenario embed descriptors
- Scoped API keys for packet read/write, archive, gateway, and event operations
- Bulk packet import and export, capped at 100 packets per request
- Signed or digest-only export manifests
- Institutional archive packages
- Platform Core gateway records
- Internal webhook-style event records without automatic external delivery
- Stable SDK contract discovery
- Additive WordPress and backend parity

## Primary endpoints

- `GET /api/v1/capabilities`
- `GET /api/v1/sdk/contracts`
- `POST /api/v1/public-dossier`
- `POST /api/v1/embeds/readiness`
- `POST /api/v1/embeds/scenario`
- `POST /api/v1/packets/export`
- `POST /api/v1/packets/import`
- `POST /api/v1/archive`
- `POST /api/v1/platform-core/gateway`
- `POST /api/v1/events`
- `POST /decision-packet/institutional-integration`

WordPress exposes matching routes under `/wp-json/scds/v1` and a dedicated workspace:

```text
[sc_decision_studio mode="integration" title="Public API, Embeds, and Institutional Integration"]
```

## Configuration

- `SCDS_API_KEY`: optional all-scopes institutional key.
- `SCDS_INSTITUTIONAL_API_KEYS`: JSON object mapping keys to allowed scopes.
- `SCDS_EXPORT_SIGNING_SECRET`: optional HMAC-SHA256 signing secret. When absent, manifests retain a SHA-256 digest and are marked unsigned.

## Preserved platform layers

v1.15.0 preserves outcomes monitoring, publication, institutional Decision Packs, private Decision Rooms, advanced scenarios, human governance, typed platform evidence, saved packets, governed exports, audit/provenance, and legacy adapters.

## Boundary

Public APIs and embeds are decision-support publication surfaces, not certification, assurance, professional advice, or automatic approval. Internal event records are structured handoffs; this release does not deliver external webhooks automatically.

See `docs/V1150_PUBLIC_API_EMBEDS_INSTITUTIONAL_INTEGRATION.md` and `docs/ROADMAP.md`.
