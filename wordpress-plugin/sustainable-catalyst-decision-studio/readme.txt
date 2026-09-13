=== Sustainable Catalyst Decision Studio ===
Contributors: content-catalyst
Tags: decision intelligence, governance, lifecycle, evidence, monitoring, collaboration
Requires at least: 6.4
Tested up to: 6.8
Requires PHP: 7.4
Stable tag: 3.0.0
License: GPLv2 or later

Uncertainty, sensitivity, and process-confidence layer for transparent robustness testing over Decision Studio tradeoff matrices, with explicit human-review boundaries.

== Description ==

Decision Studio v2.9.0 adds explicit recommendation candidates, reviewer challenges, review evaluation, and human dispositions while preserving the v2.8.0 Decision Graph, v2.7.0 Site Intelligence context, v2.6.0 Lab + Workbench native handoffs, v2.5.0 scenario/stress analysis, and earlier Decision Studio contracts.

Process confidence summarizes documentation and analysis coverage. It is not a probability that an alternative or recommendation is correct. Sensitivity results do not automatically select a winner or create a recommendation.

== Shortcodes ==

[sc_decision_studio mode="full" title="Sustainable Catalyst Decision Studio"]
[sc_decision_studio mode="uncertainty" title="Uncertainty, Sensitivity & Confidence"]
[sc_decision_studio mode="tradeoffs" title="Criteria, Alternatives & Tradeoff Matrix"]
[sc_decision_studio mode="evidence" title="Evidence & Source Bundles"]
[sc_decision_studio mode="decision-object" title="Unified Decision Object"]
[sc_decision_studio mode="connected" title="Connected Decision Intelligence Platform"]
[sc_decision_studio mode="hardening" title="Accessibility, Offline Use, and Release Hardening"]
[sc_decision_studio mode="integration" title="Public API, Embeds, and Institutional Integration"]
[sc_decision_studio mode="outcomes" title="Outcomes, Monitoring, and Reassessment"]
[sc_decision_studio mode="publication" title="Decision Briefing and Publication Studio"]
[sc_decision_studio mode="packs" title="Institutional Decision Packs"]
[sc_decision_studio mode="room" title="Collaborative Decision Room"]
[sc_decision_studio mode="export" title="Decision Studio Export Center"]
[sc_decision_studio mode="landing" title="Sustainable Catalyst Decision Studio"]

== Changelog ==

= 3.0.0 =
* Connected Decision Intelligence: eight-stage lifecycle readiness, bounded cross-product route planning, lineage visibility, and human-controlled progression.


= 2.9.0 =
* Added scds-recommendation-candidate/1.0, scds-recommendation-challenge/1.0, and scds-recommendation-review/1.0.
* Recommendation candidates require an explicit human-selected alternative; scores and graph structure do not select a winner.
* Added challenge records, open-challenge review gates, explicit human override, and governed disposition.
* Human disposition records actor and rationale but never executes a decision or implies institutional approval.
* Preserved v2.8 Decision Graph & Dependency Mapping and all prior contracts.

= 2.8.0 =
* Added Decision Dependency Graph, Dependency Diagnostics, and Change Impact Assessment contracts.
* Added explicit and structural dependency edges, orphan/unresolved/cycle diagnostics, and review-only downstream impact tracing.
* Preserved Site Intelligence context, native Lab/Workbench handoffs, Scenario/Stress, and Energy Runtime Consumer v2.3.0.
* Dependency edges do not imply causality; degree does not imply importance; change impact does not automatically invalidate or change recommendations.

= 2.7.0 =
* Added Site Intelligence context bundles, immutable signal snapshots, freshness/geography/source diagnostics, explicit scenario-context links, and bounded context receipts.
* Preserved Lab + Workbench native handoffs and earlier release contracts.

= 2.6.0 =
* Added Lab + Workbench Native Handoffs, analysis requests, deterministic fingerprints, receipts, and Decision Object lineage.
* Preserved Scenario/Stress v2.5.0 and Energy Runtime Consumer v2.3.0.

= 2.5.0 =
* Added Scenario Comparison & Stress Testing with first-class scenario sets, conditional score ranges, failure-mode diagnostics, and Decision Object/Packet attachment.
* Preserves Energy Runtime Consumer v2.3.0 and all v2.4 uncertainty/confidence contracts.
* Scenarios are not forecasts; stress-test passes do not imply approval; no automatic winner or recommendation.

= 2.4.0 =
* Added Uncertainty Register, Sensitivity Analysis, and Confidence Assessment schemas.
* Added deterministic criterion-weight and bounded-evaluation sensitivity testing.
* Added alternative score envelopes, pairwise overlap diagnostics, and ordering-change visibility.
* Added transparent process-confidence dimensions and limiting factors.
* Added Decision Object/Packet attachment and WordPress REST/UI parity.
* Preserved the Energy Runtime Consumer v2.3.0 and all v2.3.1 Tradeoff Matrix capabilities.
* Preserved no-winner, no-auto-recommendation, and no-probability-of-correctness boundaries.

= 2.3.1 =
* Added Criteria Set, Alternatives Set, Tradeoff Matrix, and Tradeoff Diagnostics schemas.
* Added normalized criteria weights while preserving input weights.
* Added direct and scale-derived scores, matrix coverage, review, missing-cell, and threshold diagnostics.
* Added weighted comparison summaries without automatic winner selection or recommendation.
* Added Tradeoff Matrix workspace, Decision Object attachment, Decision Packet projection, and REST parity.
* Preserved v2.2 Evidence & Source Bundles and all prior connected-platform capabilities.

= 2.2.0 =
* Added Source Bundle, Evidence Bundle, and Evidence Coverage schemas.
* Added deterministic SHA-256 deduplication and source-linked evidence records.
* Added citation coverage, unresolved-source, review-gap, and contradiction diagnostics.
* Added Evidence & Sources workspace, bundle merge, Decision Object attachment, and Decision Packet projection.
* Preserved v2.1.0 Decision Object, Decision Packet 2.0, and all connected-platform capabilities.

= 2.1.0 =
* Added first-class Unified Decision Object and Platform Context schemas.
* Added reversible Decision Packet promotion/projection with source-packet preservation.
* Added provenance-aware platform artifact links and completeness diagnostics.
* Added Decision Object workspace tab, shortcode mode, and REST parity.
* Preserved v2.0.1 Catalyst module handoffs and v2.0.0 Connected Platform.

= 2.0.1 =
* Added visible cards and browser-local packet handoffs for Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, and Grit.
* Added configurable routes and direct artifact-import actions.

= 2.0.0 =
* Added twelve-stage connected decision lifecycle assessment.
* Added prioritized cross-product action routing.
* Added Decision Intelligence Graph and portfolio attention index.
* Added prepared connected-exchange manifests.
* Added named-human tamper-evident lifecycle transitions.
* Added Decision Packet schema 2.0 and WordPress database version 2.1.0.
* Preserved all v1.x capabilities and compatibility surfaces.
