# Decision Studio 2.3.0 — Energy Systems Target-Side Runtime Consumer

This release activates the target-side consumer for Sustainable Catalyst Energy Systems Intelligence v1.2.0 handoff packets.

- Accepted packet schema: `sc-energy-runtime-handoff/1.0`
- Consumer contract: `sc-energy-runtime-decision-studio-handoff/1.0`
- Intake: `POST /v1/energy-runtime/consume`
- Capability/status: `GET /v1/energy-runtime/consumer`
- Persistence: disabled
- Automatic execution: disabled
- Credential forwarding: disabled

Boundary: Handoff acceptance does not normalize unlike evidence, assign hidden weights, rank alternatives, choose a winner, or issue investment or policy recommendations.
