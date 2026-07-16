# Decision Studio v1.12.0 — Institutional and Domain Decision Packs

## Purpose

Institutional Decision Packs convert reusable decision methodologies into inspectable configuration records. A pack does not supply an answer. It specifies what a defensible review must collect, compare, calculate, question, and assign to qualified human reviewers.

## Contract model

- Pack schema: `scds-institutional-decision-pack/1.0`
- Application schema: `scds-decision-pack-application/1.0`
- Decision Packet schema: `scds-decision-packet/1.5`

Each pack contains:

- required intake fields
- weighted criteria
- required evidence
- suggested indicators
- Workbench model routes
- required review roles
- risk questions
- readiness rules
- briefing templates
- governance defaults and professional boundaries

## Validation

Pack validation reports intake, evidence, and reviewer-role completion separately. Missing evidence is treated as a high-severity blocker. A methodology can be applied before it is ready, but it cannot represent itself as approved or professionally reliable.

## Application

Applying a pack populates these additive Decision Packet sections:

- `institutional_decision_pack`
- `criteria_registry`
- `evidence_plan`
- `indicator_plan`
- `model_plan`
- `governance_center.domain_pack_requirements`
- `domain_readiness_rules`
- `domain_brief_templates`

Existing packet evidence, imported artifacts, scenarios, collaboration records, and governance history remain intact.

## Workbench boundary

Decision Studio selects and documents model needs. Workbench remains the execution environment for quantitative models, sensitivity analysis beyond the built-in screening layer, engineering calculations, optimization, and domain-specific computation.

## Human authority boundary

AI and pack templates cannot approve, certify, assure, or sign off decisions. Qualified human and external professional review is mandatory where the decision is regulated, safety-critical, clinical, fiduciary, engineering-dependent, compliance-sensitive, or an exercise of public authority.
