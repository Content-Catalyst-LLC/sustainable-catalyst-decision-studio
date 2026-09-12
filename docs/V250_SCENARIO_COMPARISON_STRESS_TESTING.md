# Decision Studio v2.5.0 — Scenario Comparison & Stress Testing

## Purpose

Make conditional decision robustness visible after v2.4.0 uncertainty/sensitivity analysis. v2.5.0 applies named scenario conditions to the same Tradeoff Matrix, compares alternative performance across those conditions, and runs explicit stress gates.

## First-class contracts

- `scds-scenario-set/1.0`
- `scds-scenario-comparison/1.0`
- `scds-stress-test-suite/1.0`

## Scenario model

A scenario may change criterion weights and/or evaluation inputs while retaining the same decision, alternatives, and criteria identities. Kinds include baseline, expected, upside, downside, stress, and custom. Scenario conditions are not assigned probabilities by Decision Studio.

## Comparison diagnostics

- alternative score range across scenarios
- maximum tested score swing
- ordering changes versus baseline
- threshold breaches by scenario
- incomplete matrices by scenario

The comparison intentionally contains no `recommended_option` or `winner` field.

## Stress testing

Stress scenarios may be evaluated against explicit gates for maximum allowed score drop, maximum threshold violations, matrix completeness, and minimum process confidence. Failure codes are retained as inspectable diagnostics. Passing a stress test is not approval, certification, or recommendation.

## Preservation

v2.5.0 preserves v2.4.0 uncertainty/confidence, v2.3.1 Tradeoff Matrix, v2.2 Evidence & Source Bundles, v2.1 Unified Decision Object, Decision Packet 2.0, and Energy Systems Runtime Consumer v2.3.0.
