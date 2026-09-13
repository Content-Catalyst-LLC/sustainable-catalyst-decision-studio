# Decision Studio v2.6.0 — Lab + Workbench Native Handoffs

## Purpose

Decision Studio v2.6.0 establishes a typed exchange boundary between Decision Studio, Research Lab, and Workbench. The release lets Decision Studio receive analytical artifacts, request additional analysis/computation, attach returned artifacts to the Unified Decision Object, and preserve source lineage without absorbing execution responsibilities from either source product.

## Product boundaries

- **Research Lab owns experimentation and analysis.** Experiments, study results, causal analyses, model outputs, validation state, assumptions, uncertainty, and provenance remain Lab-owned artifacts.
- **Workbench owns computation.** Equations, units, parameter sets, calculation traces, simulations, graphs, engineering notes, and reports remain Workbench-owned artifacts.
- **Decision Studio owns comparison and choice.** It can request, receive, link, inspect, and reason over Lab/Workbench artifacts, but it does not execute their work or silently reinterpret it.

Receipt means the handoff contract and fingerprint were accepted. It does **not** mean the underlying analysis is validated, approved, correct, or recommended.

## New contracts

### `scds-analysis-handoff/1.0`
Carries a Research Lab artifact into Decision Studio while retaining the exact source payload, source product/version, artifact type/schema, review state, assumptions, uncertainty, provenance, links, optional originating request, and deterministic SHA-256 fingerprint.

### `scds-computation-handoff/1.0`
Carries a Workbench computation artifact with the same lineage guarantees. Formulae, units, inputs, outputs, graphs/reports, and computational provenance stay source-owned.

### `scds-handoff-receipt/1.0`
Records bounded acceptance or rejection of a handoff. The receipt contains validation errors/warnings, artifact fingerprint, request lineage, and explicit execution/persistence boundaries.

### `scds-analysis-request/1.0`
Represents Decision Studio asking Research Lab or Workbench for additional work. It records the question, what the result is needed for, requested artifact types, decision context, assumptions, uncertainty, provenance, target product, return contract, and request fingerprint. `performed_by_decision_studio` is always false.

## New FastAPI and WordPress-parity routes

- `GET /native-handoffs/contracts`
- `GET /native-handoffs/template`
- `POST /native-handoffs/receive`
- `POST /native-handoffs/request`
- `POST /native-handoffs/return`
- `POST /decision-object/native-handoff`
- `POST /decision-packet/native-handoff`

WordPress exposes the same actions under `/wp-json/scds/v1` and adds a **Lab + Workbench Handoffs** workspace to the existing Decision Studio interface.

## Lineage and tamper detection

The source artifact is preserved under `artifact.payload`. Its fingerprint is SHA-256 over canonical JSON. A handoff is rejected if the payload no longer matches its recorded fingerprint. Analysis requests receive their own deterministic fingerprints, and returned artifacts can retain the originating `request_id`.

## Unified Decision Object behavior

Accepted Lab handoffs can be attached to `analysis_handoffs`; Workbench handoffs can be attached to `computation_handoffs`; receipts remain separately visible; source-product model links preserve artifact type/schema/fingerprint and original payload; request records remain explicit. Decision Packet projection remains additive and retains Decision Packet schema `scds-decision-packet/2.0`.

## Preserved release lines

v2.6.0 preserves:

- v2.5.0 Scenario Comparison & Stress Testing;
- v2.4.0 Uncertainty, Sensitivity & Confidence;
- v2.3.1 Criteria, Alternatives & Tradeoff Matrix;
- v2.3.0 Energy Systems Runtime Consumer;
- v2.2.0 Evidence & Source Bundles;
- v2.1.0 Unified Decision Object & Platform Context;
- Decision Packet `scds-decision-packet/2.0`.

## Human-control boundaries

- no automatic winner selection;
- no automatic recommendation;
- handoff receipt does not imply validation;
- Decision Studio does not execute Lab experiments;
- Decision Studio does not execute Workbench computation;
- source artifacts are not silently rewritten;
- source review state, assumptions, uncertainty, and provenance remain visible.

## Next build

**v2.7.0 — Site Intelligence Context Integration** should consume the same typed exchange pattern for real-world geographic/environmental/context artifacts rather than introducing an unrelated integration model.
