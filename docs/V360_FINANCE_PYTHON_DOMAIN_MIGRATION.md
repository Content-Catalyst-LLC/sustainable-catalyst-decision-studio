# Decision Studio v3.6.0 — Finance Python Domain Migration

v3.6.0 migrates Finance from a first-class module contract into an authoritative Python/PostgreSQL domain over the shared Decision Kernel and v3.4 repository. Canvas remains authoritative from v3.5.

## Authority

Finance owns durable financial context, assumptions, scenario context, uncertainty registrations, model/result references, cost/revenue/capital/discounting context, and Workbench computation receipts. Workbench remains the sole compute authority for financial calculation/model execution. Decision Studio stores and governs financial context and results; it does not duplicate the Workbench runtime.

Shared decision identity and lifecycle remain Decision Kernel responsibilities. Final decisions remain human-governed.

## Persistence

No schema migration is introduced. Finance reuses the certified 20-table PostgreSQL schema and Alembic revision `0001_v330_pg_foundation`.

Finance stores a canonical `scds-finance-domain/1.0` object in `decision_objects` and normalizes domain-owned state into `assumptions`, `scenarios`, `scenario_variables`, `uncertainty_models`, `artifacts`, `decision_module_bindings`, and `decision_events`.

v3.6 also adds explicit domain ownership markers so Canvas and Finance can safely share the `assumptions` table without deleting each other's rows.

## API

v3.6 adds 11 routes under `/finance`. Contract/template endpoints are public. Finance decision data requires `finance:read` or `finance:write`; the repository key and super-key are also authorized.

## Legacy migration

`POST /finance/import/legacy` promotes a legacy Catalyst Finance artifact into the Python repository while preserving the original artifact in provenance. Stable decision IDs make the import idempotent.

## Workbench boundary

Workbench remains calculation authority for cash-flow, NPV/IRR, cost-benefit, sensitivity, optimization, simulation, and other computational finance tasks. Decision Studio persists model references and computation receipts but does not execute those models itself.

## Human authority

Financial outputs are evidence for judgment. They do not automatically select a winner, recommend an action, approve a decision, or become final decision authority.
