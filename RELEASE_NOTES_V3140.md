# Decision Studio v3.14.0 — Global Authentication & Authorization Integration

v3.14.0 makes Sustainable Catalyst global identity the primary user-authentication path for Decision Studio while preserving service credentials and the existing `X-SCDS-API-Key` surface as a compatibility fallback.

## New authentication contract

- `scds-global-authentication-authorization/1.0`
- `scds-authenticated-principal/1.0`
- `scds-authorization-decision/1.0`
- Primary user credential: HS256 bearer token issued by the Sustainable Catalyst global authentication layer.
- User identity includes subject, institution, roles, scopes, session identity, email, and display name.
- Service-to-service authentication uses `X-SCDS-Service-Key` with explicitly configured scopes.
- Legacy `X-SCDS-API-Key` credentials remain supported for backward compatibility.
- An invalid bearer token never falls through to a simultaneously supplied legacy key.

## Decision Room authorization

Authenticated user principals must be active Decision Room members (or the persisted owner) in addition to holding the required global scope. Persisted room roles govern member management, commenting, change requests, resolution, snapshots, and sharing. Request-body actor fields are replaced with the authenticated user identity and persisted room role, preventing participant impersonation.

Institution identity is propagated into newly created rooms. A room bound to an institution rejects authenticated users from a different institution unless they carry global administrative authority.

## Persistence boundary

No database migration is introduced. v3.14.0 preserves:

- Alembic revision `0002_v3130_collaboration`
- 26 PostgreSQL tables
- v3.13 authoritative Decision Room persistence
- v3.12 shared evidence
- v3.11 artifact/provenance
- v3.10 cross-module composition
- v3.9 unified module registry

Decision Studio validates identity and enforces resource authorization, but it does not become the credential issuer or a duplicate user directory. Final decision authority remains human-governed.
