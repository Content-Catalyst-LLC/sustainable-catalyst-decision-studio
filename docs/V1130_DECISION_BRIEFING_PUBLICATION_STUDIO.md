# Decision Studio v1.13.0 — Decision Briefing and Publication Studio

## Purpose

Decision Studio now turns a governed Decision Packet into reviewable publication artifacts without separating conclusions from evidence, assumptions, provenance, governance state, or release restrictions.

## Publication types

- **Executive Decision Memo** — executive_summary, decision_question, recommendation, key_evidence, tradeoffs, governance, next_actions.
- **Technical Decision Report** — executive_summary, decision_question, methodology, evidence, scenario_analysis, technical_analysis, assumptions, risks, governance, implementation, monitoring, bibliography.
- **Board or Leadership Brief** — executive_summary, recommendation, alternatives, material_risks, financial_tradeoffs, governance, decision_required.
- **Alternatives Analysis** — decision_question, alternatives, scenario_analysis, tradeoffs, sensitivity, recommendation, bibliography.
- **Public Decision Dossier** — executive_summary, decision_question, public_interest, alternatives, evidence, methodology, risks, governance, implementation, monitoring, bibliography.
- **Evidence Appendix** — evidence, quotations, site_intelligence, workbench_outputs, research_lab_outputs, bibliography.
- **Assumptions Register** — assumptions, uncertainties, sensitivity, review_actions.
- **Methodology Statement** — scope, methodology, decision_pack, calculation_methods, limitations, governance, bibliography.
- **Audit and Provenance Appendix** — source_ledger, calculation_trace, review_history, collaboration_history, integrity_checks, transformation_history.
- **Implementation Plan** — recommendation, implementation, owners, milestones, risks, monitoring, reassessment.
- **Minority or Dissenting View** — decision_question, majority_position, dissenting_position, contested_evidence, unresolved_assumptions, review_actions.
- **Post-Decision Monitoring Plan** — decision_commitments, indicators, baselines, targets, owners, monitoring, reassessment, public_reporting.

## Citation-native publication

Evidence records from Knowledge Library, Site Intelligence, Workbench, Research Lab, Research Librarian, and Platform Core are normalized into a Harvard-style bibliography. Stable anchors such as `[S1]` connect decision claims to the source registry. The publication does not invent bibliographic metadata when it is absent; incomplete source details remain visible for human correction.

## Audience and governance

- **Internal:** working publication; no external release authorization implied.
- **Reviewed:** requires `reviewed_export_allowed` from Decision Governance.
- **Public:** requires `public_export_allowed`, public section visibility, and redaction processing.

The system cannot approve, certify, assure, or professionally sign off a decision. A generated publication remains a draft until qualified human reviewers complete the applicable governance process.

## Visibility and redaction

Each section is classified as `private`, `institutional`, or `public`. Public output removes non-public sections and records every deterministic redaction event. Text replacement rules and public email redaction are recorded in `scds-publication-redaction/1.0`.

## Publication handoffs

Draft handoffs can target:

- Knowledge Library
- Research
- Publications
- Channel

Handoffs carry the publication ID, Decision Packet ID, content hash, audience, governance state, and review-required status. They do not automatically publish content.

## Contracts

- `scds-decision-publication/1.0`
- `scds-publication-handoff/1.0`
- `scds-publication-redaction/1.0`
- `scds-decision-packet/1.6`

## API routes

- `GET /publication-studio/template`
- `POST /publication-studio/generate`
- `POST /publication-studio/redact`
- `POST /publication-studio/handoff`
- `POST /decision-packet/publication`

WordPress mirrors these under `/wp-json/scds/v1` and provides:

```text
[sc_decision_studio mode="publication" title="Decision Briefing and Publication Studio"]
```

## PDF boundary

The release produces print-ready HTML. A reviewed user may print or save that HTML as PDF through the browser. v1.13.0 does not claim a native server-side PDF renderer or regulated document-signing service.
