# Decision Studio v2.9.0 — Recommendations, Review & Challenge Layer

Decision Studio v2.9.0 adds a governed recommendation-review layer above the Decision Graph. A recommendation candidate records a human-selected alternative and its explicit support, counterarguments, conditions, and structural dependency context. It is not an automatically selected winner.

## Contracts

- `scds-recommendation-candidate/1.0`
- `scds-recommendation-challenge/1.0`
- `scds-recommendation-review/1.0`

## Review sequence

`selected alternative → recommendation candidate → challenges → review evaluation → human disposition → human decision`

Open challenges remain visible. An accepting disposition with open challenges requires an explicit human override. A disposition records review judgment only: it does not execute a decision, authorize external action, infer institutional approval, or overwrite the legacy recommendation field automatically.

The v2.8 dependency graph remains the structural basis for support/counterargument links and review context. Graph reachability and node degree remain non-causal and non-normative.
