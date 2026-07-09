# Decision Studio v1.3.0 — Integrated Brief Generator

This release adds a professional integrated decision brief generator for the Decision Packet workflow.

## Brief sections

- Executive summary
- Decision question
- Problem framing
- Four-pillar sustainability analysis
- Scenario comparison
- Financial tradeoffs
- Impact measurement
- Claim and narrative risk
- Execution and recovery risk
- Assumptions and uncertainties
- Evidence and source ledger
- Audit appendix summary
- Next review actions
- Workbench handoffs

## Backend endpoints

- `POST /integrated-brief`
- `POST /decision-packet/brief`

## WordPress route

- `/wp-json/scds/v1/integrated-brief`

## Boundary

The integrated brief is educational decision support only. It is not legal, financial, investment, engineering, medical, tax, compliance, assurance, ESG/SDG certification, or professional advice.
