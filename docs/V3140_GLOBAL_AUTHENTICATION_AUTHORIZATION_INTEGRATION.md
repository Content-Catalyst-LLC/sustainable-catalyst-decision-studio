# v3.14.0 — Global Authentication & Authorization Integration

Decision Studio becomes a relying party of the Sustainable Catalyst global authentication layer. User bearer identity is validated locally against configured issuer/audience/signature requirements and translated into a canonical authenticated principal. Authorization is then applied per Decision Studio scope and, for collaborative Decision Rooms, per persisted room membership and role.

The release deliberately does not create a second user directory. Institution identity and session identity are claims from the global authentication authority. Machine clients use explicit service credentials. Legacy API keys remain compatibility-only.

No persistence migration is required; v3.13's collaboration schema remains current at `0002_v3130_collaboration` with 26 tables.
