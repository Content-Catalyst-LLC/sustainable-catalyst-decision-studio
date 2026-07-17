# v2.0.0 — Connected Decision Intelligence Platform

## Purpose

v2.0.0 turns Decision Studio from a collection of decision-support workspaces into one connected orchestration layer. It evaluates where a Decision Packet stands, what is missing, which Sustainable Catalyst product should address each gap, and what human-controlled action comes next.

## Lifecycle

1. Frame
2. Research
3. Gather Evidence
4. Model
5. Compare
6. Challenge Assumptions
7. Review
8. Approve
9. Publish
10. Implement
11. Monitor
12. Reassess

Each stage reports status, record count, missing requirements, product routes, and the relationship to prior stages.

## Action routing

Blockers are transformed into a prioritized queue. Critical and high-severity items appear first. Actions route to products according to their role, including Research Librarian for research paths, Knowledge Library for durable evidence, Site Intelligence for observations, Workbench and Research Lab for technical analysis, Decision Studio for governance, and Platform Core for durable exchange and registry records.

## Decision Intelligence Graph

The graph connects the decision to evidence, indicators, models, experiments, alternatives, risks, publications, reassessments, and canonical entities. Each derived node includes a content hash. Graph edges describe structural relationships and do not create causal claims.

## Portfolio index

The portfolio index evaluates up to 100 packets and sorts attention-required decisions first. It records lifecycle completion, governance state, monitoring state, implementation state, high or critical risk count, and packet hash.

## Connected exchange

The exchange record includes section-level hashes, lifecycle and graph hashes, and product routes. Its state is always `prepared_not_delivered` unless a separate authenticated system and authorized human complete delivery. It never claims external acceptance.

## Human controls

A named human actor is required to confirm a lifecycle stage. Events include previous and current hashes so modification, deletion, or reordering can be detected. Automatic approval and automatic external delivery are prohibited.

## Compatibility

Decision Packet 2.0 is additive. v1.8–v1.16 typed evidence, governance, scenarios, collaboration, Decision Packs, publication, outcomes, institutional integration, accessibility, offline recovery, and release hardening remain available.
